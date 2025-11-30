import time
import json
import random
import pandas as pd
from kafka import KafkaProducer, KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import TopicAlreadyExistsError

# Cấu hình Kafka
KAFKA_TOPIC = 'cardiac_data'
KAFKA_BOOTSTRAP_SERVERS = 'kafka:9092'

def create_topic_if_not_exists():
    try:
        admin_client = KafkaAdminClient(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            client_id='cardiac_producer'
        )
        topic_list = [NewTopic(name=KAFKA_TOPIC, num_partitions=1, replication_factor=1)]
        admin_client.create_topics(new_topics=topic_list, validate_only=False)
        print(f"✅ Topic '{KAFKA_TOPIC}' created.")
    except TopicAlreadyExistsError:
        print(f"ℹ️ Topic '{KAFKA_TOPIC}' already exists.")
    except Exception as e:
        print(f"⚠️ Error creating topic: {e}")
    finally:
        try:
            admin_client.close()
        except:
            pass

# Khởi tạo Producer
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def generate_cardiac_data():
    """
    Sinh dữ liệu giả lập bệnh nhân tim mạch khớp với schema huấn luyện.
    Features:
    - Continuous: heart_rate, bp_sys, bp_dia, spo2, resp_rate, age
    - Binary: sex, hypertension_history, diabetes_history, heart_failure_history, smoking_status
    """
    data = {
        # Continuous
        'age': random.randint(20, 90),
        'heart_rate': round(random.uniform(50, 120), 1),
        'bp_sys': round(random.uniform(90, 180), 1),
        'bp_dia': round(random.uniform(60, 110), 1),
        'spo2': round(random.uniform(90, 100), 1),
        'resp_rate': round(random.uniform(12, 30), 1),
        
        # Binary
        'sex': random.choice([0, 1]), # 0: Female, 1: Male
        'hypertension_history': random.choice([0, 1]),
        'diabetes_history': random.choice([0, 1]),
        'heart_failure_history': random.choice([0, 1]),
        'smoking_status': random.choice([0, 1]),
        
        'timestamp': time.time()
    }
    return data

def main():
    print(f"🚀 Starting Kafka Producer for topic: {KAFKA_TOPIC}")
    create_topic_if_not_exists()
    try:
        while True:
            data = generate_cardiac_data()
            producer.send(KAFKA_TOPIC, value=data)
            print(f"Sent: {data}")
            time.sleep(2) # Gửi dữ liệu mỗi 2 giây
    except KeyboardInterrupt:
        print("🛑 Stopping Producer...")
    finally:
        producer.close()

if __name__ == "__main__":
    main()
