"""
redlight_detector_consumer.py - Kafka Consumer for Red Light Violation Detection
=================================================================================
Consumes video frames from Kafka and detects red light violations in real-time.
Sends violations to 'redlight_violations' topic and saves to database.

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
    clamp_box, centroid, bottom_center, draw_box, draw_stop_line, draw_detection_zone,
    point_in_polygon, MODELS_DIR, CONFIG_DIR
)
from pipeline.detectors.tracker import CentroidTracker
from pipeline.detectors.redlight_detector import (
    TrafficLightDetector, RedLightViolationChecker,
    VEHICLE_CLASSES, VEHICLE_NAMES, COCO_TRAFFIC_LIGHT_ID
)


# =========================
# CONFIG
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_DIR = os.path.join(BASE_DIR, "violations", "redlight")

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
INPUT_TOPIC = 'helmet_video_frames'  # Share with helmet detector
OUTPUT_TOPIC = 'redlight_violations'

# YOLOv8 model
YOLOV8_WEIGHTS = os.path.join(MODELS_DIR, "yolov8n.pt")

# Detection thresholds
CONF_THRES = 0.4

# Tracking
TRACK_MAX_DIST = 100
TRACK_TTL_SEC = 2.0
SAVE_COOLDOWN_SEC = 3.0

os.makedirs(OUTPUT_DIR, exist_ok=True)


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
                group_id='redlight_detector_group',
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
    print("Red Light Violation Detector - Kafka Consumer")
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
                # Producer sends 'image_base64' key
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
            
            # Skip cameras not configured for red light detection
            if camera_id not in all_config:
                if frame_count % 100 == 1:
                    print(f"[Frame {frame_count}] ⏭️  Camera '{camera_id}' not configured - skipping")
                continue
            
            # Get camera-specific config and scale it
            config = get_camera_config(all_config, camera_id)
            scaled_config = scale_config(config, W, H)
            
            # Initialize tracker for this camera
            if camera_id not in trackers:
                trackers[camera_id] = CentroidTracker(max_dist=TRACK_MAX_DIST, ttl_sec=TRACK_TTL_SEC)
            tracker = trackers[camera_id]
            
            # Initialize detectors with scaled config
            light_detector = TrafficLightDetector(yolo_model, scaled_config)
            violation_checker = RedLightViolationChecker(scaled_config)
            
            # Get scaled values
            stop_line_y = scaled_config.get("stop_line", {}).get("y", 400)
            violation_direction = scaled_config.get("stop_line", {}).get("violation_direction", "below")
            scaled_roi = scaled_config.get("traffic_light_roi", {})
            scaled_zone = scaled_config.get("detection_zone", [])
            
            # Detect traffic light state
            light_state = light_detector.detect_light_state(frame)
            
            # Detect vehicles
            results = yolo_model.predict(frame, classes=VEHICLE_CLASSES, conf=CONF_THRES, verbose=False)
            detections = []
            for r in results:
                for box_data in r.boxes:
                    x1, y1, x2, y2 = map(int, box_data.xyxy[0].cpu().numpy())
                    cls_id = int(box_data.cls[0].item())
                    box = clamp_box([x1, y1, x2 - x1, y2 - y1], W, H)
                    vehicle_type = VEHICLE_NAMES.get(cls_id, "vehicle")
                    
                    # Filter by detection zone
                    vehicle_center = centroid(box)
                    if point_in_polygon(vehicle_center, scaled_zone):
                        detections.append((box, vehicle_type))
            
            # Track vehicles
            tracked = tracker.update(detections, now_ts)
            
            # Check violations
            violations = []
            for tid, track_info in tracked.items():
                if violation_checker.check_violation(track_info, light_state):
                    key = (camera_id, tid)
                    last = last_saved.get(key, 0)
                    if (now_ts - last) >= SAVE_COOLDOWN_SEC:
                        violations.append((tid, track_info))
                        last_saved[key] = now_ts
            
            if violations:
                print(f"\n[Frame {frame_count}] ⚠️  {len(violations)} violation(s) detected!")
            else:
                print(f"[Frame {frame_count}] ✓ Light: {light_state}", end='\r')
            
            # Process violations
            for tid, track_info in violations:
                violation_count += 1
                box = track_info["box"]
                vehicle_type = track_info.get("vehicle_type", track_info.get("extra", "vehicle"))
                
                # Create annotated image
                out = frame.copy()
                
                # Draw stop line
                draw_stop_line(out, stop_line_y)
                
                # Draw traffic light ROI
                if scaled_roi:
                    rx1, ry1 = scaled_roi.get("x1", 0), scaled_roi.get("y1", 0)
                    rx2, ry2 = scaled_roi.get("x2", 100), scaled_roi.get("y2", 100)
                    light_color = (0, 0, 255) if light_state == "RED" else (0, 255, 0) if light_state == "GREEN" else (0, 255, 255)
                    cv2.rectangle(out, (rx1, ry1), (rx2, ry2), light_color, 2)
                    cv2.putText(out, f"Light: {light_state}", (rx1, ry1 - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, light_color, 2)
                
                # Draw detection zone
                draw_detection_zone(out, scaled_zone)
                
                # Draw violation box
                draw_box(out, box, f"VIOLATION #{tid}", color=(0, 0, 255), thickness=3)
                
                # Add camera info
                cv2.putText(out, f"Camera: {camera_id}", (W - 200, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # Save image
                violation_id = str(uuid.uuid4())
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"redlight_{camera_id}_{timestamp}_{violation_id[:8]}.jpg"
                filepath = os.path.join(OUTPUT_DIR, filename)
                cv2.imwrite(filepath, out)
                
                # Encode image for Kafka
                _, img_encoded = cv2.imencode('.jpg', out, [cv2.IMWRITE_JPEG_QUALITY, 85])
                img_base64 = base64.b64encode(img_encoded.tobytes()).decode('utf-8')
                
                # Create violation message
                # Convert box [x,y,w,h] to dict for database compatibility
                bbox_dict = {"x": box[0], "y": box[1], "w": box[2], "h": box[3]} if len(box) == 4 else {}
                
                violation_msg = {
                    "violation_id": violation_id,
                    "timestamp": datetime.now().isoformat(),
                    "camera_id": camera_id,
                    "vehicle_type": vehicle_type,
                    "traffic_light_state": light_state,
                    "violation_type": "RED_LIGHT",
                    "image_path": filepath,
                    "image_base64": img_base64,
                    "bounding_box": bbox_dict,
                    "track_id": tid,
                    "frame_number": frame_count,
                    "confidence": 0.9,  # Default confidence for red light violations
                    "metadata": {
                        "stop_line_y": stop_line_y,
                        "violation_direction": violation_direction,
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
