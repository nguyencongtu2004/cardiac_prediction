Để xem sự thay đổi trong pipeline realtime, bạn cần làm theo các bước sau:

## 🔄 Bước 1: Rebuild Docker Image (vì thêm dependencies mới)

```powershell
# Dừng các container hiện tại
docker-compose down

# Rebuild image với dependencies mới (imbalanced-learn, xgboost)
docker-compose build

# Khởi động lại
docker-compose up -d
```

## 📊 Bước 2: Retrain Model với code mới

Có 2 cách:

**Cách 1: Qua Airflow UI (Khuyến nghị)**
```
1. Mở http://localhost:8080 (airflow/airflow)
2. Tìm DAG: cardiac_model_retraining
3. Click nút "Trigger DAG" ▶️
4. Đợi ~5-10 phút để train xong
5. Xem logs để thấy metrics của 3 models + ensemble
```

**Cách 2: Chạy manual qua terminal**
```powershell
# Vào container worker
docker exec -it airflow-airflow-worker-1 bash

# Chạy data prep (nếu cần)
bash /opt/airflow/projects/cardiac_prediction/scripts/run_data_prep.sh

# Chạy training
bash /opt/airflow/projects/cardiac_prediction/scripts/run_model_train.sh

# Exit
exit
```

## 🎯 Bước 3: Restart Streaming Pipeline

```powershell
# Cách 1: Qua Airflow UI
# 1. Mở http://localhost:8080
# 2. Tìm DAG: cardiac_streaming_lifecycle
# 3. Click "Trigger DAG" để restart với model mới

# Cách 2: Manual
docker exec -d airflow-airflow-worker-1 python3 /opt/airflow/projects/cardiac_prediction/scripts/producer.py

docker exec -d airflow-airflow-worker-1 spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.postgresql:postgresql:42.6.0 \
  /opt/airflow/projects/cardiac_prediction/scripts/spark_streaming.py
```

## 📈 Bước 4: Xem kết quả trên Dashboard

```
1. Mở http://localhost:8501 (Streamlit Dashboard)
2. Quan sát:
   - Predictions realtime với model mới
   - Accuracy/F1-Score có cải thiện không
   - Distribution của predictions
```

## 🔍 Bước 5: So sánh metrics Model cũ vs Model mới

```powershell
# Xem metrics của model mới vừa train
docker exec airflow-airflow-worker-1 cat /opt/airflow/models/cardiac_rf_model_metrics.json
```

Bạn sẽ thấy output như này:
```json
{
  "random_forest": {
    "Accuracy": 0.8750,
    "F1": 0.7823,
    "AUC-ROC": 0.9234
  },
  "logistic_regression": {
    "Accuracy": 0.8512,
    "F1": 0.7645
  },
  "gradient_boosting": {
    "Accuracy": 0.8698,
    "F1": 0.7756
  },
  "ensemble": {
    "accuracy": 0.8834,
    "f1": 0.7912
  }
}
```

## ⚠️ Troubleshooting

Nếu gặp lỗi khi build:
```powershell
# Xóa cache và rebuild
docker-compose down -v
docker system prune -f
docker-compose build --no-cache
docker-compose up -d
```

Bạn muốn tôi giúp chạy các bước này không? Tôi có thể:
1. ✅ Tạo script tự động để chạy toàn bộ
2. ✅ Monitor logs realtime trong quá trình training
3. ✅ So sánh metrics trước/sau