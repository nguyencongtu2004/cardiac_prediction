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
MODEL_PATH = "../config/yolo/yolov8n.pt"  # Tự động tải nếu chưa có
IMAGE_DIR = r"../images/pasteur_le_duan"  # Folder chứa ảnh tải về
ROI_CONFIG_PATH = "../config/roi.json"
OUTPUT_DIR = "../inference_results"

# Load Config
if os.path.exists(ROI_CONFIG_PATH):
    with open(ROI_CONFIG_PATH, "r") as f:
        config = json.load(f)
        ROI_CONFIG = config.get("pasteur_le_duan", {})
else:
    print(f"Warning: {ROI_CONFIG_PATH} not found. Using empty config.")
    ROI_CONFIG = {}

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
    
    # Tạo folder output
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Lấy danh sách ảnh
    image_paths = glob.glob(os.path.join(IMAGE_DIR, "*.jpg"))
    if not image_paths:
        print(f"Không tìm thấy ảnh nào trong {IMAGE_DIR}. Hãy chạy script lấy ảnh trước (ví dụ: mock_producer.py)!")
        return

    print(f"Tìm thấy {len(image_paths)} ảnh. Bắt đầu xử lý...")

    # for img_path in image_paths[:10]: # Test 10 ảnh đầu tiên
    for img_path in image_paths:
        filename = os.path.basename(img_path)
        print(f"Processing {filename}...")
        
        frame = cv2.imread(img_path)
        if frame is None:
            continue

        # Inference
        results = model(frame, verbose=False)
        result = results[0] # Chỉ lấy kết quả đầu tiên (batch=1)

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

        # Check Violations using SHARED LOGIC
        violations = traffic_logic.process_violations(detections, ROI_CONFIG, frame=frame)
        
        # Determine global TL state for drawing (hacky, just extract from first violation or re-detect)
        # For visualization, let's re-run just the color check on ROI if violations is empty to show state
        tl_state = 'UNKNOWN'
        if violations:
            tl_state = violations[0].get('traffic_light_state', 'UNKNOWN')
        else:
            # Quick check to show state even if no violation
            if ROI_CONFIG.get("traffic_light_roi"):
                 x1, y1, x2, y2 = ROI_CONFIG.get("traffic_light_roi")
                 crop = frame[y1:y2, x1:x2]
                 tl_state = traffic_logic.detect_traffic_light_color(crop)

        # Draw ROI and State
        frame = draw_roi(frame, ROI_CONFIG, tl_state)

        # Highlight Violations
        if violations:
            cv2.putText(frame, "VIOLATION DETECTED!", (50, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
            for v in violations:
                print(f"  !!! VIOLATION: {v['type']} - {v['vehicle']}")
                # Draw heavier box around violator
                # Need to find the bbox again or pass it through. 
                # For now just text is enough.

        # Lưu ảnh kết quả
        out_path = os.path.join(OUTPUT_DIR, "detected_" + filename)
        cv2.imwrite(out_path, frame)
        print(f"  -> Saved to {out_path} (State: {tl_state})")

    print(f"\nHoàn tất! Kiểm tra folder '{OUTPUT_DIR}'.")

if __name__ == "__main__":
    run_inference()
