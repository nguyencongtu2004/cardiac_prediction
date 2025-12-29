"""
detect_redlight_violation.py - Red Light Violation Detection (Standalone)
==========================================================================
Phát hiện vi phạm vượt đèn đỏ.
Sử dụng YOLOv8n model cho vehicle detection.

Usage:
    python scripts/detect_redlight_violation.py --video data/video/cam1.mp4 --camera cam1 --show --skip 3
    python scripts/detect_redlight_violation.py --video data/video/cam1.mp4
"""

import os
import sys
import time
import cv2
import argparse
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ultralytics import YOLO

# Import shared detection logic
from pipeline.detectors.base import (
    load_roi_config, get_camera_config, scale_config,
    draw_box, draw_stop_line, draw_detection_zone, MODELS_DIR
)
from pipeline.detectors.tracker import CentroidTracker
from pipeline.detectors.redlight_detector import (
    TrafficLightDetector, RedLightViolationChecker,
    detect_vehicles, annotate_violation_frame
)


# =========================
# CONFIG
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "violations", "redlight")
DATA_DIR = os.path.join(BASE_DIR, "data")

DEFAULT_VIDEO = os.path.join(DATA_DIR, "video/redlight-test.mp4")

# Use YOLOv8n model for vehicle detection (more stable for red light detection)
YOLOV8_MODEL_PATH = os.path.join(MODELS_DIR, "yolov8n.pt")

# Detection settings
CONF_THRES = 0.4
TRACK_MAX_DIST = 100
TRACK_TTL_SEC = 2.0
SAVE_COOLDOWN_SEC = 3.0

os.makedirs(OUTPUT_DIR, exist_ok=True)


# =========================
# MAIN
# =========================
def main():
    parser = argparse.ArgumentParser(description='Red Light Violation Detection')
    parser.add_argument('--video', type=str, default=DEFAULT_VIDEO, help='Path to input video')
    parser.add_argument('--config', type=str, default=None, help='Path to ROI config JSON')
    parser.add_argument('--output', type=str, default=OUTPUT_DIR, help='Output directory')
    parser.add_argument('--show', action='store_true', help='Show detection window')
    parser.add_argument('--camera', type=str, default='default', help='Camera ID for config')
    parser.add_argument('--skip', type=int, default=1, help='Process every N-th frame')
    args = parser.parse_args()
    
    # Setup output directory
    os.makedirs(args.output, exist_ok=True)
    
    # Load configuration
    all_config = load_roi_config(args.config)
    config = get_camera_config(all_config, args.camera)
    
    if not config:
        print(f"[WARNING] No config found for camera '{args.camera}', using defaults")
        config = {"stop_line": {"y": 400}, "traffic_light_roi": {"x1": 0, "y1": 0, "x2": 200, "y2": 200}}
    
    print(f"[INFO] Loaded config for camera: {args.camera}")
    
    # Load YOLOv8n model for vehicle detection
    print(f"[INFO] Loading YOLOv8n from {YOLOV8_MODEL_PATH}...")
    if not os.path.exists(YOLOV8_MODEL_PATH):
        print(f"Error: Model file not found: {YOLOV8_MODEL_PATH}")
        print("Please ensure 'yolov8n.pt' is in the 'models/' directory.")
        return
    
    try:
        yolo_model = YOLO(YOLOV8_MODEL_PATH)
        print("✓ YOLOv8n model loaded")
    except Exception as e:
        print(f"Error loading model: {e}")
        return
    
    # Open video
    print(f"[INFO] Opening video: {args.video}")
    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        print(f"Error: Cannot open video: {args.video}")
        return
    
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    print(f"[INFO] FPS={fps:.2f}, Total frames={total_frames}")
    
    # Get first frame to determine size and scale config
    ret, first_frame = cap.read()
    if not ret:
        print("Error: Cannot read first frame")
        return
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Reset to start
    
    H, W = first_frame.shape[:2]
    scaled_config = scale_config(config, W, H)
    
    # Initialize detectors with scaled config
    light_detector = TrafficLightDetector(yolo_model, scaled_config)
    violation_checker = RedLightViolationChecker(scaled_config)
    tracker = CentroidTracker(max_dist=TRACK_MAX_DIST, ttl_sec=TRACK_TTL_SEC)
    
    # Stats
    frame_idx = 0
    violation_count = 0
    last_saved = {}
    
    print(f"\n{'='*60}")
    print("Red Light Violation Detection - YOLOv8n")
    print(f"Model: {YOLOV8_MODEL_PATH}")
    print(f"Stop Line Y: {violation_checker.stop_line_y}")
    print(f"Violation Direction: {violation_checker.violation_direction}")
    print(f"Output: {args.output}")
    print(f"{'='*60}\n")
    
    if args.show:
        cv2.namedWindow("Red Light Detection", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Red Light Detection", 1280, 720)
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_idx += 1
            
            # Skip frames
            if frame_idx % args.skip != 0:
                continue
            
            now_ts = time.time()
            video_ts = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            
            # 1. Detect traffic light state
            light_state = light_detector.detect_light_state(frame)
            
            # 2. Detect vehicles (with detection zone filtering)
            detection_zone = scaled_config.get("detection_zone", [])
            detections = detect_vehicles(yolo_model, frame, detection_zone, CONF_THRES)
            
            # 3. Track vehicles
            tracked = tracker.update(detections, now_ts)
            
            # 4. Check for violations
            violations = []
            for tid, track_info in tracked.items():
                if violation_checker.check_violation(track_info, light_state):
                    last = last_saved.get(tid, 0)
                    if (now_ts - last) >= SAVE_COOLDOWN_SEC:
                        violations.append((tid, track_info))
                        last_saved[tid] = now_ts
            
            # 5. Draw and save
            if args.show or violations:
                out = annotate_violation_frame(frame, scaled_config, light_state, tracked, violations)
                
                # Draw frame info
                cv2.putText(out, f"Frame: {frame_idx}/{total_frames} | Light: {light_state} | Violations: {violation_count}",
                           (10, H - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.putText(out, "YOLOv8n", (10, H - 50),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                
                # Save violations
                for tid, track_info in violations:
                    violation_count += 1
                    vehicle_type = track_info.get("vehicle_type", track_info.get("extra", "vehicle"))
                    filename = f"redlight_t{video_ts:07.2f}_f{frame_idx:06d}_id{tid}.jpg"
                    filepath = os.path.join(args.output, filename)
                    cv2.imwrite(filepath, out)
                    print(f"[VIOLATION #{violation_count}] Frame {frame_idx} | Time {video_ts:.2f}s | "
                          f"Track {tid} | {vehicle_type} | Light: {light_state}")
                
                if args.show:
                    cv2.imshow("Red Light Detection", out)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
            
            # Progress
            if frame_idx % 100 == 0:
                print(f"[Progress] Frame {frame_idx}/{total_frames} ({100*frame_idx/max(1,total_frames):.1f}%) | "
                      f"Light: {light_state} | Violations: {violation_count}")
    
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")
    
    finally:
        cap.release()
        if args.show:
            cv2.destroyAllWindows()
    
    print(f"\n{'='*60}")
    print("Detection Complete!")
    print(f"  Model: yolov8n.pt")
    print(f"  Total frames: {frame_idx}")
    print(f"  Violations detected: {violation_count}")
    print(f"  Output directory: {args.output}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
