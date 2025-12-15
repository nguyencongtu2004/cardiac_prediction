# Báo Cáo Tiến Độ Đồ Án

## Hệ Thống Giám Sát Vi Phạm Giao Thông Thời Gian Thực

---

## Slide 1: Tổng Quan Đồ Án

### 🎯 Mục Tiêu

Xây dựng hệ thống tự động phát hiện và giám sát vi phạm giao thông theo thời gian thực sử dụng AI và công nghệ Big Data.

### 🔍 Tính Năng Chính

- **Phát hiện vi phạm tự động** bằng YOLOv8 (vượt vạch dừng, vượt đèn đỏ)
- **Xử lý luồng dữ liệu thời gian thực** từ camera giao thông TP.HCM
- **Dashboard trực quan** hiển thị vi phạm real-time
- **Lưu trữ và phân tích** dữ liệu vi phạm

### 💻 Tech Stack

| Thành phần            | Công nghệ            |
| --------------------- | -------------------- |
| **Orchestration**     | Apache Airflow 2.9.0 |
| **Stream Processing** | Apache Spark 3.5.1   |
| **Message Queue**     | Apache Kafka 7.5.0   |
| **Database**          | PostgreSQL 13        |
| **AI Detection**      | YOLOv8               |
| **Backend**           | FastAPI + WebSocket  |
| **Frontend**          | Next.js 16           |
| **Deployment**        | Docker Compose       |

---

## Slide 2: Kiến Trúc & Luồng Dữ Liệu

### 📐 Kiến Trúc Hệ Thống

```
Camera API → Kafka Producer → [Kafka: camera_raw_frames]
                                        ↓
                              Spark Streaming + YOLOv8
                                        ↓
                              [Kafka: traffic_violations]
                                   ↙         ↘
                        DB Consumer      FastAPI Backend
                              ↓                  ↓
                        PostgreSQL          Next.js Dashboard
```

### 🔄 Pipeline Xử Lý (4 Bước)

**1. Data Collection** (`kafka_producer.py`)

- Lấy ảnh từ camera giao thông TP.HCM mỗi 10 giây
- Gửi metadata vào Kafka topic `camera_raw_frames`

**2. AI Detection** (`spark_processor.py`)

- Spark Streaming tiêu thụ dữ liệu từ Kafka
- YOLOv8 phát hiện: xe (car, motorcycle, bus, truck) + đèn giao thông
- Logic phát hiện vi phạm dựa trên ROI (Region of Interest)
- Gửi vi phạm vào topic `traffic_violations`

**3. Data Persistence** (`db_consumer.py`)

- Batch insert vi phạm vào PostgreSQL
- Lưu trữ metadata: camera_id, loại vi phạm, loại xe, độ tin cậy, timestamp

**4. Visualization** (Next.js Frontend + FastAPI Backend)

- WebSocket real-time cho cập nhật vi phạm tức thì
- Dashboard hiển thị: thống kê, danh sách vi phạm, camera hoạt động

---

## Slide 3: Kết Quả Đạt Được & Demo

### ✅ Hoàn Thành

#### **Giai đoạn 1: Proof of Concept** ✓

- ✅ YOLOv8 detection model hoạt động ổn định
- ✅ Logic phát hiện vi phạm vạch dừng
- ✅ Cấu hình ROI cho camera

#### **Giai đoạn 2: Big Data Pipeline** ✓

- ✅ Kafka cluster (Zookeeper + Kafka broker)
- ✅ Spark Streaming với YOLO integration
- ✅ 2 Kafka topics: `camera_raw_frames`, `traffic_violations`
- ✅ PostgreSQL database schema đầy đủ
- ✅ Airflow DAG orchestration (8 tasks)

#### **Giai đoạn 3: Web Application** ✓

- ✅ FastAPI backend với WebSocket
- ✅ Next.js frontend với real-time updates
- ✅ Dark theme dashboard hiện đại
- ✅ Docker Compose deployment hoàn chỉnh

### 📊 Hiệu Suất Hệ Thống

- **Throughput**: 4 cameras @ 10s interval
- **YOLO Inference**: ~30ms/frame (CPU)
- **Spark Processing**: Batch mỗi 5 giây
- **WebSocket Latency**: <100ms
- **End-to-end Latency**: 2-3 giây (từ camera → dashboard)

### 🎥 Demo

**Truy cập hệ thống:**

- Airflow UI: http://localhost:8080 (quản lý pipeline)
- Dashboard: http://localhost:3000 (xem vi phạm real-time)

**Các service đang chạy:**

```bash
✓ Kafka & Zookeeper
✓ PostgreSQL
✓ Airflow (webserver, scheduler, worker, triggerer)
✓ Traffic Producer (Kafka producer)
✓ FastAPI Backend
✓ Next.js Frontend
```

### 🔮 Hướng Phát Triển Tiếp Theo

**Ngắn hạn:**

- [ ] Phát hiện vượt đèn đỏ (traffic light state detection)
- [ ] Nhận diện biển số xe (License Plate Recognition)
- [ ] Thêm nhiều camera từ các ngã tư khác

**Dài hạn:**

- [ ] Fine-tune YOLOv8 trên dataset giao thông Việt Nam
- [ ] Multi-worker Spark cluster để mở rộng quy mô
- [ ] Mobile app cho CSGT
- [ ] Email/SMS alerts tự động

---

## 🙏 Cảm ơn!

**Demo sẵn sàng - Mời thầy/cô xem hệ thống hoạt động!**

💡 **Lưu ý**: Tất cả source code và documentation có trên GitHub
📧 **Contact**: [Your Email]
🔗 **Repository**: [GitHub Link]
