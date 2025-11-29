# 🚀 Big Data Streaming ABSA with Automated Model Retraining

> **Hệ thống ABSA (Aspect-Based Sentiment Analysis) với khả năng streaming real-time và tự động huấn luyện lại mô hình**

## 📖 Tổng quan

Hệ thống Big Data hoàn chỉnh kết hợp:

- ✅ **Kafka + Spark Structured Streaming**: Xử lý dữ liệu real-time
- ✅ **Deep Learning ABSA**: Phân tích cảm xúc đa khía cạnh
- ✅ **Automated ML Pipeline**: Tự động huấn luyện & cập nhật mô hình
- ✅ **Model Registry**: Quản lý phiên bản mô hình
- ✅ **Auto-reload Model**: Consumer tự động tải mô hình mới
- ✅ **Streamlit Dashboard**: Hiển thị kết quả real-time

---

## 🎯 Tính năng chính

### 1️⃣ **Streaming Pipeline** (chạy mỗi giờ)

- Producer đọc CSV → gửi Kafka
- Consumer (v2) nhận Kafka → Inference ABSA → PostgreSQL
- **Tự động reload mô hình** khi có model mới được promote

### 2️⃣ **Retraining Pipeline** (chạy Chủ nhật 2:00 AM)

- Load dữ liệu mới từ PostgreSQL
- Train mô hình ABSA mới (XLM-RoBERTa)
- **Đánh giá & so sánh** với mô hình production
- **Chỉ promote nếu tốt hơn** (improvement > 1%)

### 3️⃣ **Model Registry**

- Lưu trữ metadata của tất cả mô hình
- Theo dõi metrics (F1, accuracy, overall score)
- Quản lý production model
- Backup tự động

---

## 📁 Cấu trúc hệ thống

**Cấu trúc gốc (root `C:\airflow`) — tóm tắt nhanh**

- `docker-compose.yaml`
  Định nghĩa toàn bộ stack (Airflow, Kafka, Zookeeper, Spark, PostgreSQL, v.v.) dùng để khởi động bằng Docker Compose.
- `.env`
  Biến môi trường cấu hình chung (UID, ports, credential, …).

**Thư mục chính và chức năng**

- `dags/`
  Chứa các file DAG (.py). Airflow Scheduler quét /opt/airflow/dags (mount từ máy host) để load workflow. (Đặt DAG vào đây để Airflow tự nhận.)
- `logs/`
  Lưu log của các task/DAG chạy trong Airflow.
- `plugins/`
  Chứa plugin tuỳ biến cho Airflow (operator/custom hooks/…).
- `config/`
  Cấu hình tuỳ chỉnh (nếu có) cho Airflow hoặc project (ví dụ config cho Spark, Kafka, connection strings).
- `base/`
  Dùng để build image base `airflow-base`: có `Dockerfile` và `requirements.txt` chứa các lib nặng (Java, pyspark, torch, kafka-client, transformers, …). Mục đích: chung hóa môi trường, giảm thời gian build cho mọi project con.

  - `base/Dockerfile` — cài Java, cài Python libs, xây image từ `apache/airflow:2.9.0`.
  - `base/requirements.txt` — list thư viện chung (pyspark, kafka-python, torch, pandas, streamlit, …).

- `models/`
  Chứa file trọng số mô hình (ví dụ `absa_model.pt`) dùng bởi job inference.
- `projects/`
  Chứa các project con (ví dụ `absa_streaming/`). Mỗi project có folder riêng gồm mã nguồn, script, data, webapp.

  - `projects/absa_streaming/scripts/` — producer.py, consumer_postgres_streaming.py, script chạy Spark/producer/consumer.
  - `projects/absa_streaming/data/` — dữ liệu mẫu (CSV, test data).
  - `projects/absa_streaming/streamlit/` — mã Streamlit dashboard hiển thị kết quả realtime.
  - `projects/absa_streaming/requirements.txt` (tuỳ chọn) — lib riêng cho project.
  - `projects/absa_streaming/README.md` — mô tả ngắn project.

- `checkpoints/` (được đề cập)
  Thư mục nơi Spark lưu checkpoint; Airflow có task monitor/cleanup để kiểm tra và xóa checkpoint theo lifecycle.

**Các DAG & pipeline chính được mô tả**

- `absa_streaming_lifecycle` (ví dụ DAG) — orchestration Kafka → Spark → PostgreSQL:

  - `deploy_producer` (BashOperator) — chạy producer để push CSV → Kafka.
  - `deploy_consumer` (SparkSubmitOperator / BashOperator) — chạy Spark Structured Streaming, inference model `.pt`, ghi kết quả vào PostgreSQL.
  - `monitor_stream` (PythonOperator) — kiểm tra checkpoint/kafka lag/postgres writes, gửi cảnh báo.
  - `cleanup_checkpoints` (BashOperator) — xóa checkpoint cũ sau vòng chạy.

- Thiết lập `schedule_interval`, `execution_timeout`, `dagrun_timeout`, `retries`, `retry_delay` để control lifecycle (ví dụ: daily DAG, dagrun_timeout ≈ 23.8h).

---

## 🚀 Quick Start

### **Khởi động hệ thống:**

