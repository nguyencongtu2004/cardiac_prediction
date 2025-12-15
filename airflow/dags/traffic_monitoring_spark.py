from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 12, 8),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'traffic_monitoring_spark_streaming',
    default_args=default_args,
    description='Real-time traffic violation detection using Spark Streaming',
    schedule_interval=None,  # Manual trigger
    catchup=False,
    tags=['traffic', 'spark', 'streaming'],
)

# Submit Spark Streaming Job
spark_submit = BashOperator(
    task_id='run_spark_streaming',
    bash_command="""
    cd /opt/airflow/projects/realtime-traffic-monitoring && \
    spark-submit \
      --master local[*] \
      --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
      --conf spark.sql.streaming.checkpointLocation=/tmp/spark_checkpoint \
      --conf spark.driver.memory=2g \
      --conf spark.executor.memory=2g \
      --conf spark.pyspark.python=/usr/local/bin/python \
      spark_processor.py
    """,
    dag=dag,
)

spark_submit
