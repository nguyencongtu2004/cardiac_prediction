#!/usr/bin/env python3
"""
Cardiac Streaming Inference
Spark Structured Streaming consumer with real-time prediction
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, current_timestamp, struct, to_json
from pyspark.sql.types import StructType, StructField, DoubleType, IntegerType
from pyspark.ml import PipelineModel
import sys

def main():
    # Initialize Spark with Kafka support
    spark = SparkSession.builder \
        .appName("Cardiac Streaming Inference") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1") \
        .config("spark.driver.memory", "4g") \
        .getOrCreate()
    
    print("✅ Spark session initialized")
    
    # Load trained model
    model_path = "/opt/airflow/projects/cardiac_prediction/models/cardiac_rf_model"
    model = PipelineModel.load(model_path)
    print(f"✅ Model loaded from: {model_path}")
    
    # Define schema for incoming JSON messages
    schema = StructType([
        StructField("heart_rate", DoubleType(), True),
        StructField("bp_sys", DoubleType(), True),
        StructField("bp_dia", DoubleType(), True),
        StructField("spo2", DoubleType(), True),
        StructField("resp_rate", DoubleType(), True),
        StructField("age", IntegerType(), True),
        StructField("sex", IntegerType(), True),
        StructField("hypertension_history", IntegerType(), True),
        StructField("diabetes_history", IntegerType(), True),
        StructField("heart_failure_history", IntegerType(), True),
        StructField("smoking_status", IntegerType(), True),
        StructField("patient_id", IntegerType(), True)
    ])
    
    # Read stream from Kafka
    kafka_df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "kafka:9092") \
        .option("subscribe", "cardiac-events") \
        .option("startingOffsets", "latest") \
        .load()
    
    print("✅ Connected to Kafka stream: cardiac-events")
    
    # Parse JSON from Kafka
    parsed_df = kafka_df \
        .select(from_json(col("value").cast("string"), schema).alias("data")) \
        .select("data.*")
    
    # Apply model transformation (prediction)
    predictions_df = model.transform(parsed_df)
    
    # Select relevant columns and add timestamp
    output_df = predictions_df.select(
        current_timestamp().alias("prediction_time"),
        col("patient_id"),
        col("heart_rate"),
        col("bp_sys"),
        col("bp_dia"),
        col("spo2"),
        col("resp_rate"),
        col("age"),
        col("sex"),
        col("hypertension_history"),
        col("diabetes_history"),
        col("heart_failure_history"),
        col("smoking_status"),
        col("prediction").alias("predicted_label"),
        col("probability")[1].alias("risk_probability")
    )
    
    # Write to console for debugging
    query = output_df \
        .writeStream \
        .outputMode("append") \
        .format("console") \
        .option("truncate", False) \
        .option("checkpointLocation", "/opt/airflow/projects/cardiac_prediction/checkpoints/console") \
        .start()
    
    print("="*80)
    print("🚀 STREAMING STARTED")
    print("="*80)
    print("Listening for cardiac events...")
    print("Press Ctrl+C to stop")
    print("="*80)
    
    # Wait for termination
    query.awaitTermination()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✅ Streaming stopped by user")
        sys.exit(0)
