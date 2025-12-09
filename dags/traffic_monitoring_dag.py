"""
traffic_monitoring_dag.py - Comprehensive Airflow DAG
======================================================
Orchestrates the complete real-time traffic violation monitoring pipeline:
- Producer: Fetch images from HCM City cameras → Kafka
- Processor: Spark Streaming with YOLO detection → Kafka
- Consumer: Kafka → PostgreSQL
- Dashboard: Streamlit visualization
"""

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.sensors.filesystem import FileSensor
from airflow.utils.trigger_rule import TriggerRule
from datetime import datetime, timedelta
import os

# ==========================
# DAG CONFIGURATION
# ==========================
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 12, 9),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=2),
    'execution_timeout': timedelta(hours=2),
}

# Paths
PROJECT_DIR = '/opt/airflow/projects/realtime-traffic-monitoring'
CONFIG_DIR = '/opt/airflow/config'

dag = DAG(
    'traffic_monitoring_full_pipeline',
    default_args=default_args,
    description='End-to-end real-time traffic violation monitoring with Producer, Processor, Consumer, and Dashboard',
    schedule_interval=None,  # Manual trigger for demo
    catchup=False,
    max_active_runs=1,
    tags=['traffic', 'kafka', 'spark', 'yolo', 'realtime'],
    doc_md="""
    ## Traffic Monitoring Pipeline
    
    This DAG orchestrates the complete traffic violation detection system:
    
    1. **Health Checks**: Verify Kafka broker connectivity
    2. **Producer**: Fetch real-time camera images from HCM City API
    3. **Spark Processor**: Run YOLO object detection and violation logic
    4. **DB Consumer**: Persist violations to PostgreSQL
    5. **Dashboard**: Real-time visualization with Streamlit
    
    ### Usage
    - Trigger manually from Airflow UI
    - Monitor logs for each task
    - Access dashboard at http://localhost:8501
    """
)

# ==========================
# HELPER FUNCTIONS
# ==========================
def check_kafka_broker():
    """Check if Kafka broker is accessible"""
    from kafka import KafkaConsumer
    from kafka.errors import NoBrokersAvailable
    import os
    
    bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
    
    try:
        consumer = KafkaConsumer(
            bootstrap_servers=bootstrap_servers,
            request_timeout_ms=10000,
            api_version_auto_timeout_ms=5000
        )
        topics = consumer.topics()
        consumer.close()
        print(f"✓ Kafka is healthy. Available topics: {topics}")
        return True
    except NoBrokersAvailable as e:
        print(f"✗ Kafka broker not available: {e}")
        raise


def check_postgres_connection():
    """Check PostgreSQL connection"""
    import psycopg2
    
    try:
        conn = psycopg2.connect(
            host='postgres',
            port='5432',
            dbname='airflow',
            user='airflow',
            password='airflow'
        )
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        print("✓ PostgreSQL connection successful")
        return True
    except Exception as e:
        print(f"✗ PostgreSQL connection failed: {e}")
        raise


# ==========================
# TASKS DEFINITION
# ==========================

# Task 1: Initialize Database Schema (runs once)
init_database = BashOperator(
    task_id='init_database_schema',
    bash_command=f"""
    echo "Initializing traffic monitoring database schema..."
    PGPASSWORD=airflow psql -h postgres -U airflow -d airflow -f {CONFIG_DIR}/init_traffic_monitoring.sql
    echo "✓ Database schema initialized"
    """,
    dag=dag,
)

# Task 2: Check Kafka Health
check_kafka = PythonOperator(
    task_id='check_kafka_health',
    python_callable=check_kafka_broker,
    dag=dag,
)

# Task 3: Check PostgreSQL Health
check_postgres = PythonOperator(
    task_id='check_postgres_health',
    python_callable=check_postgres_connection,
    dag=dag,
)