```powershell
# 1. Set environment
$env:AIRFLOW_UID = "50000"

# 2. Build và khởi động
docker-compose build
docker-compose up airflow-init
docker-compose up -d

# 3. Khởi tạo database schema
docker cp config/init_database.sql $(docker ps -qf "name=postgres"):/tmp/
docker exec -i $(docker ps -qf "name=postgres") psql -U airflow -d airflow -f /tmp/init_database.sql

# 4. Truy cập UIs
# Airflow: http://localhost:8080 (airflow/airflow)
# Streamlit: http://localhost:8501
```

### **Sử dụng Management Scripts:**

```powershell
# Import module
. .\scripts\management.ps1

# Khởi động stack
Start-ABSAStack

# Kiểm tra trạng thái
Get-ABSAStatus

# Trigger DAG
Start-RetrainingDAG

# Xem logs
Get-TrainingLogs

# Xem kết quả
Get-ABSAResults -Limit 20
```

---

## 📊 DAGs có sẵn

### 1. **`absa_streaming_lifecycle_v2`** (Mỗi giờ)

Pipeline streaming chính với auto-reload model:

- ✅ Deploy Producer (Kafka)
- ✅ Deploy Consumer v2 (Spark + Auto-reload)
- ✅ Monitor checkpoint & model
- ✅ Cleanup

### 2. **`absa_model_retraining`** (Chủ nhật 2:00 AM)

Pipeline huấn luyện tự động:

- ✅ Prepare training data
- ✅ Train new model
- ✅ Evaluate & compare
- ✅ Promote if better (>1% improvement)
- ✅ Cleanup old models

---

## 🔧 Tùy chỉnh

### **Thay đổi lịch retraining:**

File: `dags/absa_model_retraining_dag.py`

```python
# Chạy hàng ngày lúc 3:00 AM
schedule_interval="0 3 * * *"
```

### **Điều chỉnh ngưỡng promote:**

File: `projects/absa_streaming/training/evaluate_and_promote.py`

```python
IMPROVEMENT_THRESHOLD = 0.02  # 2% thay vì 1%
```

### **Tham số training:**

File: `projects/absa_streaming/training/train_absa_model.py`

```python
EPOCHS = 5
BATCH_SIZE = 32
LEARNING_RATE = 1e-5
```

---

## 📈 Monitoring

### **Kiểm tra mô hình production:**

```sql
-- Trong PostgreSQL
SELECT * FROM model_performance_summary;
```

### **Xem lịch sử training:**

```powershell
docker exec $(docker ps -qf "name=airflow-scheduler") cat /opt/airflow/projects/absa_streaming/training/evaluation_log.json
```

### **Theo dõi streaming:**

```powershell
# Logs consumer
docker logs -f $(docker ps -qf "name=airflow-scheduler")

# Kết quả trong database
docker exec -i $(docker ps -qf "name=postgres") psql -U airflow -d airflow -c "SELECT COUNT(*) FROM absa_results;"
```

---

## 🆕 Điểm mới so với phiên bản cũ

| Feature          | Old Version  | **New Version**               |
| ---------------- | ------------ | ----------------------------- |
| Consumer         | Static model | ✅ **Auto-reload model**      |
| Model update     | Manual copy  | ✅ **Automated pipeline**     |
| Model evaluation | None         | ✅ **Auto compare & promote** |
| Model registry   | None         | ✅ **PostgreSQL tracking**    |
| Retraining       | Manual       | ✅ **Scheduled (weekly)**     |
| Backup           | None         | ✅ **Auto backup old models** |

---

## 📚 Tài liệu chi tiết

👉 **Xem hướng dẫn đầy đủ tại: [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)**

Bao gồm:

- Kiến trúc hệ thống chi tiết
- Workflow đầy đủ
- Database schema
- Troubleshooting
- Best practices

---

## 🧪 Testing

### **Test streaming:**

```powershell
# Trigger manual
Start-StreamingDAG

# Hoặc trong Airflow UI
# DAGs → absa_streaming_lifecycle_v2 → Trigger
```

### **Test retraining:**

```powershell
# Trigger manual
Start-RetrainingDAG

# Kiểm tra kết quả
Get-TrainingLogs
Get-ModelRegistry
```

---

## 🔍 Troubleshooting

### **Consumer không reload model:**

```powershell
# Kiểm tra timestamp
docker exec $(docker ps -qf "name=airflow-scheduler") ls -lh /opt/airflow/models/

# Clear checkpoint và restart
Clear-Checkpoints
Start-StreamingDAG
```

### **Training fails:**

```powershell
# Xem logs chi tiết
Get-TrainingLogs

# Giảm batch size nếu OOM
# Edit: projects/absa_streaming/training/train_absa_model.py
# BATCH_SIZE = 8
```

---

## 📝 Lưu ý quan trọng

**Điểm cần chú ý khi triển khai:**

- ✅ Dùng `airflow-base` image để tránh cài lại lib nặng
- ✅ Consumer v2 tự động reload model - không cần restart
- ✅ Mô hình chỉ được promote nếu **tốt hơn > 1%**
- ✅ Mount chính xác `dags/` và `models/` vào container
- ✅ Quản lý checkpoint Spark cẩn thận
- ✅ Cấu hình retry/timeout hợp lý cho streaming job

---

## 👥 Thông tin

**SE363 – Phát triển ứng dụng trên nền tảng dữ liệu lớn**  
Khoa Công nghệ Phần mềm  
Trường Đại học Công nghệ Thông tin, ĐHQG-HCM

---

**🎉 Hệ thống đã sẵn sàng! Chúc bạn thành công!**
