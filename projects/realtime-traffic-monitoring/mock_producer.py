import os
import time
import json
from datetime import datetime
from kafka import KafkaProducer
from kafka.errors import KafkaError
import glob

# ==========================
# CẤU HÌNH
# ==========================
# Hỗ trợ cả chạy local (Windows) và trong Docker
IMAGE_DIR = os.getenv('IMAGE_DIR', '/opt/airflow/projects/realtime-traffic-monitoring/images')
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
KAFKA_TOPIC = 'camera_raw_frames'
INTERVAL = 3  # giây

# ==========================
# KAFKA PRODUCER SETUP
# ==========================
def create_producer():
    """Tạo Kafka Producer với retry"""
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
                time.sleep(3)
            else:
                raise

# ==========================
# MAIN
# ==========================
def main():
    producer = create_producer()
    
    # Tìm tất cả ảnh trong tất cả thư mục camera
    image_paths = []
    for pattern in ['**/*.jpg', '**/*.jpeg', '**/*.png']:
        image_paths.extend(glob.glob(os.path.join(IMAGE_DIR, pattern), recursive=True))
    
    if not image_paths:
        print(f"✗ Không tìm thấy ảnh nào trong {IMAGE_DIR}")
        print(f"  Thử tìm trong: {os.listdir(IMAGE_DIR) if os.path.exists(IMAGE_DIR) else 'Dir not found'}")
        return
    
    # Sắp xếp theo tên
    image_paths = sorted(image_paths)
    
    print(f"\n{'='*60}")
    print(f"Mock Producer - Topic: {KAFKA_TOPIC}")
    print(f"Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"Số ảnh: {len(image_paths)} | Interval: {INTERVAL}s")
    print(f"{'='*60}\n")
    
    try:
        idx = 0
        while True:
            # Lấy ảnh theo vòng lặp
            img_path = image_paths[idx % len(image_paths)]
            filename = os.path.basename(img_path)
            
            # Lấy camera_id từ thư mục cha
            camera_id = os.path.basename(os.path.dirname(img_path))
            
            # Tạo message
            message = {
                "camera_id": camera_id,
                "timestamp": datetime.now().isoformat(),
                "image_path": img_path,
                "filename": filename
            }
            
            # Gửi tới Kafka
            future = producer.send(KAFKA_TOPIC, value=message)
            record_metadata = future.get(timeout=10)
            
            print(f"✓ [{idx+1}] Sent: {camera_id}/{filename}")
            print(f"   Partition={record_metadata.partition}, Offset={record_metadata.offset}")
            
            idx += 1
            time.sleep(INTERVAL)
    
    except KeyboardInterrupt:
        print("\n\n🛑 Dừng Mock Producer...")
    finally:
        producer.flush()
        producer.close()
        print("✓ Đã đóng kết nối Kafka")

if __name__ == "__main__":
    main()
