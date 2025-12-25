"""
helmet_violation_dag.py - Airflow DAG for Helmet Violation Detection
=====================================================================
Orchestrates the helmet violation detection pipeline using video streaming:
- Video Producer: Stream video frames → Kafka
- Helmet Detector: AI/ML detection (YOLOv3 + YOLOv8) → violations
- Backend: Persist to PostgreSQL + WebSocket broadcast

This DAG replaces the standalone Docker services:
- helmet-video-producer
- helmet-detector-consumer
"""

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.utils.trigger_rule import TriggerRule
from datetime import datetime, timedelta
import os

# ==========================
# DAG CONFIGURATION
# ==========================
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 12, 25),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=1),
    'execution_timeout': timedelta(hours=1),
}

# Paths
PROJECT_DIR = '/opt/airflow/projects/realtime-traffic-monitoring'
CONFIG_DIR = '/opt/airflow/config'

# Timeouts (seconds)
PRODUCER_TIMEOUT = int(os.getenv('PRODUCER_TIMEOUT', '300'))  # 5 minutes default
DETECTOR_TIMEOUT = int(os.getenv('DETECTOR_TIMEOUT', '300'))  # 5 minutes default

dag = DAG(
    'helmet_violation_pipeline',
    default_args=default_args,
    description='Helmet Violation Detection Pipeline - Video Producer + AI Detector',
    schedule_interval=None,  # Manual trigger
    catchup=False,
    max_active_runs=1,
    tags=['helmet', 'violation', 'kafka', 'yolo', 'realtime', 'video'],
    doc_md="""
    ## Helmet Violation Detection Pipeline
    
    This DAG orchestrates the helmet violation detection system from video:
    
    ### Pipeline Flow:
    1. **Init Database**: Create `helmet_violations` table if not exists
    2. **Health Checks**: Verify Kafka and PostgreSQL connectivity
    3. **Video Producer**: Stream video frames to Kafka at configured FPS
    4. **Helmet Detector**: Run YOLOv3 + YOLOv8 for violation detection
    5. **Verify Data**: Check violations stored in database
    6. **Generate Report**: Summary statistics
    
    ### Configuration:
    - `PRODUCER_TIMEOUT`: Duration to run video producer (default: 300s)
    - `DETECTOR_TIMEOUT`: Duration to run detector (default: 300s)
    - `TARGET_FPS`: Frames per second for video streaming (default: 7)
    
    ### Access:
    - Dashboard: http://localhost:3000
    - API: http://localhost:8000/api/stats
    - Violations: http://localhost:8000/api/violations
    
    ### Usage:
    1. Ensure video file exists at `data/video/bike-test.mp4`
    2. Ensure YOLO models exist in `models/` directory
    3. Trigger DAG manually from Airflow UI
    4. Monitor dashboard for real-time violations
    """
)

