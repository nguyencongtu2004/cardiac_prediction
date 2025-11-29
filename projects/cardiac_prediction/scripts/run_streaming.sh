#!/bin/bash
set -e

echo "================================================"
echo "Cardiac Streaming Demo"
echo "================================================"
echo ""
echo "This will start:"
echo "  1. Kafka Producer (cardiac events)"
echo "  2. Spark Streaming Consumer (inference)"
echo ""
echo "Press Ctrl+C to stop"
echo "================================================"
echo ""

# Start producer in background
echo "▶️  Starting Kafka Producer..."
python3 /opt/airflow/projects/cardiac_prediction/scripts/cardiac_producer.py \
  --kafka-server kafka:9092 \
  --topic cardiac-events \
  --delay 2.0 \
  --max-records 50 &

PRODUCER_PID=$!
sleep 3

# Start consumer (foreground)
echo "▶️  Starting Spark Streaming Consumer..."
spark-submit \
  --master local[*] \
  --driver-memory 4g \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1 \
  /opt/airflow/projects/cardiac_prediction/scripts/cardiac_streaming_inference.py

# Cleanup
kill $PRODUCER_PID 2>/dev/null || true
echo ""
echo "✅ Streaming demo completed"
