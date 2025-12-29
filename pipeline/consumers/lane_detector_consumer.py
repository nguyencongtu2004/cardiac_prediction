"""
lane_detector_consumer.py - Kafka Consumer for Lane Violation Detection
========================================================================
Consumes video frames from Kafka and detects lane violations in real-time.
Sends violations to 'lane_violations' topic and saves to database.

Uses shared detection logic from pipeline.detectors.
"""

import os
import time
import json
import base64
import cv2
import numpy as np
import sys
import uuid
from datetime import datetime
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

# Try to import ultralytics
try:
    from ultralytics import YOLO
except ImportError:
    print("Error: 'ultralytics' module not found. Please install it using: pip install ultralytics")
    sys.exit(1)

# Add project root to path for imports (needed in Docker)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import shared detection logic
from pipeline.detectors.base import (
    load_roi_config, get_camera_config, scale_config,
    clamp_box, centroid, bottom_center, draw_box,
    point_in_polygon, MODELS_DIR, CONFIG_DIR
)
from pipeline.detectors.tracker import CentroidTracker
from pipeline.detectors.lane_detector import (
    LaneViolationChecker, detect_vehicles_for_lane,
    annotate_lane_frame, VEHICLE_CLASSES, VEHICLE_NAMES
)


# =========================
# CONFIG
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_DIR = os.path.join(BASE_DIR, "violations", "lane")

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
INPUT_TOPIC = 'helmet_video_frames'  # Share with other detectors
OUTPUT_TOPIC = 'lane_violations'

# YOLOv8 model
YOLOV8_WEIGHTS = os.path.join(MODELS_DIR, "yolov8n.pt")

# Detection thresholds
CONF_THRES = 0.4

# Tracking
TRACK_MAX_DIST = 100
TRACK_TTL_SEC = 2.0
SAVE_COOLDOWN_SEC = 3.0

os.makedirs(OUTPUT_DIR, exist_ok=True)


def scale_lane_config(config: dict, actual_width: int, actual_height: int) -> dict:
    """Scale lane configuration to match actual frame dimensions"""
    config_width = config.get("frame_width", 1920)
    config_height = config.get("frame_height", 1080)
    
    scale_x = actual_width / config_width
    scale_y = actual_height / config_height
    
    scaled = config.copy()
    
    # Scale lane lines
    if "lane_lines" in config:
        scaled_lines = []
        for line in config["lane_lines"]:
            scaled_line = {
                "x1": int(line.get("x1", 0) * scale_x),
                "y1": int(line.get("y1", 0) * scale_y),
                "x2": int(line.get("x2", 0) * scale_x),
                "y2": int(line.get("y2", 0) * scale_y),
                "type": line.get("type", "solid")
            }
            scaled_lines.append(scaled_line)
        scaled["lane_lines"] = scaled_lines
    
    # Scale detection zone
    if "detection_zone" in config and config["detection_zone"]:
        raw_zone = config["detection_zone"]
        scaled["detection_zone"] = [
            [int(pt[0] * scale_x), int(pt[1] * scale_y)] for pt in raw_zone
        ]
    
    return scaled


# =========================
# KAFKA SETUP
# =========================
def create_consumer():
    """Create Kafka consumer"""
    max_retries = 10
    for i in range(max_retries):
        try:
            consumer = KafkaConsumer(
                INPUT_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                group_id='lane_detector_group',
                auto_offset_reset='latest',
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                max_poll_interval_ms=300000,
                session_timeout_ms=30000,
                heartbeat_interval_ms=10000,
                max_poll_records=1
            )
            print(f"[INFO] Connected to Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
            return consumer
        except Exception as e:
            print(f"[WARN] Kafka connection attempt {i+1}/{max_retries} failed: {e}")
            time.sleep(5)
    
    raise RuntimeError(f"Failed to connect to Kafka after {max_retries} attempts")


def create_producer():
    """Create Kafka producer"""
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        max_request_size=10485760,
        acks='all',
        retries=3,
        compression_type='gzip'
    )


