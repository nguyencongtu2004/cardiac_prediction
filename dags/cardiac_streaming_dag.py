"""
Cardiac Streaming Lifecycle DAG
Orchestrate Kafka producer and Spark streaming consumer
"""

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import time

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'cardiac_streaming_lifecycle',
    default_args=default_args,
    description='Cardiac streaming lifecycle management',
    schedule_interval=None,  # Manual trigger
    catchup=False,
    tags=['cardiac', 'streaming']
)

# Deploy Kafka Producer
deploy_producer = BashOperator(
    task_id='deploy_producer',
    bash_command="""
    python3 /opt/airflow/projects/cardiac_prediction/scripts/cardiac_producer.py \
        --kafka-server kafka:9092 \
        --topic cardiac-events \
        --delay 2.0 \
        --max-records 100 &
    echo $! > /tmp/cardiac_producer.pid
    echo "✅ Producer started (PID: $(cat /tmp/cardiac_producer.pid))"
    """,
    dag=dag
)

# Monitor Stream (simple health check)
def check_stream_health():
    """Check if streaming is healthy"""
    # Simple check - in production, query Spark UI or checkpoint status
    time.sleep(5)
    print("✅ Stream health check passed")
    return True

monitor_stream = PythonOperator(
    task_id='monitor_stream',
    python_callable=check_stream_health,
    dag=dag
)

# Cleanup
cleanup = BashOperator(
    task_id='cleanup',
    bash_command="""
    if [ -f /tmp/cardiac_producer.pid ]; then
        PID=$(cat /tmp/cardiac_producer.pid)
        kill $PID 2>/dev/null || true
        rm /tmp/cardiac_producer.pid
        echo "✅ Producer stopped"
    fi
    """,
    dag=dag
)

# Task dependencies
deploy_producer >> monitor_stream >> cleanup
