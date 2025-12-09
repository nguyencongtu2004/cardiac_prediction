"""
db_consumer.py - Kafka Consumer to PostgreSQL
==============================================
Consumes traffic violation messages from Kafka and persists to PostgreSQL database.
"""

import os
import sys
import json
import time
import signal
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

import psycopg2
from psycopg2.extras import execute_batch
from kafka import KafkaConsumer
from kafka.errors import KafkaError

# ==========================
# CONFIGURATION
# ==========================
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'traffic_violations')
KAFKA_GROUP_ID = os.getenv('KAFKA_GROUP_ID', 'traffic_db_consumer')

# PostgreSQL Configuration
DB_HOST = os.getenv('DB_HOST', 'postgres')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'airflow')
DB_USER = os.getenv('DB_USER', 'airflow')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'airflow')

# Batch settings
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '10'))
BATCH_TIMEOUT = float(os.getenv('BATCH_TIMEOUT', '5.0'))  # seconds

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Graceful shutdown flag
shutdown_flag = False


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global shutdown_flag
    logger.info("🛑 Shutdown signal received. Finishing current batch...")
    shutdown_flag = True


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# ==========================
# DATABASE CONNECTION
# ==========================
def get_db_connection():
    """Create PostgreSQL connection with retry"""
    retries = 5
    for attempt in range(retries):
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )
            logger.info(f"✓ Connected to PostgreSQL at {DB_HOST}:{DB_PORT}/{DB_NAME}")
            return conn
        except psycopg2.Error as e:
            logger.warning(f"✗ Attempt {attempt + 1}/{retries}: DB connection failed - {e}")
            if attempt < retries - 1:
                time.sleep(3)
            else:
                raise


def insert_violations(conn, violations: List[Dict[str, Any]]) -> int:
    """Batch insert violations into database"""
    if not violations:
        return 0
    
    insert_sql = """
        INSERT INTO traffic_violations 
        (camera_id, violation_type, vehicle_type, confidence, 
         position_x, position_y, image_path, detected_at)
        VALUES (%(camera_id)s, %(violation_type)s, %(vehicle_type)s, %(confidence)s,
                %(position_x)s, %(position_y)s, %(image_path)s, %(detected_at)s)
    """
    
    try:
        with conn.cursor() as cur:
            execute_batch(cur, insert_sql, violations)
        conn.commit()
        return len(violations)
    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"✗ Failed to insert violations: {e}")
        return 0


def update_summary(conn, camera_id: str, hour_bucket: datetime, 
                   violations_count: int, vehicle_types: Dict[str, int],
                   violation_types: Dict[str, int]):
    """Update or insert hourly summary"""
    upsert_sql = """
        INSERT INTO detection_summary 
        (camera_id, hour_bucket, total_violations, vehicle_breakdown, violation_breakdown, updated_at)
        VALUES (%s, %s, %s, %s, %s, NOW())
        ON CONFLICT (camera_id, hour_bucket) DO UPDATE SET
            total_violations = detection_summary.total_violations + EXCLUDED.total_violations,
            vehicle_breakdown = detection_summary.vehicle_breakdown || EXCLUDED.vehicle_breakdown,
            violation_breakdown = detection_summary.violation_breakdown || EXCLUDED.violation_breakdown,
            updated_at = NOW()
    """
    
    try:
        with conn.cursor() as cur:
            cur.execute(upsert_sql, (
                camera_id, 
                hour_bucket,
                violations_count,
                json.dumps(vehicle_types),
                json.dumps(violation_types)
            ))
        conn.commit()
    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"✗ Failed to update summary: {e}")


# ==========================
# KAFKA CONSUMER
# ==========================
def create_consumer() -> KafkaConsumer:
    """Create Kafka Consumer with retry"""
    retries = 5
    for attempt in range(retries):
        try:
            consumer = KafkaConsumer(
                KAFKA_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                group_id=KAFKA_GROUP_ID,
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                consumer_timeout_ms=int(BATCH_TIMEOUT * 1000)
            )
            logger.info(f"✓ Connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")
            logger.info(f"  Topic: {KAFKA_TOPIC} | Group: {KAFKA_GROUP_ID}")
            return consumer
        except KafkaError as e:
            logger.warning(f"✗ Attempt {attempt + 1}/{retries}: Kafka connection failed - {e}")
            if attempt < retries - 1:
                time.sleep(5)
            else:
                raise


def parse_message(message: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse Kafka message and extract violations"""
    violations = []
    
    try:
        camera_id = message.get('camera_id', 'unknown')
        timestamp_str = message.get('timestamp', datetime.now().isoformat())
        image_path = message.get('image_path', '')
        
        # Parse timestamp
        try:
            detected_at = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except:
            detected_at = datetime.now()
        
        # Parse violations (could be string or list)
        raw_violations = message.get('violations', [])
        if isinstance(raw_violations, str):
            raw_violations = json.loads(raw_violations)
        
        for v in raw_violations:
            position = v.get('position', [0, 0])
            violations.append({
                'camera_id': camera_id,
                'violation_type': v.get('type', 'unknown'),
                'vehicle_type': v.get('vehicle', 'unknown'),
                'confidence': float(v.get('confidence', 0.0)),
                'position_x': float(position[0]) if len(position) > 0 else 0.0,
                'position_y': float(position[1]) if len(position) > 1 else 0.0,
                'image_path': image_path,
                'detected_at': detected_at
            })
    except Exception as e:
        logger.error(f"✗ Failed to parse message: {e}")
    
    return violations


# ==========================
# MAIN LOOP
# ==========================
def main():
    global shutdown_flag
    
    logger.info("=" * 60)
    logger.info("🚀 Starting Traffic Violations DB Consumer")
    logger.info("=" * 60)
    
    # Connect to services
    conn = get_db_connection()
    consumer = create_consumer()
    
    batch: List[Dict[str, Any]] = []
    last_flush = time.time()
    total_processed = 0
    
    logger.info(f"📦 Batch settings: size={BATCH_SIZE}, timeout={BATCH_TIMEOUT}s")
    logger.info("Listening for messages... (Ctrl+C to stop)\n")
    
    try:
        while not shutdown_flag:
            # Poll for messages
            try:
                for message in consumer:
                    if shutdown_flag:
                        break
                    
                    # Parse and add to batch
                    violations = parse_message(message.value)
                    batch.extend(violations)
                    
                    # Check if should flush
                    should_flush = (
                        len(batch) >= BATCH_SIZE or 
                        (time.time() - last_flush) >= BATCH_TIMEOUT
                    )
                    
                    if should_flush and batch:
                        inserted = insert_violations(conn, batch)
                        total_processed += inserted
                        logger.info(f"💾 Inserted {inserted} violations | Total: {total_processed}")
                        batch = []
                        last_flush = time.time()
            
            except StopIteration:
                # Consumer timeout, flush if needed
                if batch:
                    inserted = insert_violations(conn, batch)
                    total_processed += inserted
                    logger.info(f"💾 Timeout flush: {inserted} violations | Total: {total_processed}")
                    batch = []
                    last_flush = time.time()
            
            # Small sleep to prevent tight loop
            time.sleep(0.1)
    
    except Exception as e:
        logger.error(f"✗ Unexpected error: {e}")
        raise
    
    finally:
        # Final flush
        if batch:
            inserted = insert_violations(conn, batch)
            total_processed += inserted
            logger.info(f"💾 Final flush: {inserted} violations")
        
        # Cleanup
        consumer.close()
        conn.close()
        logger.info(f"\n✓ Consumer stopped. Total processed: {total_processed}")


if __name__ == "__main__":
    main()