# Task 4: Start Producer (runs in background, limited duration for DAG)
start_producer = BashOperator(
    task_id='start_producer',
    bash_command=f"""
    echo "Starting Kafka Producer for traffic cameras..."
    cd {PROJECT_DIR}
    
    # Run producer for 5 minutes (for demo, adjust as needed)
    timeout 300 python kafka_producer.py || true
    
    echo "✓ Producer task completed"
    """,
    dag=dag,
)

# Task 5: Start Spark Streaming Processor
start_spark_processor = BashOperator(
    task_id='start_spark_streaming',
    bash_command=f"""
    echo "Starting Spark Streaming for violation detection..."
    cd {PROJECT_DIR}
    
    # Run Spark processor
    timeout 300 spark-submit \
      --master local[*] \
      --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
      --conf spark.sql.streaming.checkpointLocation=/tmp/spark_checkpoint \
      --conf spark.driver.memory=2g \
      --conf spark.executor.memory=2g \
      spark_processor.py || true
    
    echo "✓ Spark Streaming task completed"
    """,
    dag=dag,
)

# Task 6: Start DB Consumer
start_db_consumer = BashOperator(
    task_id='start_db_consumer',
    bash_command=f"""
    echo "Starting DB Consumer (Kafka → PostgreSQL)..."
    cd {PROJECT_DIR}
    
    # Run consumer for 5 minutes
    timeout 300 python db_consumer.py || true
    
    echo "✓ DB Consumer task completed"
    """,
    dag=dag,
)

# Task 7: Verify Data in Database
verify_data = BashOperator(
    task_id='verify_database_data',
    bash_command="""
    echo "Verifying data in PostgreSQL..."
    
    PGPASSWORD=airflow psql -h postgres -U airflow -d airflow -c "
    SELECT 'Cameras:' as table_name, COUNT(*) as count FROM cameras
    UNION ALL
    SELECT 'Violations:', COUNT(*) FROM traffic_violations
    UNION ALL
    SELECT 'Summaries:', COUNT(*) FROM detection_summary;
    "
    
    echo ""
    echo "Recent violations:"
    PGPASSWORD=airflow psql -h postgres -U airflow -d airflow -c "
    SELECT camera_id, violation_type, vehicle_type, confidence, detected_at 
    FROM traffic_violations 
    ORDER BY detected_at DESC 
    LIMIT 5;
    "
    
    echo "✓ Data verification completed"
    """,
    trigger_rule=TriggerRule.ALL_SUCCESS,
    dag=dag,
)

# Task 8: Generate Summary Report
generate_report = BashOperator(
    task_id='generate_summary_report',
    bash_command="""
    echo "=========================================="
    echo "        TRAFFIC MONITORING REPORT        "
    echo "=========================================="
    echo ""
    
    PGPASSWORD=airflow psql -h postgres -U airflow -d airflow -c "
    SELECT 
        camera_id,
        COUNT(*) as total_violations,
        COUNT(DISTINCT violation_type) as violation_types,
        ROUND(AVG(confidence)::numeric, 2) as avg_confidence,
        MIN(detected_at) as first_detection,
        MAX(detected_at) as last_detection
    FROM traffic_violations
    GROUP BY camera_id
    ORDER BY total_violations DESC;
    "
    
    echo ""
    echo "Violations by type:"
    PGPASSWORD=airflow psql -h postgres -U airflow -d airflow -c "
    SELECT violation_type, vehicle_type, COUNT(*) as count
    FROM traffic_violations
    GROUP BY violation_type, vehicle_type
    ORDER BY count DESC;
    "
    
    echo "=========================================="
    """,
    trigger_rule=TriggerRule.ALL_DONE,
    dag=dag,
)

# ==========================
# TASK DEPENDENCIES
# ==========================
# Phase 1: Initialization
init_database >> [check_kafka, check_postgres]

# Phase 2: Start all streaming components in parallel after health checks
[check_kafka, check_postgres] >> start_producer
[check_kafka, check_postgres] >> start_spark_processor
[check_kafka, check_postgres] >> start_db_consumer

# Phase 3: Verification after processing
[start_producer, start_spark_processor, start_db_consumer] >> verify_data

# Phase 4: Report generation
verify_data >> generate_report
