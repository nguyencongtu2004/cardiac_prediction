"""
Cardiac Model Retraining DAG
Daily retraining with evaluation and promotion
"""

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import json
import os

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
    'cardiac_model_retraining',
    default_args=default_args,
    description='Daily cardiac model retraining and promotion',
    schedule_interval='@daily',
    catchup=False,
    tags=['cardiac', 'training']
)

# Train new model
train_model = BashOperator(
    task_id='train_model',
    bash_command='bash /opt/airflow/projects/cardiac_prediction/scripts/run_model_train.sh',
    dag=dag
)

# Evaluate and promote
def evaluate_and_promote():
    """Compare new model with current and promote if better"""
    
    # Load new metrics
    new_metrics_path = "/opt/airflow/models/cardiac_rf_model_metrics.json"
    if not os.path.exists(new_metrics_path):
        print("❌ No new metrics found")
        return False
    
    with open(new_metrics_path, 'r') as f:
        new_metrics = json.load(f)
    
    # Load current metrics (if exists)
    current_metrics_path = "/opt/airflow/projects/cardiac_prediction/models/cardiac_rf_model_metrics.json"
    
    if os.path.exists(current_metrics_path):
        with open(current_metrics_path, 'r') as f:
            current_metrics = json.load(f)
        
        print("\n" + "="*80)
        print("MODEL COMPARISON")
        print("="*80)
        print(f"Current AUC-ROC: {current_metrics.get('AUC-ROC', 0):.4f}")
        print(f"New AUC-ROC:     {new_metrics.get('AUC-ROC', 0):.4f}")
        
        # Promote if better
        if new_metrics.get('AUC-ROC', 0) > current_metrics.get('AUC-ROC', 0):
            print("\n✅ New model is better! Promoting...")
            os.system("cp -r /opt/airflow/models/cardiac_rf_model /opt/airflow/projects/cardiac_prediction/models/cardiac_rf_model_backup")
            os.system("cp -r /opt/airflow/models/cardiac_rf_model /opt/airflow/projects/cardiac_prediction/models/")
            os.system("cp /opt/airflow/models/cardiac_rf_model_metrics.json /opt/airflow/projects/cardiac_prediction/models/")
            print("✅ Model promoted successfully")
            return True
        else:
            print("\n⚠️  New model is not better. Keeping current model.")
            return False
    else:
        # First time training
        print("\n✅ First model training. Promoting by default...")
        os.system("cp -r /opt/airflow/models/cardiac_rf_model /opt/airflow/projects/cardiac_prediction/models/")
        os.system("cp /opt/airflow/models/cardiac_rf_model_metrics.json /opt/airflow/projects/cardiac_prediction/models/")
        print("✅ Model promoted successfully")
        return True

evaluate_promote = PythonOperator(
    task_id='evaluate_and_promote',
    python_callable=evaluate_and_promote,
    dag=dag
)

# Task dependencies
train_model >> evaluate_promote
