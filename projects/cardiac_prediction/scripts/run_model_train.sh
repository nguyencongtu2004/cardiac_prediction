#!/bin/bash
set -e

echo "================================================"
echo "Cardiac Model Training"
echo "================================================"

# Run Spark submit
spark-submit \
  --master local[*] \
  --driver-memory 4g \
  /opt/airflow/projects/cardiac_prediction/scripts/cardiac_model_train.py

echo ""
echo "✅ Model training completed successfully"
