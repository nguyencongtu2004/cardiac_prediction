"""
detect_helmet_violation.py - Helmet Violation Detection (Standalone)
=====================================================================
Phát hiện người đi xe máy không đội mũ bảo hiểm.
Sử dụng shared detection logic từ pipeline.detectors.

Usage:
    python scripts/detect_helmet_violation.py --video data/video/cam4.mp4 --show --skip 3
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
    get_output_layer_names, detect_helmets, detect_persons_and_bikes,
    associate_riders, check_helmet_violation, annotate_helmet_frame,
    HEAD_RATIO
)


# =========================
# CONFIG
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "violations", "helmet")
DATA_DIR = os.path.join(BASE_DIR, "data")

DEFAULT_VIDEO = os.path.join(DATA_DIR, "video/bike-test.mp4")
YOLOV8_WEIGHTS = os.path.join(MODELS_DIR, "yolov8n.pt")
HELMET_CFG = os.path.join(MODELS_DIR, "yolov3-helmet.cfg")
HELMET_WEIGHTS = os.path.join(MODELS_DIR, "yolov3-helmet.weights")

# Detection settings
CONF_THRES = 0.5
NMS_THRES = 0.4
INPUT_SIZE = 416
TRACK_MAX_DIST = 80
TRACK_TTL_SEC = 1.0
SAVE_COOLDOWN_SEC = 2.0

os.makedirs(OUTPUT_DIR, exist_ok=True)


# =========================
# MAIN
# =========================
def main():
    parser = argparse.ArgumentParser(description='Helmet Violation Detection')
    parser.add_argument('--video', type=str, default=DEFAULT_VIDEO, help='Path to video file')
    parser.add_argument('--show', action='store_true', help='Show real-time display')
    parser.add_argument('--camera', type=str, default='default', help='Camera ID')
    parser.add_argument('--skip', type=int, default=1, help='Process every N-th frame')
    args = parser.parse_args()
    
    # 1. Load YOLOv3 Helmet
    print("[INFO] Loading YOLOv3 (Helmet)...")
    if not os.path.exists(HELMET_CFG) or not os.path.exists(HELMET_WEIGHTS):
        print(f"Error: Helmet model files missing: {HELMET_CFG} or {HELMET_WEIGHTS}")
        return
    
    helmet_net = cv2.dnn.readNetFromDarknet(HELMET_CFG, HELMET_WEIGHTS)
    helmet_net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
    helmet_net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
    helmet_out = get_output_layer_names(helmet_net)
    
    # 2. Load YOLOv8
    print(f"[INFO] Loading YOLOv8 from {YOLOV8_WEIGHTS}...")
    try:
        yolo8_model = YOLO(YOLOV8_WEIGHTS)
    except Exception as e:
        print(f"Error loading YOLOv8: {e}")
        return
    
    # 3. Open Video
    print(f"[INFO] Opening video: {args.video}")
    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        print(f"Error: Cannot open video: {args.video}")
        return
    
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    print(f"[INFO] FPS={fps:.2f}, Total frames={total_frames}")
    
    print(f"\n{'='*60}")
    print("Helmet Violation Detection - Started")
    print(f"Output: {OUTPUT_DIR}")
    print(f"{'='*60}\n")
    
    tracker = CentroidTracker(max_dist=TRACK_MAX_DIST, ttl_sec=TRACK_TTL_SEC)
    last_saved = {}
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
            
            # A. Detect Helmets (YOLOv3)
            helmet_boxes = detect_helmets(helmet_net, helmet_out, frame, CONF_THRES, NMS_THRES, INPUT_SIZE)
            
            # B. Detect Persons + Bikes (YOLOv8)
            persons, bikes = detect_persons_and_bikes(yolo8_model, frame, CONF_THRES)
            
            # Create display frame
            display = frame.copy()
            
            # Draw helmets (green)
            for hb in helmet_boxes:
                draw_box(display, hb, "Helmet", color=(0, 255, 0))
            
            # Draw bikes (blue)
            for b in bikes:
                draw_box(display, b, "Bike", color=(255, 150, 0))
            
            if len(persons) == 0 or len(bikes) == 0:
                if frame_idx % 100 == 0:
                    print(f"[Progress] Frame {frame_idx}/{total_frames} ({100*frame_idx/max(1,total_frames):.1f}%) | Violations: {violation_count}")
                
                if args.show:
                    cv2.imshow("Helmet Detection", display)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                continue
            
            # C. Associate Riders
            riders = associate_riders(persons, bikes)
            
            if len(riders) == 0:
                if args.show:
                    cv2.imshow("Helmet Detection", display)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                continue
            
            # D. Track Riders
            rider_boxes = [r[0] for r in riders]
            tracked = tracker.update([(box, "rider") for box in rider_boxes], now_ts)
            
            # E. Check Violations
            violations = []
            for tid, track_info in tracked.items():
                pbox = track_info["box"]
                
                # Draw rider (yellow)
                draw_box(display, pbox, f"Rider {tid}", color=(0, 255, 255))
                
                # Check for helmet
                if check_helmet_violation(pbox, helmet_boxes):
                    # Spam check
                    last = last_saved.get(tid, 0)
                    if (now_ts - last) >= SAVE_COOLDOWN_SEC:
                        violations.append((tid, pbox))
                        last_saved[tid] = now_ts
                    else:
                        # Still draw but don't save
                        draw_box(display, pbox, f"NO HELMET {tid}", color=(0, 0, 255), thickness=3)
            
            # F. Handle Violations
            for tid, pbox in violations:
                violation_count += 1
                
                # Draw violation
                draw_box(display, pbox, f"NO HELMET {tid}", color=(0, 0, 255), thickness=3)
                
                print(f"[VIOLATION #{violation_count}] Frame {frame_idx} | Time {video_ts:.2f}s | Track {tid}")
                
                # Save image
                filename = f"helmet_{uuid.uuid4()}.jpg"
                filepath = os.path.join(OUTPUT_DIR, filename)
                cv2.imwrite(filepath, display)
            
            # Progress
            if frame_idx % 100 == 0:
                print(f"[Progress] Frame {frame_idx}/{total_frames} ({100*frame_idx/max(1,total_frames):.1f}%) | Violations: {violation_count}")
            
            # Show frame
            if args.show:
                cv2.putText(display, f"Frame: {frame_idx}/{total_frames}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(display, f"Violations: {violation_count}", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.putText(display, f"Camera: {args.camera}", (W - 200, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
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
        print(f"  Total frames: {frame_idx}")
        print(f"  Violations detected: {violation_count}")
        print(f"  Output directory: {OUTPUT_DIR}")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
