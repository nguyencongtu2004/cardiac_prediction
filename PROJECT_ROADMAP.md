# Lộ Trình Phát Triển Hệ Thống Giám Sát Vi Phạm Giao Thông Thời Gian Thực (Real-Time Traffic Violation Monitoring System)

Tài liệu này mô tả chi tiết kế hoạch triển khai, từ bước thử nghiệm mô hình đến triển khai hệ thống Big Data hoàn chỉnh.

## 1. Mục Tiêu Dự Án

Xây dựng hệ thống tự động phát hiện các hành vi vi phạm giao thông từ camera đường phố (CCTV) sử dụng công nghệ Deep Learning và Big Data Processing.

- **Vi phạm chính**: Vượt đèn đỏ, đi sai làn đường, lấn vạch dừng.
- **Công nghệ cốt lõi**: YOLOv8 (Object Detection), Apache Kafka (Message Queue), Apache Spark (Stream Processing), Streamlit (Dashboard).

---

## 2. Lộ Trình Triển Khai (Roadmap)

### Giai Đoạn 1: Proof of Concept (PoC) & Core Logic (Tuần 1)

**Mục tiêu**: Chứng minh khả năng phát hiện xe và logic xử lý vi phạm trên dữ liệu tĩnh (ảnh/video lưu offline).

1.  **Chuẩn bị Dữ liệu & Môi trường**:

    - Thu thập mẫu dữ liệu từ Camera Giao Thông TP.HCM (dùng script có sẵn).
    - Cài đặt môi trường Python, CUDA (nếu có GPU) và thư viện `ultralytics` (YOLOv8).
    - Lấy mẫu ảnh các ngã tư điển hình: Pasteur - Lê Duẩn, Nam Kỳ Khởi Nghĩa.

2.  **Phát triển Module Detection (YOLOv8)**:

    - Sử dụng Pretrained Model (`yolov8n.pt` hoặc `yolov8s.pt`) để detect: `Car`, `Motorcycle`, `Bus`, `Truck`, `Traffic Light`.
    - Viết script `offline_inference.py` để chạy thử trên folder ảnh.

3.  **Xây dựng Logic Phát Hiện Vi Phạm**:
    - **Cấu hình ROI (Region of Interest)**: Xây dựng tool hoặc file config (`roi.json`) để định nghĩa tọa độ:
      - Vùng đèn giao thông (Traffic Light Zone).
      - Vạch dừng (Stop Line).
      - Vùng cấm (No Parking/Wrong Lane).
    - **Thuật toán Vượt đèn đỏ**:
      - B1: Detect trạng thái màu đèn (Red/Green) trong vùng ROI đèn.
      - B2: Nếu Đèn Đỏ + Tâm xe (Bounding Box Center) vượt qua Vạch dừng (Stop Line) $\rightarrow$ Vi phạm.

### Giai Đoạn 2: Xây dựng Big Data Pipeline (Tuần 2-3)

**Mục tiêu**: Chuyển đổi từ xử lý file tĩnh sang luồng dữ liệu thời gian thực (Real-time Streaming).

1.  **Data Ingestion (Kafka)**:

    - Cập nhật crawler camera để đẩy dữ liệu vào Kafka thay vì lưu file.
    - **Topic**: `camera_raw_frames` (chứa Camera ID, Timestamp, Image URL hoặc Base64 Image).
    - Đảm bảo `docker-compose` hoạt động ổn định với Kafka/Zookeeper.

2.  **Stream Processing (Apache Spark Structured Streaming)**:

    - Khởi tạo Spark Session với gói `spark-sql-kafka`.
    - Đọc stream từ topic `camera_raw_frames`.
    - **YOLO Wrapper for Spark**: Sử dụng **Pandas UDF** để nhúng model YOLO vào Spark để tăng hiệu năng (batch processing).
    - Áp dụng logic vi phạm (đã test ở GĐ1) vào từng batch dữ liệu.
    - Ghi kết quả vi phạm ra topic Kafka mới: `traffic_violations`.

3.  **Lưu trữ (Storage)**:
    - Lưu metadata vi phạm vào Database (PostgreSQL) để truy vấn lịch sử.
    - Lưu ảnh bằng chứng vi phạm vào Object Storage (MinIO) hoặc thư mục local được mount.

### Giai Đoạn 3: Visualization & Ứng dụng Thực tế (Tuần 4)

**Mục tiêu**: Hiển thị kết quả trực quan cho người dùng cuối (CSGT hoặc quản trị viên).

1.  **Dashboard (Streamlit)**:

    - Kết nối Kafka Consumer để nhận cảnh báo vi phạm tức thì.
    - Hiển thị Live Feed (ảnh update liên tục) kèm Bounding Box.
    - Danh sách "Vi phạm gần nhất" kèm ảnh bằng chứng.
    - Thống kê: Số lượng vi phạm theo giờ/ngày, theo Camera.

