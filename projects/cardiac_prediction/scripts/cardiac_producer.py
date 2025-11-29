#!/usr/bin/env python3
"""
Cardiac Event Producer
Simulate streaming cardiac events to Kafka
"""

import json
import time
import argparse
from kafka import KafkaProducer
from pyspark.sql import SparkSession

def create_producer(bootstrap_servers):
    return KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

def main():
    parser = argparse.ArgumentParser(description='Cardiac Event Producer')
    parser.add_argument('--kafka-server', default='kafka:9092', help='Kafka bootstrap server')
    parser.add_argument('--topic', default='cardiac-events', help='Kafka topic')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between messages (seconds)')
    parser.add_argument('--max-records', type=int, default=0, help='Max records to send (0=unlimited)')
    args = parser.parse_args()
    
    # Initialize Spark to read test data
    spark = SparkSession.builder \
        .appName("Cardiac Producer") \
        .getOrCreate()
    
    # Load test data
    test_data = spark.read.parquet("/opt/airflow/projects/cardiac_prediction/data/test_data")
    
    print(f"✅ Loaded {test_data.count()} test records")
    
    # Create Kafka producer
    producer = create_producer(args.kafka_server)
    
    print(f"✅ Connected to Kafka: {args.kafka_server}")
    print(f"📤 Sending to topic: {args.topic}")
    print(f"⏱️  Delay: {args.delay}s per record")
    print("="*80)
    
    # Convert to pandas for easier iteration
    df_pandas = test_data.toPandas()
    
    count = 0
    for idx, row in df_pandas.iterrows():
        # Create message
        message = {
            'heart_rate': float(row['heart_rate']),
            'bp_sys': float(row['bp_sys']),
            'bp_dia': float(row['bp_dia']),
            'spo2': float(row['spo2']),
            'resp_rate': float(row['resp_rate']),
            'age': int(row['age']),
            'sex': int(row['sex']),
            'hypertension_history': int(row['hypertension_history']),
            'diabetes_history': int(row['diabetes_history']),
            'heart_failure_history': int(row['heart_failure_history']),
            'smoking_status': int(row['smoking_status']),
            'patient_id': idx  # Use index as patient_id
        }
        
        # Send to Kafka
        producer.send(args.topic, value=message)
        count += 1
        
        if count % 10 == 0:
            print(f"✅ Sent {count} records...")
        
        time.sleep(args.delay)
        
        if args.max_records > 0 and count >= args.max_records:
            break
    
    producer.flush()
    print(f"\n✅ Finished sending {count} records")
    spark.stop()

if __name__ == "__main__":
    main()
