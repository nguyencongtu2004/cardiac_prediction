# Spark Streaming Test Script (Local Mode)
# This script tests the Spark processor locally without Docker

from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, StringType
import json

# Schema
input_schema = StructType([
    StructField("camera_id", StringType(), True),
    StructField("timestamp", StringType(), True),
    StructField("image_path", StringType(), True),
    StructField("filename", StringType(), True)
])

def test_kafka_connection():
    """Test Kafka connection and read messages"""
    print("Testing Kafka connection...")
    
    spark = SparkSession.builder \
        .appName("KafkaTest") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
        .master("local[*]") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    
    try:
        # Read from Kafka
        df = spark \
            .readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", "localhost:9092") \
            .option("subscribe", "camera_raw_frames") \
            .option("startingOffsets", "latest") \
            .load()
        
        # Parse JSON
        parsed_df = df.select(
            from_json(col("value").cast("string"), input_schema).alias("data")
        ).select("data.*")
        
        # Write to console
        query = parsed_df \
            .writeStream \
            .outputMode("append") \
            .format("console") \
            .option("truncate", False) \
            .start()
        
        print("✓ Connected to Kafka. Waiting for messages...")
        print("  Topic: camera_raw_frames")
        print("  Press Ctrl+C to stop.\n")
        
        query.awaitTermination()
    
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        spark.stop()

if __name__ == "__main__":
    test_kafka_connection()