2.  **Tối ưu hóa**:
    - Điều chỉnh `TRIGGER_INTERVAL` của Spark để cân bằng độ trễ (latency) và thông lượng (throughput).
    - Xử lý các trường hợp biên (xe bị che khuất, đèn tín hiệu bị lóa).

### Giai Đoạn 4: Nâng cao & Finetune (Dài hạn)

**Mục tiêu**: Nâng cao độ chính xác đặc thù cho giao thông Việt Nam.

1.  **Fine-tuning YOLOv8**:

    - Xây dựng bộ Dataset riêng: Label lại các ảnh từ camera TP.HCM (xe máy đông đúc, xe ba gác, ninja lead...).
    - Train lại model để nhận diện tốt hơn trong điều kiện thiếu sáng hoặc mưa.
    - Label riêng class `traffic_light_red`, `traffic_light_green` thay vì dùng logic crop ảnh.

2.  **Deploy Edge**:
    - Đóng gói module Inference thành Docker Image riêng, tối ưu bằng TensorRT để chạy trên thiết bị biên (Jetson Nano) nếu cần.

### Giai Đoạn 5: Helmet Violation Detection System ✅ (Đã hoàn thành)

**Mục tiêu**: Phát hiện vi phạm không đội mũ bảo hiểm real-time qua video streaming.

1.  **Multi-Video Parallel Streaming**:

    - Quét tất cả video trong thư mục `data/video/`
    - Stream song song nhiều video cùng lúc (mỗi video = 1 thread)
    - Hỗ trợ định dạng: `.mp4`, `.avi`, `.mkv`, `.mov`

2.  **Helmet Detection Pipeline**:

    - **YOLOv3**: Phát hiện mũ bảo hiểm
    - **YOLOv8**: Phát hiện người + xe máy
    - **CentroidTracker**: Theo dõi object qua các frame
    - **Violation Logic**: Person + Motorbike + No Helmet = Vi phạm

3.  **Airflow DAGs**:

    - `helmet_demo_streaming`: Demo DAG - Producer & Detector chạy song song
    - `helmet_violation_pipeline`: Full pipeline với health checks

4.  **Modular Backend**:

    - Cấu trúc: `config.py`, `services/`, `routers/`
    - API endpoints: `/api/videos`, `/api/cameras`, `/api/violations`
    - WebSocket: `/ws` (violations), `/ws/camera` (live stream)

5.  **Component-based Frontend**:
    - `CameraViewer`: Multi-camera selection với thumbnails
    - `VideoSourceList`: Hiển thị video có sẵn
    - `StatsCard`, `ViolationCard`: Hiển thị thống kê và vi phạm

## 3. Kiến Trúc Hệ Thống (Technical Architecture)

```mermaid
graph LR
    A[Camera Streams] -->|HTTP Get| B[Data Ingestion\n(Python Script)]
    B -->|Produce| C[Kafka Topic\n'raw_frames']
    C -->|Consume| D[Apache Spark\n(Structured Streaming)]
    D -->|Inference| E[Deep Learning Model\n(YOLOv8)]
    E -->|Detection Results| D
    D -->|Logic Check| F{Violation?}
    F -->|Yes| G[Kafka Topic\n'violations']
    F -->|No| H[Discard/Log Stat]
    G -->|Consume| I[Dashboard\n(Streamlit)]
    G -->|Save| J[Database\n(PostgreSQL)]
```

## 4. Công Nghệ Sử Dụng (Tech Stack)

| Thành phần        | Công nghệ                  | Lý do chọn                                         |
| :---------------- | :------------------------- | :------------------------------------------------- |
| **Language**      | Python 3.9+                | Hỗ trợ mạnh mẽ AI & Big Data.                      |
| **Model**         | YOLOv8 (Ultralytics)       | SOTA về tốc độ/độ chính xác (Real-time).           |
| **Streaming**     | Spark Structured Streaming | Xử lý phân tán, chịu tải cao, tích hợp tốt với AI. |
| **Message Queue** | Apache Kafka               | Đệm dữ liệu tin cậy, decouple hệ thống.            |
| **Database**      | PostgreSQL                 | Lưu dữ liệu có cấu trúc (lịch sử vi phạm).         |
| **Frontend**      | Streamlit                  | Xây dựng Dashboard nhanh chóng, Python-native.     |
| **Container**     | Docker & Docker Compose    | Đóng gói môi trường, dễ triển khai.                |

## 5. Hướng Dẫn Bắt Đầu (Next Steps)

1.  Truy cập thư mục `projects/realtime-traffic-monitoring`.
2.  Tạo file `offline_inference.py`.
3.  Cấu hình `roi.json` cho camera `pasteur_le_duan`.
4.  Chạy test detection offline.
