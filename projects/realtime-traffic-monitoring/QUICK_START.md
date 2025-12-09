# 🚀 Quick Start: Real-Time Traffic Violation Monitoring

Hướng dẫn chạy nhanh hệ thống giám sát vi phạm giao thông chỉ trong 5 phút.

## 1. Yêu cầu (Prerequisites)

- **Docker** & **Docker Compose** đã được cài đặt.
- **RAM**: Tối thiểu 8GB (khuyên dùng 16GB).

## 2. Cài đặt & Khởi động (Installation & Startup)

Chạy các lệnh sau tại thư mục gốc của project (`cardiac_prediction`):

```bash
# 1. Build Docker images (Lần đầu tiên sẽ mất 5-10 phút)
docker-compose build

# 2. Khởi động hệ thống
docker-compose up -d

# 3. Fix quyền thư mục images (Để tránh lỗi Permission denied)
docker-compose exec airflow-worker bash -c "mkdir -p /opt/airflow/projects/realtime-traffic-monitoring/images && chmod -R 777 /opt/airflow/projects/realtime-traffic-monitoring/images"
```

## 3. Kích hoạt Pipeline (Trigger Pipeline)

1. Truy cập **Airflow UI**: http://localhost:8080 (User/Pass: `airflow`/`airflow`)
2. Tìm DAG: `traffic_monitoring_full_pipeline`
3. Bật DAG (Toggle switch **ON**)
4. Bấm nút **Trigger DAG** (nút ▶️ ở cột Actions)

Sau khi trigger, Airflow sẽ chạy các task:

- `check_health`: Kiểm tra Kafka/DB.
- `start_producer`: Lấy ảnh từ camera.
- `start_spark`: Xử lý AI phát hiện vi phạm.
- `start_db_consumer`: Lưu kết quả vào DB.

## 4. Xem Kết Quả (View Dashboard)

Truy cập **Streamlit Dashboard**:
👉 **http://localhost:8501**

- **Live Camera Feed**: Xem ảnh realtime từ camera.
- **Raw Feed**: Bật checkbox "Show Raw Camera Feed" ở sidebar để xem ảnh ngay cả khi chưa có vi phạm.
- **Recent Violations**: Danh sách xe vi phạm (vượt vạch, đèn đỏ).

---

## 5. Troubleshooting (Sửa lỗi nhanh)

### Dashboard không hiện ảnh?

- Bật checkbox **"Show Raw Camera Feed"**.
- Kiểm tra producer có chạy không:
  ```bash
  docker-compose logs -f traffic-monitoring-producer
  ```

### Lỗi Permission denied?

- Chạy lại lệnh fix quyền:
  ```bash
  docker-compose exec airflow-worker chmod -R 777 /opt/airflow/projects/realtime-traffic-monitoring/images/
  ```

### Muốn test dữ liệu giả lập (Mock Data)?

Nếu API camera thực tế bị lỗi, chạy script giả lập:

```bash
docker-compose exec -d airflow-worker bash -c "cd /opt/airflow/projects/realtime-traffic-monitoring && python mock_producer.py"
```

### Reset hệ thống?

Nếu gặp lỗi lạ, hãy reset toàn bộ để chạy lại từ đầu:

```bash
docker-compose down -v  # Xóa cả volumes data cũ
docker-compose up -d
```
