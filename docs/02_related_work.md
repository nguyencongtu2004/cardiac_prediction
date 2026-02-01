# 2. TỔNG QUAN NGHIÊN CỨU (RELATED WORK)

## 2.1 Phát Hiện Đối Tượng Dựa Trên Deep Learning

### 2.1.1 Họ YOLO (You Only Look Once)

YOLO là một trong những kiến trúc phát hiện đối tượng một giai đoạn (one-stage detector) phổ biến nhất, được đề xuất lần đầu bởi Redmon et al. [2] vào năm 2016. Ưu điểm chính của YOLO là tốc độ xử lý nhanh, phù hợp cho ứng dụng thời gian thực.

| Version | Năm  | Đặc điểm chính           | FPS (GPU) | mAP   |
| ------- | ---- | ------------------------ | --------- | ----- |
| YOLOv1  | 2016 | Kiến trúc đầu tiên       | 45        | 63.4% |
| YOLOv3  | 2018 | Feature Pyramid Networks | 65        | 57.9% |
| YOLOv5  | 2020 | PyTorch, dễ training     | 140       | 56.8% |
| YOLOv8  | 2023 | Anchor-free, SOTA        | 180       | 53.9% |

**YOLOv8** (Ultralytics, 2023) [3] được sử dụng trong nghiên cứu này vì:

- Kiến trúc anchor-free, giảm số lượng hyperparameters
- Hỗ trợ nhiều task: detection, segmentation, classification
- Cộng đồng lớn và được cập nhật thường xuyên
- Đạt trạng thái state-of-the-art trên nhiều benchmark

### 2.1.2 So Sánh Với Các Kiến Trúc Khác

| Phương pháp      | Loại      | Tốc độ     | Độ chính xác | Phù hợp real-time |
| ---------------- | --------- | ---------- | ------------ | ----------------- |
| Faster R-CNN [4] | Two-stage | Chậm       | Cao          | ❌                |
| SSD [5]          | One-stage | Nhanh      | Trung bình   | ✅                |
| RetinaNet [6]    | One-stage | Trung bình | Cao          | ⚠️                |
| **YOLOv8**       | One-stage | Rất nhanh  | Cao          | ✅                |

## 2.2 Phát Hiện Vi Phạm Không Đội Mũ Bảo Hiểm

### 2.2.1 Các Nghiên Cứu Trước

**Raj et al. (2022)** [7] đề xuất hệ thống phát hiện mũ bảo hiểm sử dụng YOLOv5 với 2 mô hình riêng biệt:

- Mô hình 1: Phát hiện người và xe máy (COCO pre-trained)
- Mô hình 2: Phát hiện mũ bảo hiểm (custom trained)

_Hạn chế_: Cần inference 2 lần, tăng độ trễ.

**Shine & Joshi (2020)** [8] sử dụng CNN kết hợp với HOG features:

- Độ chính xác: 91.3%
- Thời gian xử lý: 150ms/frame

_Hạn chế_: Không phát hiện được nhiều người trong một frame.

**Lin et al. (2021)** [9] áp dụng attention mechanism:

- Cải thiện phát hiện mũ bị che khuất
- mAP đạt 87.2%

_Hạn chế_: Yêu cầu GPU mạnh, khó triển khai edge device.

### 2.2.2 Điểm Khác Biệt Của Nghiên Cứu Này

Chúng tôi sử dụng **Unified Model 8 classes** với một lần inference:

- Classes: person, bicycle, car, motorcycle, bus, truck, with_helmet, without_helmet
- Giảm 50% thời gian xử lý so với pipeline 2 mô hình
- Kết hợp spatial reasoning để xác định người đang đi xe

## 2.3 Phát Hiện Vi Phạm Vượt Đèn Đỏ

### 2.3.1 Phương Pháp Truyền Thống

**Phương pháp inductive loop** [10]:

