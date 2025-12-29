"""
detect_lane_violation.py - Lane Violation Detection (Standalone)
=================================================================
Phát hiện vi phạm lấn làn (vượt vạch liền).
Sử dụng YOLOv8n model cho vehicle detection.

Usage:
    python scripts/detect_lane_violation.py --video data/video/cam1.mp4 --camera cam1 --show --skip 3
    python scripts/detect_lane_violation.py --video data/video/cam1.mp4 --show
"""

import os
import sys
import time
import cv2
import argparse
import uuid
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ultralytics import YOLO

# Import shared detection logic
from pipeline.detectors.base import (
    load_roi_config, get_camera_config, scale_config,
    draw_box, MODELS_DIR
)
from pipeline.detectors.tracker import CentroidTracker
from pipeline.detectors.lane_detector import (
    LaneViolationChecker, detect_vehicles_for_lane,
    annotate_lane_frame, draw_lane_lines
)


# =========================
# CONFIG
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "violations", "lane")
DATA_DIR = os.path.join(BASE_DIR, "data")

DEFAULT_VIDEO = os.path.join(DATA_DIR, "video/cam1.mp4")

# Use YOLOv8n model for vehicle detection
YOLOV8_MODEL_PATH = os.path.join(MODELS_DIR, "yolov8n.pt")

# Detection settings
CONF_THRES = 0.4
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
# MAIN
# =========================
def main():
    parser = argparse.ArgumentParser(description='Lane Violation Detection')
    parser.add_argument('--video', type=str, default=DEFAULT_VIDEO, help='Path to input video')
    parser.add_argument('--config', type=str, default=None, help='Path to ROI config JSON')
    parser.add_argument('--output', type=str, default=OUTPUT_DIR, help='Output directory')
    parser.add_argument('--show', action='store_true', help='Show detection window')
    parser.add_argument('--camera', type=str, default='default', help='Camera ID for config')
    parser.add_argument('--skip', type=int, default=1, help='Process every N-th frame')
    parser.add_argument('--conf', type=float, default=CONF_THRES, help='Confidence threshold')
    args = parser.parse_args()
    
    # Setup output directory
    os.makedirs(args.output, exist_ok=True)
    
    # Load configuration
    all_config = load_roi_config(args.config)
    config = get_camera_config(all_config, args.camera)
    
    if not config:
        print(f"[WARNING] No config found for camera '{args.camera}', using defaults")
        config = {
            "lane_lines": [
                {"x1": 400, "y1": 300, "x2": 200, "y2": 1000, "type": "solid"},
                {"x1": 800, "y1": 300, "x2": 700, "y2": 1000, "type": "dashed"},
                {"x1": 1200, "y1": 300, "x2": 1300, "y2": 1000, "type": "solid"}
            ]
        }
    
    # Check if lane_lines is configured
    if "lane_lines" not in config or not config["lane_lines"]:
        print(f"[WARNING] No lane_lines configured for camera '{args.camera}'")
        print("[INFO] Please configure lane_lines in config/roi_config.json")
        print("[INFO] Using default lane lines for demonstration")
        config["lane_lines"] = [
            {"x1": 400, "y1": 300, "x2": 200, "y2": 1000, "type": "solid"},
            {"x1": 800, "y1": 300, "x2": 700, "y2": 1000, "type": "dashed"},
            {"x1": 1200, "y1": 300, "x2": 1300, "y2": 1000, "type": "solid"}
        ]
    
    print(f"[INFO] Loaded config for camera: {args.camera}")
    print(f"[INFO] Lane lines configured: {len(config.get('lane_lines', []))}")
    
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
    scaled_config = scale_lane_config(config, W, H)
    
    # Also apply general scaling
    scaled_config = scale_config(scaled_config, W, H)
    
    # Initialize detector and tracker
    lane_checker = LaneViolationChecker(scaled_config)
    tracker = CentroidTracker(max_dist=TRACK_MAX_DIST, ttl_sec=TRACK_TTL_SEC)
    
    # Stats
    frame_idx = 0
    violation_count = 0
    last_saved = {}  # track_id -> timestamp
    
    print(f"\n{'='*60}")
    print("Lane Violation Detection - YOLOv8n")
    print(f"Model: {YOLOV8_MODEL_PATH}")
    print(f"Lane lines: {len(lane_checker.lane_lines)}")
    print(f"Output: {args.output}")
    print(f"{'='*60}\n")
    
    if args.show:
        cv2.namedWindow("Lane Detection", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Lane Detection", 1280, 720)
    
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
            
            # Detect vehicles
            detection_zone = scaled_config.get("detection_zone", [])
            detections = detect_vehicles_for_lane(yolo_model, frame, detection_zone, args.conf)
            
            # Convert detections to format expected by tracker (box, extra)
            tracker_detections = [(d[0], d[1]) for d in detections]
            
            # Track vehicles
            tracked = tracker.update(tracker_detections, now_ts)
            
            # Check for violations
            violations = []
            for tid, track_info in tracked.items():
                violation_info = lane_checker.check_violation(tid, track_info)
                if violation_info:
                    last = last_saved.get(tid, 0)
                    if (now_ts - last) >= SAVE_COOLDOWN_SEC:
                        violations.append((tid, track_info, violation_info))
                        last_saved[tid] = now_ts
            
            # Cleanup old tracks
            lane_checker.cleanup_old_tracks(set(tracked.keys()))
            
            # Create display frame
            if args.show or violations:
                out = annotate_lane_frame(frame, scaled_config, lane_checker, tracked, violations)
                
                # Draw frame info
                cv2.putText(out, f"Frame: {frame_idx}/{total_frames} | Violations: {violation_count}",
                           (10, H - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.putText(out, f"Camera: {args.camera}", (W - 200, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.putText(out, "YOLOv8n + Lane Detection", (10, H - 50),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                
                # Save violations
                for tid, track_info, violation_info in violations:
                    violation_count += 1
                    vehicle_type = track_info.get("vehicle_type", track_info.get("extra", "vehicle"))
                    
                    filename = f"lane_{args.camera}_{uuid.uuid4()}.jpg"
                    filepath = os.path.join(args.output, filename)
                    cv2.imwrite(filepath, out)
                    
                    print(f"\n[VIOLATION #{violation_count}] Frame {frame_idx} | Time {video_ts:.2f}s")
                    print(f"  Track {tid} | {vehicle_type} | {violation_info.get('type', 'unknown')}")
                    print(f"  Line {violation_info.get('line_id', -1)}: {violation_info.get('from_side')} -> {violation_info.get('to_side')}")
                    print(f"  Saved: {filename}")
                
                if args.show:
                    cv2.imshow("Lane Detection", out)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
            
            # Progress
            if frame_idx % 100 == 0:
                print(f"[Progress] Frame {frame_idx}/{total_frames} ({100*frame_idx/max(1,total_frames):.1f}%) | "
                      f"Tracked: {len(tracked)} | Violations: {violation_count}")
    
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
