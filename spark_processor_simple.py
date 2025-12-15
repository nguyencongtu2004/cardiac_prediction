# Simplified Spark Processor for Testing
# This version removes YOLO inference to test Kafka connectivity first

from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, lit
from pyspark.sql.types import StructType, StructField, StringType
import os

# ==========================
# CẤU HÌNH
# ==========================
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
INPUT_TOPIC = 'camera_raw_frames'
CHECKPOINT_DIR = '/tmp/spark_checkpoint_simple'

# ==========================
# SCHEMA
# ==========================
input_schema = StructType([
    StructField("camera_id", StringType(), True),
    StructField("timestamp", StringType(), True),
    StructField("image_path", StringType(), True),
    StructField("filename", StringType(), True)
])

# ==========================
# MAIN
# ==========================
def main():
    print("🚀 Starting Simple Spark Streaming Test...")
    
    # Create Spark Session
    spark = SparkSession.builder \
        .appName("TrafficMonitoringSimple") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    
    # Read from Kafka
    df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", INPUT_TOPIC) \
        .option("startingOffsets", "latest") \
        .load()
    
    # Parse JSON
    parsed_df = df.select(
        from_json(col("value").cast("string"), input_schema).alias("data")
    ).select("data.*")
    
    # Add simple processing indicator
    processed_df = parsed_df.withColumn("status", lit("received"))
    
    # Write to console
    query = processed_df \
        .writeStream \
        .outputMode("append") \
        .format("console") \
        .option("truncate", False) \
        .option("checkpointLocation", CHECKPOINT_DIR) \
        .start()
    
    print("✓ Streaming started successfully!")
    print(f"  - Input Topic: {INPUT_TOPIC}")
    print(f"  - Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
    print("\nWaiting for messages...\n")
    
    query.awaitTermination()

if __name__ == "__main__":
    main()
