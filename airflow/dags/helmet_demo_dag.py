"""
violation_demo_dag.py - Unified Violation Detection Demo DAG
=============================================================
Producer và các Consumer (Helmet + Red Light) chạy SONG SONG để demo real-time streaming.
Tích hợp phát hiện: không đội mũ bảo hiểm + vượt đèn đỏ.
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
    'execution_timeout': timedelta(minutes=15),
}

PROJECT_DIR = '/opt/airflow/projects/realtime-traffic-monitoring'

# Duration in seconds
STREAM_DURATION = int(os.getenv('STREAM_DURATION', '300'))  # 5 minutes default

dag = DAG(
    'violation_demo_streaming',
    default_args=default_args,
    description='Demo: Phát hiện vi phạm giao thông (Helmet + Red Light)',
    schedule_interval=None,
    catchup=False,
    max_active_runs=1,
    tags=['demo', 'helmet', 'redlight', 'violation', 'parallel', 'streaming'],
    doc_md="""
    ## 🚦 Unified Violation Detection Demo
    
    Phát hiện **SONG SONG** các loại vi phạm:
    - 🪖 Không đội mũ bảo hiểm (Helmet)
    - 🚦 Vượt đèn đỏ (Red Light)
    
    ### Flow:
    ```
    init_check
       ↓
    start_producer
       ↓
    [helmet_detector] ←→ [redlight_detector]  (song song)
       ↓                       ↓
                summary
    ```
    
    ### Usage:
    1. Trigger DAG
    2. Mở dashboard: http://localhost:3002
    3. Xem violations hiển thị real-time
    
    ### Config:
    - `STREAM_DURATION`: Thời gian chạy (giây), mặc định 360s
    - ROI config: `config/roi_config.json` (cho Red Light)
    """
)

# ==========================
# TASKS
# ==========================

# Task 1: Init check
init_check = BashOperator(
    task_id='init_check',
    bash_command=f"""
    echo "🚀 Starting Unified Violation Detection Demo..."
    echo "Duration: {STREAM_DURATION}s"
    
    # Check video directory
    if [ ! -d {PROJECT_DIR}/data/video ]; then
        echo "❌ Video directory not found!"
        exit 1
    fi
    echo "✓ Video directory found"
    
    # Check models exist
    if [ ! -f {PROJECT_DIR}/models/yolov8n.pt ]; then
        echo "❌ YOLOv8 model not found!"
        exit 1
    fi
    echo "✓ YOLOv8 model found"
    
    # Check helmet model
    if [ -f {PROJECT_DIR}/models/yolov3-helmet.weights ]; then
        echo "✓ Helmet model found"
    else
        echo "⚠️ Helmet model not found - helmet detection may not work"
    fi
    
    # Check ROI config
    if [ -f {PROJECT_DIR}/config/roi_config.json ]; then
        echo "✓ ROI config found"
    else
        echo "⚠️ ROI config not found - using defaults"
    fi
    
    echo "✓ Ready to start streaming!"
    """,
    dag=dag,
)

# Task 2: Start Video Producer
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

# Task 3: Start Helmet Detector
helmet_detector = BashOperator(
    task_id='helmet_detector',
    bash_command=f"""
    echo "🪖 Starting Helmet Detector..."
    cd {PROJECT_DIR}
    
    export KAFKA_BOOTSTRAP_SERVERS=kafka:29092
    
    # Small delay to let producer start first
    sleep 3
    
    # Run detector for specified duration
    timeout {STREAM_DURATION} python pipeline/consumers/helmet_detector_consumer.py || true
    
    echo "✓ Helmet Detector finished"
    """,
    dag=dag,
)

# Task 4: Start Red Light Detector
redlight_detector = BashOperator(
    task_id='redlight_detector',
    bash_command=f"""
    echo "🚦 Starting Red Light Detector..."
    cd {PROJECT_DIR}
    
    export KAFKA_BOOTSTRAP_SERVERS=kafka:29092
    
    # Small delay to let producer start first
    sleep 3
    
    # Run detector for specified duration
    timeout {STREAM_DURATION} python pipeline/consumers/redlight_detector_consumer.py || true
    
    echo "✓ Red Light Detector finished"
    """,
    dag=dag,
)

# Task 5: Summary
summary = BashOperator(
    task_id='summary',
    bash_command="""
    echo ""
    echo "=========================================="
    echo "    VIOLATION DETECTION DEMO COMPLETE    "
    echo "=========================================="
    
    echo ""
    echo "🪖 Helmet Violations (last 15 min):"
    PGPASSWORD=airflow psql -h postgres -U airflow -d traffic_monitoring -t -c "
    SELECT COUNT(*) FROM helmet_violations WHERE timestamp > NOW() - INTERVAL '15 minutes';
    " 2>/dev/null || echo "0"
    
    echo ""
    echo "🚦 Red Light Violations (last 15 min):"
    PGPASSWORD=airflow psql -h postgres -U airflow -d traffic_monitoring -t -c "
    SELECT COUNT(*) FROM redlight_violations WHERE timestamp > NOW() - INTERVAL '15 minutes';
    " 2>/dev/null || echo "0"
    
    echo ""
    echo "🌐 Dashboard: http://localhost:3002"
    echo "📡 API Helmet: http://localhost:8000/api/stats"
    echo "📡 API RedLight: http://localhost:8000/api/redlight-stats"
    echo "=========================================="
    """,
    trigger_rule=TriggerRule.ALL_DONE,
    dag=dag,
)

# ==========================
# DEPENDENCIES
# ==========================

# Init → [Producer + Helmet + RedLight] (tất cả song song) → Summary
init_check >> [start_producer, helmet_detector, redlight_detector] >> summary
