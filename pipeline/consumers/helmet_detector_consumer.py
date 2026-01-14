"""
helmet_detector_consumer.py - Kafka Consumer for Helmet Violation Detection
============================================================================
Consumes video frames from Kafka and detects helmet violations.
Sends violations to 'helmet_violations' topic and saves to database.

Uses UNIFIED model (best.pt) with 8 classes:
0: person, 1: bicycle, 2: car, 3: motorcycle,
4: bus, 5: truck, 6: with_helmet, 7: without_helmet
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
    detect_violations_unified, annotate_unified_frame,
    ViolationDeduplicator, HEAD_RATIO
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

# Use unified model (best.pt)
UNIFIED_MODEL_PATH = os.path.join(MODELS_DIR, "best.pt")

# Detection settings
CONF_THRES = 0.25  # Lower threshold for better recall

# Tracking
TRACK_MAX_DIST = 80
TRACK_TTL_SEC = 1.0

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
    print("Helmet Violation Detector - Kafka Consumer (UNIFIED MODEL)")
    print("="*60)
    
    # Load Unified Model (best.pt)
    print(f"[INFO] Loading UNIFIED model from {UNIFIED_MODEL_PATH}...")
    if not os.path.exists(UNIFIED_MODEL_PATH):
        print(f"[ERROR] Model file not found: {UNIFIED_MODEL_PATH}")
        return
    
    try:
        model = YOLO(UNIFIED_MODEL_PATH)
        print("✓ Unified model loaded (8 classes: person, vehicles, with_helmet, without_helmet)")
    except Exception as e:
        print(f"[ERROR] Failed to load model: {e}")
        return
    
    # Create Kafka connections
    consumer = create_consumer()
    producer = create_producer()
    
    # Tracking state per camera
    trackers = {}  # camera_id -> CentroidTracker
    deduplicators = {}  # camera_id -> ViolationDeduplicator
    
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
            
            # Initialize tracker and deduplicator for this camera
            if camera_id not in trackers:
                trackers[camera_id] = CentroidTracker(max_dist=TRACK_MAX_DIST, ttl_sec=TRACK_TTL_SEC)
            if camera_id not in deduplicators:
                deduplicators[camera_id] = ViolationDeduplicator()
            
            tracker = trackers[camera_id]
            deduplicator = deduplicators[camera_id]
            
            # Detect violations using unified model
            violations, all_detections = detect_violations_unified(
                model, frame, tracker, deduplicator, now_ts, CONF_THRES
            )
            
            # Log detection info
            det_info = f"({len(all_detections.get('person_boxes', []))}p, {len(all_detections.get('motorcycle_boxes', []))}m)"
            
            if violations:
                print(f"\n[Frame {frame_count}] ⚠️  {len(violations)} violation(s) detected! {det_info}")
            elif frame_count % 50 == 0:
                riders_count = (len(all_detections.get('riders_with_helmet', [])) + 
                               len(all_detections.get('riders_without_helmet', [])))
                print(f"[Frame {frame_count}] ✓ {riders_count} rider(s) tracked {det_info}", end='\r')
            
            # Process Violations
            for violation_info in violations:
                violation_count += 1
                
                track_id = violation_info['track_id']
                box = violation_info['box']
                confidence = violation_info['confidence']
                method = violation_info.get('method', 'unknown')
                
                # Create annotated image
                out = annotate_unified_frame(frame, all_detections, [violation_info])
                
                # Draw violation box
                draw_box(out, box, f"NO HELMET {track_id}", color=(0, 0, 255), thickness=3)
                
                # Add camera info
                cv2.putText(out, f"Camera: {camera_id}", (W - 200, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(out, f"Conf: {confidence:.2f} | {method}", (10, H - 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                
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
                # Convert box [x,y,w,h] to dict for database compatibility
                bbox_dict = {"x": box[0], "y": box[1], "w": box[2], "h": box[3]} if len(box) == 4 else {}
                
                violation_msg = {
                    "violation_id": violation_id,
                    "timestamp": datetime.now().isoformat(),
                    "camera_id": camera_id,
                    "violation_type": "no_helmet",
                    "image_path": filepath,
                    "image_base64": img_base64,
                    "bounding_box": bbox_dict,
                    "track_id": track_id,
                    "frame_number": frame_count,
                    "confidence": confidence,
                    "detection_method": method,
                    "metadata": {
                        "frame_size": [W, H],
                        "persons_detected": len(all_detections.get('person_boxes', [])),
                        "vehicles_detected": len(all_detections.get('motorcycle_boxes', [])),
                        "helmets_detected": len(all_detections.get('helmet_boxes', [])),
                        "no_helmets_detected": len(all_detections.get('no_helmet_boxes', []))
                    }
                }
                
                # Send to Kafka
                try:
                    producer.send(OUTPUT_TOPIC, violation_msg)
                    producer.flush()
                    print(f"  📤 Sent violation to Kafka: {violation_id[:8]}... | conf={confidence:.2f} | {method}")
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
