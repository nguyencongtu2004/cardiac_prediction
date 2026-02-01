# 5. THỰC NGHIỆM VÀ KẾT QUẢ (EXPERIMENTS AND RESULTS)

## 5.1 Dataset và Môi Trường Thực Nghiệm

### 5.1.1 Dataset

#### Helmet Violation Dataset

- **Nguồn**: Kết hợp từ nhiều nguồn công khai và tự thu thập
- **Tổng số ảnh**: 5,420 ảnh
- **Phân chia**: Train (70%) / Val (20%) / Test (10%)
- **Classes**: 8 classes (person, bicycle, car, motorcycle, bus, truck, with_helmet, without_helmet)
- **Annotation format**: YOLO format (txt files)

| Dataset    | Số ảnh | Số annotations |
| ---------- | ------ | -------------- |
| Train      | 3,794  | 28,450         |
| Validation | 1,084  | 8,130          |
| Test       | 542    | 4,065          |

#### Red Light Violation Videos

- **Nguồn**: Camera giám sát giao thông TP.HCM (công khai)
- **Số lượng**: 15 video segments
- **Tổng thời lượng**: ~45 phút
- **Resolution**: 1920x1080 (Full HD)
- **Ground truth**: Manually annotated violations

#### Lane Violation Videos

- **Nguồn**: Dashcam recordings + traffic camera
- **Số lượng**: 8 video segments
- **Tổng thời lượng**: ~25 phút

### 5.1.2 Hardware Configuration

| Component | Specification                               |
| --------- | ------------------------------------------- |
| CPU       | Intel Core i7-12700H (14 cores, 20 threads) |
| RAM       | 32 GB DDR5                                  |
| GPU       | NVIDIA RTX 3060 (6GB VRAM)                  |
| Storage   | 512 GB NVMe SSD                             |
| OS        | Ubuntu 22.04 LTS                            |

### 5.1.3 Software Stack

| Software     | Version | Purpose                 |
| ------------ | ------- | ----------------------- |
| Python       | 3.10    | Main language           |
| PyTorch      | 2.1.0   | Deep learning framework |
| Ultralytics  | 8.0.196 | YOLOv8 implementation   |
| OpenCV       | 4.8.1   | Image processing        |
| Apache Kafka | 7.5.0   | Message broker          |
| PostgreSQL   | 13      | Database                |
| FastAPI      | 0.104.1 | Backend API             |
| Next.js      | 14.x    | Frontend                |

## 5.2 Evaluation Metrics

### 5.2.1 Object Detection Metrics

- **Precision (P)**: Tỷ lệ predictions đúng trong tất cả predictions
  $$P = \frac{TP}{TP + FP}$$

- **Recall (R)**: Tỷ lệ ground truth được phát hiện
  $$R = \frac{TP}{TP + FN}$$

- **F1-Score**: Harmonic mean của Precision và Recall
  $$F1 = 2 \times \frac{P \times R}{P + R}$$

- **mAP@0.5**: Mean Average Precision tại IoU threshold 0.5

### 5.2.2 System Performance Metrics

- **FPS (Frames Per Second)**: Số frame xử lý mỗi giây
- **Latency**: Độ trễ end-to-end từ capture đến display
- **Throughput**: Số lượng camera xử lý đồng thời

## 5.3 Kết Quả Thực Nghiệm

### 5.3.1 Helmet Detection Performance

**Model Training Results:**

| Model                      | mAP@0.5   | mAP@0.5:0.95 | Precision | Recall    |
| -------------------------- | --------- | ------------ | --------- | --------- |
| YOLOv8n (baseline)         | 0.782     | 0.523        | 0.814     | 0.756     |
| YOLOv8s                    | 0.821     | 0.567        | 0.845     | 0.789     |
| **Unified 8-class (ours)** | **0.847** | **0.612**    | **0.872** | **0.823** |

**Per-class Performance:**

| Class          | Precision | Recall | F1-Score |
| -------------- | --------- | ------ | -------- |
| person         | 0.89      | 0.86   | 0.87     |
| motorcycle     | 0.91      | 0.88   | 0.89     |
| with_helmet    | 0.85      | 0.82   | 0.83     |
| without_helmet | 0.84      | 0.79   | 0.81     |

### 5.3.2 Red Light Detection Performance

**Traffic Light Color Recognition:**

| Condition       | Accuracy  | Notes                    |
| --------------- | --------- | ------------------------ |
| Daytime, clear  | 94.2%     | Best performance         |
| Daytime, cloudy | 91.5%     | Slight decrease          |
| Nighttime       | 88.3%     | LED easier to detect     |
| Rainy           | 85.1%     | Reflections cause issues |
| **Average**     | **89.8%** |                          |

**Violation Detection:**

| Metric              | Value |
| ------------------- | ----- |
| True Positive Rate  | 91.2% |
| False Positive Rate | 6.8%  |
| Precision           | 93.1% |
| Recall              | 91.2% |

### 5.3.3 Lane Detection Performance

| Metric                        | Value |
| ----------------------------- | ----- |
| Solid line crossing detection | 82.4% |
| False alarm rate              | 8.5%  |
| Average detection latency     | 45ms  |

### 5.3.4 System Performance

**Processing Speed:**

| Configuration  | FPS    | Latency  |
| -------------- | ------ | -------- |
| CPU only       | 12-15  | 80-100ms |
| GPU (RTX 3060) | 45-60  | 20-30ms  |
| GPU + TensorRT | 80-100 | 12-18ms  |

**End-to-End Latency Breakdown:**

| Stage               | Time      |
| ------------------- | --------- |
| Frame capture       | 5ms       |
| Kafka produce       | 10ms      |
| YOLO inference      | 25ms      |
| Post-processing     | 5ms       |
| Kafka consume       | 10ms      |
| WebSocket broadcast | 5ms       |
| **Total**           | **~60ms** |

**Scalability Test:**

| Num Cameras | Total FPS | Latency | Resource Usage |
| ----------- | --------- | ------- | -------------- |
| 1           | 55        | 18ms    | 25% GPU        |
| 2           | 48        | 22ms    | 45% GPU        |
| 4           | 38        | 35ms    | 78% GPU        |
| 6           | 28        | 48ms    | 95% GPU        |

## 5.4 So Sánh Với Các Phương Pháp Khác

### 5.4.1 Helmet Detection Comparison

| Method                   | mAP      | FPS    | Multi-rider |
| ------------------------ | -------- | ------ | ----------- |
| Raj et al. (2022) [7]    | 0.81     | 25     | ❌          |
| Shine & Joshi (2020) [8] | 0.79     | 8      | ❌          |
| Lin et al. (2021) [9]    | 0.87     | 18     | ⚠️          |
| **Ours**                 | **0.85** | **55** | **✅**      |

### 5.4.2 Red Light Detection Comparison

| Method                   | Precision | Recall  | Real-time |
| ------------------------ | --------- | ------- | --------- |
| Dilek et al. (2023) [12] | 89%       | 85%     | ❌        |
| Wang et al. (2022) [13]  | 91%       | 88%     | ⚠️        |
| **Ours**                 | **93%**   | **91%** | **✅**    |

### 5.4.3 Overall System Comparison

| Aspect          | Traditional Systems | AI-based (Batch) | **Ours**          |
| --------------- | ------------------- | ---------------- | ----------------- |
| Violation types | 1                   | 1-2              | **3**             |
| Processing      | Real-time           | Offline          | **Real-time**     |
| Multi-camera    | Limited             | Yes              | **Yes**           |
| Dashboard       | Basic               | None             | **Full-featured** |
| Latency         | <100ms              | Hours            | **<100ms**        |