# =========================
# MAIN DETECTION LOOP
# =========================
def main():
    print("="*60)
    print("Lane Violation Detector - Kafka Consumer")
    print("="*60)
    
    # Load model
    print(f"[INFO] Loading YOLOv8 from {YOLOV8_WEIGHTS}...")
    try:
        yolo_model = YOLO(YOLOV8_WEIGHTS)
        print("[INFO] Model loaded successfully")
    except Exception as e:
        print(f"[ERROR] Failed to load model: {e}")
        return
    
    # Load ROI config
    all_config = load_roi_config()
    print(f"[INFO] Loaded configs for cameras: {list(all_config.keys())}")
    
    # Create Kafka connections
    consumer = create_consumer()
    producer = create_producer()
    
    # Tracking state per camera
    trackers = {}  # camera_id -> CentroidTracker
    lane_checkers = {}  # camera_id -> LaneViolationChecker
    last_saved = {}  # (camera_id, track_id) -> timestamp
    
    # Stats
    frame_count = 0
    violation_count = 0
    
    print(f"\n[INFO] Listening to topic: {INPUT_TOPIC}")
    print(f"[INFO] Publishing violations to: {OUTPUT_TOPIC}")
    print(f"[INFO] Output directory: {OUTPUT_DIR}")
    print("="*60 + "\n")
    
    try:
        for message in consumer:
            frame_count += 1
            frame_data = message.value
            
            # Decode frame
            try:
                frame_b64 = frame_data.get('image_base64') or frame_data.get('frame')
                if not frame_b64:
                    print(f"[ERROR] No image data in message")
                    continue
                jpg_bytes = base64.b64decode(frame_b64)
                nparr = np.frombuffer(jpg_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is None:
                    continue
            except Exception as e:
                print(f"[ERROR] Failed to decode frame: {e}")
                continue
            
            camera_id = frame_data.get('camera_id', 'default')
            H, W = frame.shape[:2]
            now_ts = time.time()
            
            # Get camera-specific config
            config = get_camera_config(all_config, camera_id)
            
            # Skip cameras without lane configuration
            if "lane_lines" not in config or not config["lane_lines"]:
                if frame_count % 100 == 1:
                    print(f"[Frame {frame_count}] ⏭️  Camera '{camera_id}' has no lane_lines config - skipping")
                continue
            
            # Scale config
            scaled_config = scale_lane_config(config, W, H)
            scaled_config = scale_config(scaled_config, W, H)
            
            # Initialize tracker and lane checker for this camera
            if camera_id not in trackers:
                trackers[camera_id] = CentroidTracker(max_dist=TRACK_MAX_DIST, ttl_sec=TRACK_TTL_SEC)
            if camera_id not in lane_checkers:
                lane_checkers[camera_id] = LaneViolationChecker(scaled_config)
            
            tracker = trackers[camera_id]
            lane_checker = lane_checkers[camera_id]
            
            # Detect vehicles
            detection_zone = scaled_config.get("detection_zone", [])
            detections = detect_vehicles_for_lane(yolo_model, frame, detection_zone, CONF_THRES)
            
            # Convert for tracker
            tracker_detections = [(d[0], d[1]) for d in detections]
            
            # Track vehicles
            tracked = tracker.update(tracker_detections, now_ts)
            
            # Check violations
            violations = []
            for tid, track_info in tracked.items():
                violation_info = lane_checker.check_violation(tid, track_info)
                if violation_info:
                    key = (camera_id, tid)
                    last = last_saved.get(key, 0)
                    if (now_ts - last) >= SAVE_COOLDOWN_SEC:
                        violations.append((tid, track_info, violation_info))
                        last_saved[key] = now_ts
            
            # Cleanup old tracks
            lane_checker.cleanup_old_tracks(set(tracked.keys()))
            
            if violations:
                print(f"\n[Frame {frame_count}] ⚠️  {len(violations)} lane violation(s) detected!")
            else:
                print(f"[Frame {frame_count}] ✓ Tracked: {len(tracked)} vehicles", end='\r')
            
            # Process violations
            for tid, track_info, violation_info in violations:
                violation_count += 1
                box = track_info["box"]
                vehicle_type = track_info.get("vehicle_type", track_info.get("extra", "vehicle"))
                
                # Create annotated image
                out = annotate_lane_frame(frame, scaled_config, lane_checker, tracked, [(tid, track_info, violation_info)])
                
                # Add camera info
                cv2.putText(out, f"Camera: {camera_id}", (W - 200, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # Save image
                violation_id = str(uuid.uuid4())
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"lane_{camera_id}_{timestamp}_{violation_id[:8]}.jpg"
                filepath = os.path.join(OUTPUT_DIR, filename)
                cv2.imwrite(filepath, out)
                
                # Encode image for Kafka
                _, img_encoded = cv2.imencode('.jpg', out, [cv2.IMWRITE_JPEG_QUALITY, 85])
                img_base64 = base64.b64encode(img_encoded.tobytes()).decode('utf-8')
                
                # Create violation message
                violation_msg = {
                    "violation_id": violation_id,
                    "timestamp": datetime.now().isoformat(),
                    "camera_id": camera_id,
                    "vehicle_type": vehicle_type,
                    "violation_type": "lane_violation",
                    "crossed_line_type": violation_info.get("line_type", "solid"),
                    "line_id": violation_info.get("line_id", -1),
                    "from_side": violation_info.get("from_side", "unknown"),
                    "to_side": violation_info.get("to_side", "unknown"),
                    "image_path": filepath,
                    "image_base64": img_base64,
                    "bounding_box": box,
                    "track_id": tid,
                    "metadata": {
                        "violation_position": violation_info.get("position", [0, 0]),
                        "distance_to_line": violation_info.get("distance", 0),
                        "frame_size": [W, H]
                    }
                }
                
                # Send to Kafka
                try:
                    producer.send(OUTPUT_TOPIC, violation_msg)
                    producer.flush()
                    print(f"  📤 Sent violation to Kafka: {violation_id[:8]}...")
                except Exception as e:
                    print(f"  ⚠️  Failed to send to Kafka: {e}")
                
                print(f"  📸 Saved: {filename}")
    
    except KeyboardInterrupt:
        print("\n\n[INFO] Shutting down...")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        consumer.close()
        producer.close()
        print(f"\n[STATS] Processed {frame_count} frames, detected {violation_count} violations")


if __name__ == "__main__":
    main()
