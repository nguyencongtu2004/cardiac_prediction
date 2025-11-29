#!/bin/bash
set -e

echo "================================================"
echo "Cardiac Data Preparation"
echo "================================================"

# Run Spark submit
spark-submit \
  --master local[*] \
  --driver-memory 4g \
  /opt/airflow/projects/cardiac_prediction/scripts/cardiac_data_prep.py

echo ""
echo "✅ Data preparation completed successfully"
