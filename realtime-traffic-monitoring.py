import os
import time
import requests
from datetime import datetime

# ==========================
# CẤU HÌNH
# ==========================
OUTPUT_DIR = r".\images"

# Thời gian lấy ảnh (giây) – CHỈ CHỈNH CHỖ NÀY
INTERVAL = 10   # ví dụ: 10 giây / ảnh / mỗi camera

# Danh sách camera
CAMERAS = [
    {"id": "662b83ff1afb9c00172dcffb", "name": "pasteur_le_duan"},
    {"id": "5deb576d1dc17d7c5515ad03", "name": "nam_ky_khoi_nghia_nguyen_dinh_chieu"},
    {"id": "58af8d68bd82540010390c2e", "name": "nam_ky_khoi_nghia_dien_bien_phu"},
    {"id": "662b83381afb9c00172dcf88", "name": "hai_ba_trung_nguyen_dinh_chieu"},
    {"id": "5deb576d1dc17d7c5515ad15", "name": "ly_tu_trong_chu_manh_trinh"},
    {"id": "662b4de41afb9c00172d85c5", "name": "hai_thuong_lan_ong_chau_van_liem"},
]

BASE_URL = "https://giaothong.hochiminhcity.gov.vn:8007/Render/CameraHandler.ashx"
HOME_URL = "https://giaothong.hochiminhcity.gov.vn/"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==========================
# TẠO SESSION GIỐNG TRÌNH DUYỆT
# ==========================
session = requests.Session()

session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120 Safari/537.36",
    "Referer": "https://giaothong.hochiminhcity.gov.vn/",
})

print("Đang lấy cookie...")
session.get(HOME_URL, timeout=10)
print("Cookie đã lấy:", session.cookies.get_dict())


# ==========================
# HÀM LẤY ẢNH TỪ 1 CAMERA
# ==========================
def fetch_and_save(camera: dict):
    cam_id = camera["id"]
    cam_name = camera.get("name") or cam_id

    timestamp = int(time.time() * 1000)

    params = {
        "id": cam_id,
        "bg": "black",
        "h": 320,
        "w": 550,
        "t": timestamp,
    }

    try:
        r = session.get(BASE_URL, params=params, timeout=10)
        print(f"[{cam_name}] URL gọi:", r.url)
        r.raise_for_status()

        # mỗi camera 1 folder riêng
        cam_dir = os.path.join(OUTPUT_DIR, cam_name)
        os.makedirs(cam_dir, exist_ok=True)

        filename = f"{cam_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = os.path.join(cam_dir, filename)

        with open(filepath, "wb") as f:
            f.write(r.content)

        print(f"[{cam_name}] Đã lưu: {filepath}")

    except Exception as e:
        print(f"[{cam_name}] Lỗi tải ảnh:", e)


# ==========================
# MAIN LOOP
# ==========================
print(f"Bắt đầu tải ảnh từ {len(CAMERAS)} camera mỗi {INTERVAL} giây...")
print("Nhấn Ctrl + C để dừng.")

while True:
    start = time.time()

    for cam in CAMERAS:
        fetch_and_save(cam)

    elapsed = time.time() - start
    sleep_time = max(0, INTERVAL - elapsed)

    time.sleep(sleep_time)
