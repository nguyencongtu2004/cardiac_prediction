"""
helmet_detector_consumer.py - Kafka Consumer for Helmet Violation Detection
============================================================================
Consumes video frames from Kafka and detects helmet violations.
Sends violations to 'helmet_violations' topic and saves to database.

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
from pipeline.detectors.base import clamp_box, draw_box, head_region, MODELS_DIR
from pipeline.detectors.tracker import CentroidTracker
from pipeline.detectors.helmet_detector import (
    get_output_layer_names, detect_helmets, detect_persons_and_bikes,
    associate_riders, check_helmet_violation, annotate_helmet_frame,
    HEAD_RATIO
)


# =========================
# CONFIG
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_DIR = os.path.join(BASE_DIR, "violations", "helmet")

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
INPUT_TOPIC = 'helmet_video_frames'
OUTPUT_TOPIC = 'helmet_violations'

# Model paths
HELMET_CFG = os.path.join(MODELS_DIR, "yolov3-helmet.cfg")
HELMET_WEIGHTS = os.path.join(MODELS_DIR, "yolov3-helmet.weights")
YOLOV8_WEIGHTS = os.path.join(MODELS_DIR, "yolov8n.pt")

# Detection settings
CONF_THRES = 0.5
NMS_THRES = 0.4
INPUT_SIZE = 416

# Tracking
TRACK_MAX_DIST = 80
TRACK_TTL_SEC = 1.0
SAVE_COOLDOWN_SEC = 2.0

os.makedirs(OUTPUT_DIR, exist_ok=True)


# =========================
# KAFKA SETUP
# =========================
def create_consumer():
    """Create Kafka consumer with retry logic"""
    max_retries = 10
    for i in range(max_retries):
        try:
            consumer = KafkaConsumer(
                INPUT_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                group_id='helmet_detector_group',
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
    print("Helmet Violation Detector - Kafka Consumer")
    print("="*60)
    
    # Load YOLOv3 Helmet model
    print("[INFO] Loading YOLOv3 (Helmet)...")
    if not os.path.exists(HELMET_CFG) or not os.path.exists(HELMET_WEIGHTS):
        print(f"[ERROR] Helmet model files missing")
        return
    
    helmet_net = cv2.dnn.readNetFromDarknet(HELMET_CFG, HELMET_WEIGHTS)
    helmet_net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
    helmet_net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
    helmet_out = get_output_layer_names(helmet_net)
    print("[INFO] YOLOv3 Helmet model loaded")
    
    # Load YOLOv8 model
    print(f"[INFO] Loading YOLOv8 from {YOLOV8_WEIGHTS}...")
    try:
        yolo8_model = YOLO(YOLOV8_WEIGHTS)
        print("[INFO] YOLOv8 model loaded")
    except Exception as e:
        print(f"[ERROR] Failed to load YOLOv8: {e}")
        return
    
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
            
            # Initialize tracker for this camera
            if camera_id not in trackers:
                trackers[camera_id] = CentroidTracker(max_dist=TRACK_MAX_DIST, ttl_sec=TRACK_TTL_SEC)
            tracker = trackers[camera_id]
            
            # A. Detect Helmets (YOLOv3)
            helmet_boxes = detect_helmets(helmet_net, helmet_out, frame, CONF_THRES, NMS_THRES, INPUT_SIZE)
            
            # B. Detect Persons + Bikes (YOLOv8)
            persons, bikes = detect_persons_and_bikes(yolo8_model, frame, CONF_THRES)
            
            if len(persons) == 0 or len(bikes) == 0:
                if frame_count % 100 == 0:
                    print(f"[Frame {frame_count}] No riders detected")
                continue
            
            # C. Associate Riders
            riders = associate_riders(persons, bikes)
            
            if len(riders) == 0:
                continue
            
            # D. Track Riders
            rider_boxes = [r[0] for r in riders]
            tracked = tracker.update([(box, "rider") for box in rider_boxes], now_ts)
            
            # E. Check Violations
            violations = []
            for tid, track_info in tracked.items():
                pbox = track_info["box"]
                
                if check_helmet_violation(pbox, helmet_boxes):
                    key = (camera_id, tid)
                    last = last_saved.get(key, 0)
                    if (now_ts - last) >= SAVE_COOLDOWN_SEC:
                        violations.append((tid, pbox))
                        last_saved[key] = now_ts
            
            if violations:
                print(f"\n[Frame {frame_count}] ⚠️  {len(violations)} violation(s) detected!")
            elif frame_count % 50 == 0:
                print(f"[Frame {frame_count}] ✓ {len(tracked)} rider(s) tracked", end='\r')
            
            # F. Process Violations
            for tid, pbox in violations:
                violation_count += 1
                
                # Create annotated image
                out = annotate_helmet_frame(frame, helmet_boxes, bikes, 
                                           {tid: pbox for tid, _ in [(tid, pbox)]}, 
                                           [(tid, pbox)])
                
                # Add camera info
                cv2.putText(out, f"Camera: {camera_id}", (W - 200, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # Save image
                violation_id = str(uuid.uuid4())
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"helmet_{camera_id}_{timestamp}_{violation_id[:8]}.jpg"
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
                    "violation_type": "no_helmet",
                    "image_path": filepath,
                    "image_base64": img_base64,
                    "bounding_box": pbox,
                    "track_id": tid,
                    "metadata": {
                        "frame_size": [W, H],
                        "helmets_detected": len(helmet_boxes),
                        "riders_tracked": len(tracked)
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
