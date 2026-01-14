"""
detect_helmet_violation.py - Helmet Violation Detection (Standalone)
=====================================================================
Phát hiện người đi xe máy không đội mũ bảo hiểm.
Sử dụng UNIFIED model (best.pt) với 8 classes:
0: person, 1: bicycle, 2: car, 3: motorcycle,
4: bus, 5: truck, 6: with_helmet, 7: without_helmet

Usage:
    python scripts/detect_helmet_violation.py --video data/video/helmet_segment_001.mp4 --show --skip 3
    python scripts/detect_helmet_violation.py --video data/video/bike-test.mp4 --show
"""

import os
import sys
import time
import cv2
import argparse
import uuid

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ultralytics import YOLO

# Import shared detection logic
from pipeline.detectors.base import MODELS_DIR, draw_box
from pipeline.detectors.tracker import CentroidTracker
from pipeline.detectors.helmet_detector import (
    detect_violations_unified, annotate_unified_frame,
    ViolationDeduplicator, HEAD_RATIO
)


# =========================
# CONFIG
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "violations", "helmet")
DATA_DIR = os.path.join(BASE_DIR, "data")

DEFAULT_VIDEO = os.path.join(DATA_DIR, "video/bike-test.mp4")

# Use unified model (best.pt)
UNIFIED_MODEL_PATH = os.path.join(MODELS_DIR, "best.pt")

# Detection settings
CONF_THRES = 0.25  # Lower threshold for better recall
TRACK_MAX_DIST = 80
TRACK_TTL_SEC = 1.0

os.makedirs(OUTPUT_DIR, exist_ok=True)


# =========================
# MAIN
# =========================
def main():
    parser = argparse.ArgumentParser(description='Helmet Violation Detection (Unified Model)')
    parser.add_argument('--video', type=str, default=DEFAULT_VIDEO, help='Path to video file')
    parser.add_argument('--show', action='store_true', help='Show real-time display')
    parser.add_argument('--camera', type=str, default='default', help='Camera ID')
    parser.add_argument('--skip', type=int, default=1, help='Process every N-th frame')
    parser.add_argument('--conf', type=float, default=CONF_THRES, help='Confidence threshold')
    args = parser.parse_args()
    
    # 1. Load Unified Model (best.pt)
    print(f"[INFO] Loading UNIFIED model from {UNIFIED_MODEL_PATH}...")
    if not os.path.exists(UNIFIED_MODEL_PATH):
        print(f"Error: Model file not found: {UNIFIED_MODEL_PATH}")
        print("Please ensure 'best.pt' is in the 'models/' directory.")
        return
    
    try:
        model = YOLO(UNIFIED_MODEL_PATH)
        print("✓ Unified model loaded (8 classes: person, vehicles, with_helmet, without_helmet)")
    except Exception as e:
        print(f"Error loading model: {e}")
        return
    
    # 2. Open Video
    print(f"[INFO] Opening video: {args.video}")
    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        print(f"Error: Cannot open video: {args.video}")
        return
    
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    print(f"[INFO] FPS={fps:.2f}, Total frames={total_frames}")
    
    print(f"\n{'='*60}")
    print("Helmet Violation Detection - UNIFIED MODEL")
    print(f"Model: {UNIFIED_MODEL_PATH}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"{'='*60}\n")
    
    tracker = CentroidTracker(max_dist=TRACK_MAX_DIST, ttl_sec=TRACK_TTL_SEC)
    deduplicator = ViolationDeduplicator()
    frame_idx = 0
    violation_count = 0
    
    if args.show:
        cv2.namedWindow("Helmet Detection", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Helmet Detection", 1280, 720)
    
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame_idx += 1
            
            # Skip frames
            if frame_idx % args.skip != 0:
                continue
            
            H, W = frame.shape[:2]
            now_ts = time.time()
            video_ts = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            
            # Detect violations using unified model
            violations, all_detections = detect_violations_unified(
                model, frame, tracker, deduplicator, now_ts, args.conf
            )
            
            # Create display frame
            display = annotate_unified_frame(frame, all_detections, violations)
            
            # Log detection info
            det_info = f"({len(all_detections.get('person_boxes', []))}p, {len(all_detections.get('motorcycle_boxes', []))}m)"
            
            if violations:
                print(f"\n[Frame {frame_idx}] ⚠️  {len(violations)} violation(s) {det_info}")
            elif frame_idx % 100 == 0:
                print(f"[Progress] Frame {frame_idx}/{total_frames} ({100*frame_idx/max(1,total_frames):.1f}%) | Violations: {violation_count}")
            
            # Handle violations
            for violation_info in violations:
                violation_count += 1
                
                track_id = violation_info['track_id']
                confidence = violation_info['confidence']
                method = violation_info.get('method', 'unknown')
                
                # Draw violation on display
                box = violation_info['box']
                draw_box(display, box, f"NO HELMET {track_id}", color=(0, 0, 255), thickness=3)
                
                print(f"[VIOLATION #{violation_count}] Frame {frame_idx} | Time {video_ts:.2f}s | "
                      f"Track {track_id} | Conf: {confidence:.2f} | Method: {method}")
                
                # Save image
                filename = f"helmet_{uuid.uuid4()}.jpg"
                filepath = os.path.join(OUTPUT_DIR, filename)
                cv2.imwrite(filepath, display)
            
            # Show frame
            if args.show:
                cv2.putText(display, f"Frame: {frame_idx}/{total_frames}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(display, f"Violations: {violation_count}", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.putText(display, f"Camera: {args.camera}", (W - 200, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.putText(display, "UNIFIED MODEL (best.pt)", (10, H - 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                
                cv2.imshow("Helmet Detection", display)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
    
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")
    
    finally:
        cap.release()
        if args.show:
            cv2.destroyAllWindows()
        
        print(f"\n{'='*60}")
        print("Detection Complete!")
        print(f"  Model: best.pt (Unified)")
        print(f"  Total frames: {frame_idx}")
        print(f"  Violations detected: {violation_count}")
        print(f"  Output directory: {OUTPUT_DIR}")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
