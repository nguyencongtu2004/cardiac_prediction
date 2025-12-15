import cv2
import json

IMG_PATH = r"C:\Users\LENOVO\Desktop\cardiac_prediction\projects\realtime-traffic-monitoring\images\pasteur_le_duan\pasteur_le_duan_20251209_064024.jpg"          # ảnh mẫu
ROI_JSON = r"C:\Users\LENOVO\Desktop\cardiac_prediction\projects\realtime-traffic-monitoring\test_roi.json"                  # file sẽ lưu

img = cv2.imread(IMG_PATH)
h, w = img.shape[:2]
print(f"Image size: {w}×{h}")

# ---- 1️⃣ Chọn stop line (hai điểm) ----
print("\n--- Click 2 points for STOP LINE ---")
pts = cv2.selectROI("Select stop line (drag a thin rectangle)", img, fromCenter=False, showCrosshair=True)
# selectROI trả về (x, y, w, h) – chúng ta chỉ cần 2 điểm:
x1, y1, w1, h1 = pts
stop_line = [[x1, y1], [x1 + w1, y1 + h1]]
cv2.destroyAllWindows()

# ---- 2️⃣ Chọn traffic‑light ROI (hình chữ nhật) ----
print("\n--- Drag a rectangle around the TRAFFIC LIGHT ---")
x, y, w, h = cv2.selectROI("Traffic light ROI", img, fromCenter=False, showCrosshair=True)
traffic_light_roi = [int(x), int(y), int(x + w), int(y + h)]
cv2.destroyAllWindows()

# ---- 3️⃣ Ghi vào file JSON ----
config = {
    "my_camera_id": {
        "stop_line": stop_line,
        "traffic_light_roi": traffic_light_roi
    }
}
with open(ROI_JSON, "w") as f:
    json.dump(config, f, indent=4)
print(f"Saved ROI to {ROI_JSON}")