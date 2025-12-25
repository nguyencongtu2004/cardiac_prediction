"""
helmet_demo_dag.py - Simple Demo DAG for Helmet Detection
=========================================================
Producer và Consumer chạy SONG SONG (parallel) để demo real-time streaming.
Đơn giản, nhẹ, dễ trigger.
"""

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.trigger_rule import TriggerRule
from datetime import datetime, timedelta
import os

# ==========================
# CONFIG
# ==========================
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 12, 25),
    'retries': 0,
    'execution_timeout': timedelta(minutes=10),
}

PROJECT_DIR = '/opt/airflow/projects/realtime-traffic-monitoring'

# Duration in seconds
STREAM_DURATION = int(os.getenv('STREAM_DURATION', '120'))  # 2 minutes default

dag = DAG(
    'helmet_demo_streaming',
    default_args=default_args,
    description='Demo: Producer & Consumer chạy song song - Helmet Violation Detection',
    schedule_interval=None,
    catchup=False,
    max_active_runs=1,
    tags=['demo', 'helmet', 'parallel', 'streaming'],
    doc_md="""
    ## 🎬 Demo Streaming DAG
    
    Producer và Consumer chạy **SONG SONG** để demo real-time detection.
    
    ### Flow:
    ```
    init_db
       ↓
    [start_producer] ←→ [start_detector]  (song song)
       ↓                    ↓
              summary
    ```
    
    ### Usage:
    1. Trigger DAG
    2. Mở dashboard: http://localhost:3002
    3. Xem violations hiển thị real-time
    
    ### Config:
    - `STREAM_DURATION`: Thời gian chạy (giây), mặc định 120s
    """
)

# ==========================
# TASKS
# ==========================

# Task 1: Quick init check
init_check = BashOperator(
    task_id='init_check',
    bash_command=f"""
    echo "🚀 Starting Helmet Demo..."
    echo "Duration: {STREAM_DURATION}s"
    
    # Check video exists
    if [ ! -f {PROJECT_DIR}/data/video/bike-test.mp4 ]; then
        echo "❌ Video not found!"
        exit 1
    fi
    echo "✓ Video found"
    
    # Check models exist
    if [ ! -f {PROJECT_DIR}/models/yolov8n.pt ]; then
        echo "❌ YOLOv8 model not found!"
        exit 1
    fi
    echo "✓ Models found"
    
    echo "✓ Ready to start streaming!"
    """,
    dag=dag,
)

# Task 2: Start Video Producer (runs in background-ish via timeout)
start_producer = BashOperator(
    task_id='start_producer',
    bash_command=f"""
    echo "📹 Starting Multi-Video Producer..."
    cd {PROJECT_DIR}
    
    export KAFKA_BOOTSTRAP_SERVERS=kafka:29092
    export VIDEO_DIR={PROJECT_DIR}/data/video
    export TARGET_FPS=5
    
    # Run producer for specified duration - streams ALL videos in parallel
    timeout {STREAM_DURATION} python pipeline/producers/video_producer.py || true
    
    echo "✓ Producer finished"
    """,
    dag=dag,
)

# Task 3: Start Helmet Detector (runs in PARALLEL with producer)
start_detector = BashOperator(
    task_id='start_detector',
    bash_command=f"""
    echo "🔍 Starting Helmet Detector..."
    cd {PROJECT_DIR}
    
    export KAFKA_BOOTSTRAP_SERVERS=kafka:29092
    
    # Small delay to let producer start first
    sleep 3
    
    # Run detector for specified duration
    timeout {STREAM_DURATION} python pipeline/consumers/helmet_detector_consumer.py || true
    
    echo "✓ Detector finished"
    """,
    dag=dag,
)

# Task 4: Summary
summary = BashOperator(
    task_id='summary',
    bash_command="""
    echo ""
    echo "=========================================="
    echo "         DEMO STREAMING COMPLETE         "
    echo "=========================================="
    
    echo ""
    echo "📊 Violations detected:"
    PGPASSWORD=airflow psql -h postgres -U airflow -d traffic_monitoring -t -c "
    SELECT COUNT(*) FROM helmet_violations WHERE timestamp > NOW() - INTERVAL '10 minutes';
    " 2>/dev/null || echo "0"
    
    echo ""
    echo "🌐 Dashboard: http://localhost:3002"
    echo "📡 API: http://localhost:8000/api/stats"
    echo "=========================================="
    """,
    trigger_rule=TriggerRule.ALL_DONE,
    dag=dag,
)

# ==========================
# DEPENDENCIES - PARALLEL!
# ==========================

# Producer và Detector chạy SONG SONG sau init
init_check >> [start_producer, start_detector]

# Summary chạy khi cả 2 xong
[start_producer, start_detector] >> summary
