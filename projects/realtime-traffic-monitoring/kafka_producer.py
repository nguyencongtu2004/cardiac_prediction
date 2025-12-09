import os
import time
import json
import base64
import requests
from datetime import datetime
from kafka import KafkaProducer
from kafka.errors import KafkaError

# ==========================
# CẤU HÌNH
# ==========================
OUTPUT_DIR = r"/opt/airflow/projects/realtime-traffic-monitoring/images"
INTERVAL = 10  # giây

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
KAFKA_TOPIC = 'camera_raw_frames'

# Danh sách camera (focus vào pasteur_le_duan cho test)
CAMERAS = [
    {"id": "662b83ff1afb9c00172dcffb", "name": "pasteur_le_duan"},
    {"id": "582e95d2a978d8001d60eacd", "name": "nguyen_thi_minh_khai"},
    {"id": "5826a04b061dda001b6fc009", "name": "hai_ba_trung"},
    {"id": "582e952aa978d8001d60eacc", "name": "nam_ky_khoi_nghia"},
]

BASE_URL = "https://giaothong.hochiminhcity.gov.vn:8007/Render/CameraHandler.ashx"
HOME_URL = "https://giaothong.hochiminhcity.gov.vn/"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==========================
# KAFKA PRODUCER SETUP
# ==========================
def create_producer():
    """Tạo Kafka Producer với retry logic"""
    retries = 5
    for i in range(retries):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',
                retries=3
            )
            print(f"✓ Kết nối Kafka thành công tại {KAFKA_BOOTSTRAP_SERVERS}")
            return producer
        except KafkaError as e:
            print(f"✗ Lần {i+1}/{retries}: Không thể kết nối Kafka - {e}")
            if i < retries - 1:
                time.sleep(5)
            else:
                raise Exception("Không thể kết nối tới Kafka sau nhiều lần thử")

# ==========================
# SESSION GIỐNG TRÌNH DUYỆT
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
# HÀM LẤY ẢNH VÀ GỬI KAFKA
# ==========================
def fetch_and_produce(camera: dict, producer: KafkaProducer):
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
        r = session.get(BASE_URL, params=params, timeout=30)
        print(f"[{cam_name}] URL gọi:", r.url)
        r.raise_for_status()

        # Lưu ảnh vào disk (backup) - với xử lý permission
        cam_dir = os.path.join(OUTPUT_DIR, cam_name)
        filepath = None
        
        try:
            # Tạo thư mục với full permissions
            os.makedirs(cam_dir, mode=0o777, exist_ok=True)
            # Đảm bảo thư mục có thể ghi được
            if not os.access(cam_dir, os.W_OK):
                # Thử chmod nếu không có quyền ghi
                try:
                    os.chmod(cam_dir, 0o777)
                except OSError:
                    pass
            
            filename = f"{cam_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            filepath = os.path.join(cam_dir, filename)
            
            with open(filepath, "wb") as f:
                f.write(r.content)
            print(f"[{cam_name}] ✓ Đã lưu: {filepath}")
            
        except PermissionError as pe:
            # Fallback: Lưu vào /tmp nếu không có quyền
            fallback_dir = f"/tmp/traffic_images/{cam_name}"
            os.makedirs(fallback_dir, exist_ok=True)
            filename = f"{cam_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            filepath = os.path.join(fallback_dir, filename)
            
            with open(filepath, "wb") as f:
                f.write(r.content)
            print(f"[{cam_name}] ⚠️ Permission issue, saved to fallback: {filepath}")
        except Exception as save_error:
            # Nếu không thể lưu file, vẫn gửi Kafka với image_base64
            print(f"[{cam_name}] ⚠️ Cannot save file: {save_error}, sending base64 instead")
            filepath = None


        # Chuẩn bị message cho Kafka
        message = {
            "camera_id": cam_name,
            "timestamp": datetime.now().isoformat(),
            "image_path": filepath,  # Đường dẫn file trong container
            # Optional: Base64 encode nếu cần gửi ảnh trực tiếp
            # "image_base64": base64.b64encode(r.content).decode('utf-8')
        }

        # Gửi message tới Kafka
        future = producer.send(KAFKA_TOPIC, value=message)
        record_metadata = future.get(timeout=10)
        
        print(f"[{cam_name}] ✓ Đã gửi Kafka: Topic={record_metadata.topic}, Partition={record_metadata.partition}, Offset={record_metadata.offset}")

    except Exception as e:
        print(f"[{cam_name}] ✗ Lỗi: {e}")
        return  # Skip this iteration and continue

# ==========================
# MAIN LOOP
# ==========================
def main():
    producer = create_producer()
    
    print(f"\n{'='*60}")
    print(f"Bắt đầu Producer - Topic: {KAFKA_TOPIC}")
    print(f"Camera: {len(CAMERAS)} | Interval: {INTERVAL}s")
    print(f"{'='*60}\n")
    print("Nhấn Ctrl + C để dừng.")
    
    try:
        while True:
            start = time.time()
            
            for cam in CAMERAS:
                fetch_and_produce(cam, producer)
            
            elapsed = time.time() - start
            sleep_time = max(0, INTERVAL - elapsed)
            
            if sleep_time > 0:
                print(f"⏱️  Chờ {sleep_time:.1f}s trước lần tiếp theo...\n")
                time.sleep(sleep_time)
    
    except KeyboardInterrupt:
        print("\n\n🛑 Dừng Producer...")
    finally:
        producer.flush()
        producer.close()
        print("✓ Đã đóng kết nối Kafka")

if __name__ == "__main__":
    main()
