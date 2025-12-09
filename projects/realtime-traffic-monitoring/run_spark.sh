#!/bin/bash

# Script to submit Spark job for traffic monitoring

SPARK_HOME=${SPARK_HOME:-/opt/spark}
KAFKA_PACKAGE="org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0"

echo "🚀 Submitting Spark Streaming Job..."
echo "   Kafka Package: $KAFKA_PACKAGE"
echo ""

$SPARK_HOME/bin/spark-submit \
  --master local[*] \
  --packages $KAFKA_PACKAGE \
  --conf spark.sql.streaming.checkpointLocation=/tmp/spark_checkpoint \
  --conf spark.driver.memory=2g \
  --conf spark.executor.memory=2g \
  spark_processor.py

echo ""
echo "✓ Spark job completed or terminated."
