from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

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
    description='Manage Cardiac Prediction Streaming Job',
    schedule_interval='@once',
    catchup=False,
    tags=['cardiac', 'streaming']
)

# Start Producer (Background)
start_producer = BashOperator(
    task_id='start_producer',
    bash_command='nohup python3 /opt/airflow/projects/cardiac_prediction/scripts/producer.py > /tmp/producer.log 2>&1 &',
    dag=dag
)

# Start Spark Streaming Job
start_streaming = BashOperator(
    task_id='start_spark_streaming',
    bash_command='spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.postgresql:postgresql:42.6.0 /opt/airflow/projects/cardiac_prediction/scripts/spark_streaming.py',
    dag=dag
)

start_producer >> start_streaming