- Sử dụng cảm biến từ tính dưới mặt đường
- Độ chính xác cao nhưng chi phí lắp đặt lớn
- Khó bảo trì và mở rộng

**Phương pháp radar** [11]:

- Phát hiện qua tín hiệu radar
- Không phụ thuộc điều kiện thời tiết
- Giá thành cao

### 2.3.2 Phương Pháp Computer Vision

**Dilek et al. (2023)** [12] đề xuất kết hợp YOLO với HSV color detection:

- Phát hiện đèn giao thông bằng YOLO
- Xác định màu bằng phân tích HSV
- Độ chính xác: 89%

_Hạn chế_: Chưa có tracking, khó xử lý occlusion.

**Wang et al. (2022)** [13] sử dụng DeepSORT cho tracking:

- Kết hợp detection và tracking
- Xác định hướng di chuyển chính xác hơn

_Hạn chế_: DeepSORT tốn tài nguyên, khó scale.

### 2.3.3 Điểm Khác Biệt Của Nghiên Cứu Này

Chúng tôi kết hợp:

- **YOLOv8** cho vehicle detection
- **HSV dual-range** cho color detection (xử lý cả 2 spectrum của màu đỏ)
- **CentroidTracker** lightweight cho tracking
- **Direction-aware violation** hỗ trợ cả 2 hướng vi phạm

## 2.4 Phát Hiện Vi Phạm Lấn Làn

### 2.4.1 Các Nghiên Cứu Trước

**Lane detection approaches** [14]:

- Hough Transform: Phát hiện đường thẳng
- Polynomial fitting: Phát hiện làn cong
- Deep learning: SegNet, ENet cho lane segmentation

**Lee et al. (2021)** [15] dùng semantic segmentation:

- Phát hiện vạch kẻ đường bằng segmentation
- Xác định xe chạm vạch

_Hạn chế_: Heavy model, không phân biệt solid/dashed.

### 2.4.2 Điểm Khác Biệt Của Nghiên Cứu Này

- Sử dụng **ROI configuration** thay vì lane detection tự động
- Phân biệt **solid line** (vi phạm) và **dashed line** (cho phép)
- Thuật toán **point-to-line side tracking** để xác định crossing

## 2.5 Kiến Trúc Xử Lý Stream Thời Gian Thực

### 2.5.1 Message Queue Systems

| Hệ thống         | Throughput | Latency    | Persistence | Use case   |
| ---------------- | ---------- | ---------- | ----------- | ---------- |
| RabbitMQ         | Trung bình | Thấp       | Có          | Task queue |
| Redis Pub/Sub    | Cao        | Rất thấp   | Không       | Real-time  |
| **Apache Kafka** | Rất cao    | Thấp       | Có          | Stream     |
| AWS Kinesis      | Cao        | Trung bình | Có          | Cloud      |

**Apache Kafka** [16] được chọn vì:

- Throughput cao (millions msg/sec)
- Persistent storage cho replay
- Consumer groups cho scaling
- Ecosystem phong phú (Kafka Streams, ksqlDB)

### 2.5.2 Orchestration Frameworks

**Apache Airflow** [17] được sử dụng để:

- Quản lý và schedule pipeline tasks
- Monitor và retry khi có lỗi
- DAG visualization cho debugging

## 2.6 Tổng Hợp Khoảng Trống Nghiên Cứu

| Khía cạnh               | Nghiên cứu trước | Nghiên cứu này                |
| ----------------------- | ---------------- | ----------------------------- |
| Số loại vi phạm         | 1 loại           | 3 loại đồng thời              |
| Xử lý                   | Offline/batch    | Real-time stream              |
| Số camera               | 1                | Multi-camera                  |
| Tracking                | Không/DeepSORT   | Lightweight CentroidTracker   |
| False positive handling | Không            | Deduplicator + Multi-strategy |
| Tích hợp                | Standalone       | Full-stack (DB + API + UI)    |
