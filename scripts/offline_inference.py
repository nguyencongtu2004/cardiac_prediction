import cv2
import json
import os
import glob
from ultralytics import YOLO
import numpy as np
try:
    from core import traffic_logic
except ImportError:
    # Handle case where script is run from a different directory
    import sys
    # Add project root to sys.path (parent of scripts/)
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core import traffic_logic

# ==========================
# CẤU HÌNH
# ==========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "config", "yolo", "yolov8n.pt")
MODEL_PATH = os.path.join(BASE_DIR, "config", "yolo", "yolov8n.pt")
IMAGES_ROOT = os.path.join(BASE_DIR, "images")
ROI_CONFIG_PATH = os.path.join(BASE_DIR, "config", "roi.json")
OUTPUT_ROOT = os.path.join(BASE_DIR, "inference_results")

# Load Global Config
FULL_CONFIG = {}
if os.path.exists(ROI_CONFIG_PATH):
    with open(ROI_CONFIG_PATH, "r") as f:
        FULL_CONFIG = json.load(f)
else:
    print(f"Warning: {ROI_CONFIG_PATH} not found. Using empty config.")

# Map class names (COCO dataset)
# 2: car, 3: motorcycle, 5: bus, 7: truck, 9: traffic light
TARGET_CLASSES = [2, 3, 5, 7, 9]

# ==========================
# HÀM XỬ LÝ
# ==========================
def draw_roi(img, config, traffic_light_state="UNKNOWN"):
    stop_line = config.get("stop_line", [])
    tl_roi = config.get("traffic_light_roi", [])
    
    # Vẽ Stop Line
    if stop_line:
        pts = np.array(stop_line, np.int32)
        pts = pts.reshape((-1, 1, 2))
        cv2.polylines(img, [pts], False, (0, 0, 255), 2)
        cv2.putText(img, "STOP LINE", (stop_line[0][0], stop_line[0][1] - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    # Vẽ Traffic Light Zone
    if tl_roi:
        x1, y1, x2, y2 = tl_roi
        # Color based on state
        color = (0, 255, 255) # Yellow default
        if traffic_light_state == 'RED': color = (0, 0, 255)
        elif traffic_light_state == 'GREEN': color = (0, 255, 0)
        
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        cv2.putText(img, f"TL: {traffic_light_state}", (x1, y1 - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return img

def run_inference():
    # Load Model
    print("Loading YOLOv8 model...")
    model = YOLO(MODEL_PATH)

    # Get all camera folders
    if not os.path.exists(IMAGES_ROOT):
        print(f"Image root not found: {IMAGES_ROOT}")
        return

    camera_folders = [d for d in os.listdir(IMAGES_ROOT) if os.path.isdir(os.path.join(IMAGES_ROOT, d))]
    
    if not camera_folders:
        print(f"No camera folders found in {IMAGES_ROOT}")
        return

    print(f"Found {len(camera_folders)} cameras: {camera_folders}")

    for camera_id in camera_folders:
        print(f"\n{'='*30}")
        print(f"PROCESSING CAMERA: {camera_id}")
        print(f"{'='*30}")

        # Config cho camera này
        roi_config = FULL_CONFIG.get(camera_id, {})
        
        # Paths
        cam_image_dir = os.path.join(IMAGES_ROOT, camera_id)
        cam_output_dir = os.path.join(OUTPUT_ROOT, camera_id)
        os.makedirs(cam_output_dir, exist_ok=True)

        # Lấy danh sách ảnh
        image_paths = glob.glob(os.path.join(cam_image_dir, "*.jpg"))
        if not image_paths:
            print(f"  No images found in {cam_image_dir}")
            continue
        
        print(f"  Found {len(image_paths)} images.")

        for img_path in image_paths:
            filename = os.path.basename(img_path)
            # print(f"  Processing {filename}...")
            
            frame = cv2.imread(img_path)
            if frame is None:
                continue

            # Inference
            results = model(frame, verbose=False)
            result = results[0]

            detections = []
            
            # Parse detections
            for box in result.boxes:
                cls_id = int(box.cls[0])
                if cls_id in TARGET_CLASSES:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0])
                    cx = (x1 + x2) / 2
                    cy = (y1 + y2) / 2
                    
                    det = {
                        "class_id": cls_id,
                        "class_name": model.names[cls_id],
                        "confidence": conf,
                        "bbox": [x1, y1, x2, y2],
                        "center": [cx, cy]
                    }
                    detections.append(det)

                    # Draw raw detection
                    color = (0, 255, 0) if cls_id != 9 else (0, 255, 255)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(frame, f"{det['class_name']} {conf:.2f}", (x1, y1 - 5), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

            # Check Violations
            violations = traffic_logic.process_violations(detections, roi_config, frame=frame)
            
            # Determine global TL state
            tl_state = 'UNKNOWN'
            if violations:
                tl_state = violations[0].get('traffic_light_state', 'UNKNOWN')
            else:
                if roi_config.get("traffic_light_roi"):
                        x1, y1, x2, y2 = roi_config.get("traffic_light_roi")
                        crop = frame[y1:y2, x1:x2]
                        tl_state = traffic_logic.detect_traffic_light_color(crop)

            # Draw ROI and State
            frame = draw_roi(frame, roi_config, tl_state)

            # Highlight Violations
            if violations:
                cv2.putText(frame, "VIOLATION DETECTED!", (50, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
                for v in violations:
                    print(f"  !!! VIOLATION [{camera_id}]: {v['type']} - {v['vehicle']} ({filename})")

            # Lưu ảnh kết quả
            out_path = os.path.join(cam_output_dir, "detected_" + filename)
            cv2.imwrite(out_path, frame)
            # print(f"  -> Saved to {out_path}")

    print(f"\nAll done! Check folder '{OUTPUT_ROOT}'.")

if __name__ == "__main__":
    run_inference()
