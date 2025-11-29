# Kế hoạch Đồ án: Cardiac Admission Outcome Prediction
## Phân tích dữ liệu y tế streaming để dự báo khả năng nhập viện tim mạch

### Mục tiêu
Xây dựng hệ thống Big Data end-to-end để dự báo nguy cơ nhập viện/tái nhập viện tim mạch dựa trên dữ liệu streaming. Hệ thống bao gồm thu thập dữ liệu, xử lý streaming, mô hình hóa (Machine Learning), orchestration và visualization.

### 3. Kế hoạch chi tiết (What + Tech)

#### Giai đoạn 0 – Stack & Môi trường
**Công nghệ chính:**
*   **Apache Spark 3.x (PySpark):** DataFrame, MLlib, Structured Streaming.
*   **Apache Kafka:** Message broker (topics: `cardiac-events`, `cardiac-predictions`).
*   **Apache Airflow 2.x:** Orchestrate DAG streaming & retrain (Pattern: ABSA).
*   **PostgreSQL:** Lưu trữ kết quả prediction (hoặc ClickHouse).
*   **Streamlit:** Dashboard realtime.
*   **Docker Compose:** Dựng cluster (Airflow + Kafka + Spark + Postgres + Streamlit).

#### Giai đoạn 1 – Bài toán & Dữ liệu
*   **Dataset:** Chọn dataset chất lượng (ví dụ: Hospital Admissions Data hoặc Cardiology Unit Admission trên Kaggle).
*   **Định nghĩa Label:**
    *   `1`: Admission type là "cardiac" hoặc readmission trong 30 ngày.
    *   `0`: Các trường hợp còn lại.
*   **Load Data (PySpark):** Sử dụng `spark.read.csv(..., header=True, inferSchema=True)`.
*   **EDA & Preprocessing:** Describe, check missing values, phân bố label, xử lý imbalance.

#### Giai đoạn 2 – Xây dựng Spark ML Pipeline (Offline)
*   **Tiền xử lý (Feature Engineering):**
    *   `StringIndexer`: Cho các cột category (giới tính, bảo hiểm, loại nhập viện...).
    *   `OneHotEncoder`: Mã hóa category index.
    *   `VectorAssembler`: Gộp features vào cột `features`.
    *   `StandardScaler` / `Normalizer`: Chuẩn hóa numeric features.
*   **Model:**
    *   Thử nghiệm: `LogisticRegression`, `RandomForestClassifier`, `GBTClassifier`, `MultilayerPerceptronClassifier`.
    *   Tuning: Dùng `ParamGridBuilder` + `CrossValidator` để tìm hyperparameters tối ưu (depth, numTrees, maxIter...).
*   **Đánh giá:**
    *   Metric: AUC, F1, Recall class 1 (ưu tiên bắt đúng ca nguy cơ cao).
    *   Lưu Confusion Matrix, ROC Curve.
*   **Đóng gói Model:**
    *   Tạo Pipeline hoàn chỉnh (Preprocessing + Model).
    *   Lưu model: `model.write().overwrite().save("models/cardiac_admission")`.

#### Giai đoạn 3 – Streaming Inference (Kafka + Spark Structured Streaming)
*   **Kafka Producer (Python):**
    *   Mô phỏng streaming dữ liệu y tế.
    *   Đọc từ CSV, gửi từng record (JSON) lên topic `cardiac-events`.
*   **Spark Structured Streaming Job:**
    *   `readStream` từ topic `cardiac-events`.
    *   Parse JSON -> DataFrame (schema giống training).
    *   Load PipelineModel -> `model.transform(stream_df)` để dự báo.
*   **Output (`writeStream`):**
    *   `foreachBatch`: Ghi vào PostgreSQL table `cardiac_predictions`.
    *   (Option) Ghi vào topic `cardiac-alerts` nếu xác suất > threshold.
*   **Checkpoint:** Cấu hình `checkpointLocation` để đảm bảo fault-tolerance.

#### Giai đoạn 4 – Orchestration bằng Airflow
*   **DAG 1: `cardiac_streaming_lifecycle` (Streaming hằng ngày)**
    *   `deploy_producer` (BashOperator): Chạy script đẩy dữ liệu.
    *   `deploy_consumer` (SparkSubmitOperator): Chạy Spark Streaming job.
    *   `monitor_stream` (PythonOperator): Kiểm tra health của job.
    *   `cleanup_checkpoints` (BashOperator): Dọn dẹp cuối ngày.
*   **DAG 2: `cardiac_model_retraining_daily` (Cải thiện model liên tục)**
    *   Schedule: `@daily`.
    *   `extract_training_data`: Lấy dữ liệu mới đã có nhãn -> Parquet/Table.
    *   `train_model`: Retrain Pipeline MLlib, lưu version mới (`models/cardiac/v<date>`).
    *   `evaluate_and_promote`: So sánh metric với model cũ. Nếu tốt hơn -> Promote (update symlink/config).

#### Giai đoạn 5 – Ứng dụng thực tế & Demo
*   **Streamlit Dashboard:**
    *   Kết nối PostgreSQL.
    *   Hiển thị: Bảng bệnh nhân nguy cơ cao, Biểu đồ xu hướng (High-risk/giờ), Chi tiết từng ca (Feature Importance).
*   **Use Case Story:** Hệ thống cảnh báo sớm cho bác sĩ/phòng cấp cứu về nguy cơ tái nhập viện.
*   **Báo cáo & Bảo vệ:**
    *   Lý do chọn đề tài.
    *   Kiến trúc hệ thống (Diagram).
    *   Mô tả ML Pipeline & So sánh Model.
    *   **Demo Live:** Airflow trigger -> Producer bắn tin -> Dashboard cập nhật realtime.