# ==========================
# HELPER FUNCTIONS
# ==========================
def check_kafka_broker():
    """Check if Kafka broker is accessible"""
    from kafka import KafkaConsumer
    from kafka.errors import NoBrokersAvailable
    import time
    
    bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
    
    max_retries = 5
    for attempt in range(max_retries):
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
            print(f"✗ Attempt {attempt+1}/{max_retries}: Kafka not available - {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
            else:
                raise


def check_postgres_connection():
    """Check PostgreSQL connection to traffic_monitoring database"""
    import psycopg2
    
    try:
        conn = psycopg2.connect(
            host='postgres',
            port='5432',
            dbname='traffic_monitoring',
            user='airflow',
            password='airflow'
        )
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        print("✓ PostgreSQL (traffic_monitoring) connection successful")
        return True
    except Exception as e:
        print(f"✗ PostgreSQL connection failed: {e}")
        raise


def check_models_exist():
    """Check if YOLO models are available"""
    models_dir = f"{PROJECT_DIR}/models"
    required_files = [
        "yolov3-helmet.cfg",
        "yolov3-helmet.weights",
        "helmet.names",
        "yolov8n.pt"
    ]
    
    missing = []
    for f in required_files:
        path = f"{models_dir}/{f}"
        if not os.path.exists(path):
            missing.append(f)
    
    if missing:
        raise FileNotFoundError(f"Missing model files: {missing}")
    
    print(f"✓ All YOLO models found in {models_dir}")
    return True


def check_video_exists():
    """Check if test video file exists"""
    video_path = f"{PROJECT_DIR}/data/video/bike-test.mp4"
    
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    print(f"✓ Video file found: {video_path}")
    return True


# ==========================
# TASKS DEFINITION
# ==========================

# Task 1: Initialize Helmet Violations Database Schema
init_helmet_database = BashOperator(
    task_id='init_helmet_database',
    bash_command=f"""
    echo "Initializing helmet violations database schema..."
    PGPASSWORD=airflow psql -h postgres -U airflow -d traffic_monitoring -f {CONFIG_DIR}/init_helmet_violations.sql
    echo "✓ Helmet violations table initialized"
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

# Task 4: Check YOLO Models Exist
check_models = PythonOperator(
    task_id='check_models_exist',
    python_callable=check_models_exist,
    dag=dag,
)

# Task 5: Check Video File Exists
check_video = PythonOperator(
    task_id='check_video_exists',
    python_callable=check_video_exists,
    dag=dag,
)

# Task 6: Start Video Producer (streams frames to Kafka)
start_video_producer = BashOperator(
    task_id='start_video_producer',
    bash_command=f"""
    echo "========================================"
    echo "Starting Video Producer..."
    echo "========================================"
    cd {PROJECT_DIR}
    
    # Set environment variables
    export KAFKA_BOOTSTRAP_SERVERS=kafka:29092
    export VIDEO_PATH={PROJECT_DIR}/data/video/bike-test.mp4
    export TARGET_FPS=${{TARGET_FPS:-7}}
    export CAMERA_ID=bike-test
    export LOOP_VIDEO=false
    
    echo "Configuration:"
    echo "  VIDEO_PATH: $VIDEO_PATH"
    echo "  TARGET_FPS: $TARGET_FPS"
    echo "  TIMEOUT: {PRODUCER_TIMEOUT}s"
    echo ""
    
    # Run producer with timeout
    timeout {PRODUCER_TIMEOUT} python pipeline/producers/video_producer.py || true
    
    echo ""
    echo "✓ Video Producer task completed"
    """,
    dag=dag,
)

# Task 7: Start Helmet Detector Consumer (runs AI detection)
start_helmet_detector = BashOperator(
    task_id='start_helmet_detector',
    bash_command=f"""
    echo "========================================"
    echo "Starting Helmet Detector Consumer..."
    echo "========================================"
    cd {PROJECT_DIR}
    
    # Set environment variables
    export KAFKA_BOOTSTRAP_SERVERS=kafka:29092
    
    echo "Configuration:"
    echo "  Models: {PROJECT_DIR}/models/"
    echo "  Output: {PROJECT_DIR}/violations/"
    echo "  TIMEOUT: {DETECTOR_TIMEOUT}s"
    echo ""
    
    # Run detector with timeout
    timeout {DETECTOR_TIMEOUT} python pipeline/consumers/helmet_detector_consumer.py || true
    
    echo ""
    echo "✓ Helmet Detector task completed"
    """,
    dag=dag,
)

# Task 8: Verify Violations in Database
verify_violations = BashOperator(
    task_id='verify_violations',
    bash_command="""
    echo "========================================"
    echo "Verifying Helmet Violations in Database"
    echo "========================================"
    
    echo ""
    echo "Total violations count:"
    PGPASSWORD=airflow psql -h postgres -U airflow -d traffic_monitoring -c "
    SELECT COUNT(*) as total_violations FROM helmet_violations;
    "
    
    echo ""
    echo "Violations by camera:"
    PGPASSWORD=airflow psql -h postgres -U airflow -d traffic_monitoring -c "
    SELECT camera_id, COUNT(*) as count 
    FROM helmet_violations 
    GROUP BY camera_id 
    ORDER BY count DESC;
    "
    
    echo ""
    echo "Recent violations (last 5):"
    PGPASSWORD=airflow psql -h postgres -U airflow -d traffic_monitoring -c "
    SELECT violation_id, camera_id, track_id, confidence, timestamp
    FROM helmet_violations 
    ORDER BY timestamp DESC 
    LIMIT 5;
    "
    
    echo ""
    echo "✓ Verification completed"
    """,
    trigger_rule=TriggerRule.ALL_DONE,  # Run even if detector times out
    dag=dag,
)

# Task 9: Generate Summary Report
generate_report = BashOperator(
    task_id='generate_report',
    bash_command="""
    echo "========================================"
    echo "  HELMET VIOLATION DETECTION REPORT    "
    echo "========================================"
    echo ""
    
    echo "📊 Statistics Summary:"
    PGPASSWORD=airflow psql -h postgres -U airflow -d traffic_monitoring -c "
    SELECT 
        COUNT(*) as total_violations,
        COUNT(DISTINCT camera_id) as cameras,
        COUNT(DISTINCT track_id) as unique_tracks,
        ROUND(AVG(confidence)::numeric, 3) as avg_confidence,
        MIN(timestamp) as first_detection,
        MAX(timestamp) as last_detection
    FROM helmet_violations;
    "
    
    echo ""
    echo "📈 Violations per hour (today):"
    PGPASSWORD=airflow psql -h postgres -U airflow -d traffic_monitoring -c "
    SELECT 
        DATE_TRUNC('hour', timestamp) as hour,
        COUNT(*) as violations
    FROM helmet_violations 
    WHERE DATE(timestamp) = CURRENT_DATE
    GROUP BY DATE_TRUNC('hour', timestamp)
    ORDER BY hour DESC
    LIMIT 10;
    "
    
    echo ""
    echo "========================================"
    echo "Dashboard: http://localhost:3000"
    echo "API Stats: http://localhost:8000/api/stats"
    echo "========================================"
    """,
    trigger_rule=TriggerRule.ALL_DONE,
    dag=dag,
)

# ==========================
# TASK DEPENDENCIES
# ==========================

# Phase 1: Initialization
init_helmet_database >> [check_kafka, check_postgres, check_models, check_video]

# Phase 2: Start streaming pipeline (producer must run before detector to have frames)
[check_kafka, check_postgres, check_models, check_video] >> start_video_producer
start_video_producer >> start_helmet_detector

# Phase 3: Verification and reporting
start_helmet_detector >> verify_violations >> generate_report
