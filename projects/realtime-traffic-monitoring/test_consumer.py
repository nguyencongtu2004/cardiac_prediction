# Traffic Monitoring - Kafka Consumer Test Script

import json
from kafka import KafkaConsumer

KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
KAFKA_TOPIC = 'camera_raw_frames'

def main():
    print(f"Connecting to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"Subscribing to topic: {KAFKA_TOPIC}")
    print("="*60)
    
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        auto_offset_reset='latest',  # Chỉ đọc message mới
        enable_auto_commit=True,
        group_id='traffic-monitoring-test-group',
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )
    
    print("✓ Connected! Waiting for messages...\n")
    
    try:
        for message in consumer:
            data = message.value
            print(f"📸 Received from {data['camera_id']}")
            print(f"   Timestamp: {data['timestamp']}")
            print(f"   Image Path: {data['image_path']}")
            print(f"   Partition: {message.partition}, Offset: {message.offset}")
            print("-"*60)
    
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping consumer...")
    finally:
        consumer.close()
        print("✓ Consumer closed")

if __name__ == "__main__":
    main()
