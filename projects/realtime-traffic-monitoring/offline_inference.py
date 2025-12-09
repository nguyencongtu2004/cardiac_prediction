import cv2
import json
import os
import glob
from ultralytics import YOLO
import numpy as np

# ==========================
# CẤU HÌNH
# ==========================
MODEL_PATH = "yolov8n.pt"  # Tự động tải nếu chưa có
IMAGE_DIR = r".\images\pasteur_le_duan"  # Folder chứa ảnh tải về
ROI_CONFIG_PATH = "roi.json"
OUTPUT_DIR = "inference_results"

# Load Config
with open(ROI_CONFIG_PATH, "r") as f:
    config = json.load(f)
    cam_config = config.get("pasteur_le_duan", {})

STOP_LINE = cam_config.get("stop_line", [])
TRAFFIC_LIGHT_ROI = cam_config.get("traffic_light_roi", []) # [x1, y1, x2, y2]

# Map class names (COCO dataset)
# 2: car, 3: motorcycle, 5: bus, 7: truck, 9: traffic light
TARGET_CLASSES = [2, 3, 5, 7, 9]

# ==========================
# HÀM XỬ LÝ
# ==========================
def draw_roi(img):
    # Vẽ Stop Line
    if STOP_LINE:
        pts = np.array(STOP_LINE, np.int32)
        pts = pts.reshape((-1, 1, 2))
        cv2.polylines(img, [pts], False, (0, 0, 255), 2)
        cv2.putText(img, "STOP LINE", (STOP_LINE[0][0], STOP_LINE[0][1] - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    # Vẽ Traffic Light Zone
    if TRAFFIC_LIGHT_ROI:
        x1, y1, x2, y2 = TRAFFIC_LIGHT_ROI
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 255), 2)
        cv2.putText(img, "TRAFFIC LIGHT", (x1, y1 - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
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
        print(f"Không tìm thấy ảnh nào trong {IMAGE_DIR}. Hãy chạy script lấy ảnh trước!")
        return

    print(f"Tìm thấy {len(image_paths)} ảnh. Bắt đầu xử lý...")

    for img_path in image_paths[:5]: # Test 5 ảnh đầu tiên
        filename = os.path.basename(img_path)
        print(f"Processing {filename}...")
        
        frame = cv2.imread(img_path)
        if frame is None:
            continue

        # Inference
        results = model(frame, verbose=False)
        result = results[0] # Chỉ lấy kết quả đầu tiên (batch=1)

        # Vẽ Bounding Box cho các object quan tâm
        for box in result.boxes:
            cls_id = int(box.cls[0])
            if cls_id in TARGET_CLASSES:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                label = f"{model.names[cls_id]} {conf:.2f}"
                
                # Màu sắc: Đỏ cho xe, Vàng cho đèn
                color = (0, 255, 0) if cls_id != 9 else (0, 255, 255)
                
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, label, (x1, y1 - 5), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        # Vẽ ROI
        frame = draw_roi(frame)

        # Lưu ảnh kết quả
        out_path = os.path.join(OUTPUT_DIR, "detected_" + filename)
        cv2.imwrite(out_path, frame)
        print(f"Đã lưu: {out_path}")

    print("Hoàn tất! Kiểm tra folder 'inference_results'.")

if __name__ == "__main__":
    run_inference()
