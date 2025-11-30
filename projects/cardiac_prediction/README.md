# Cardiac Admission Prediction System

## 📖 Overview
This project implements an end-to-end **Real-time Cardiac Admission Prediction System** using Big Data technologies. It ingests simulated patient health data, processes it in real-time using **Apache Spark**, applies a Machine Learning model to predict hospital admission risk, and visualizes the results on a **Streamlit** dashboard.

## 🏗 Architecture
The system follows a Lambda Architecture-inspired approach for real-time processing:

1.  **Data Source**: A Kafka Producer simulates real-time patient vitals (Heart Rate, BP, SPO2, etc.).
2.  **Message Queue**: **Apache Kafka** buffers the streaming data.
3.  **Stream Processing**: **Spark Structured Streaming** consumes data from Kafka, applies a pre-trained **Random Forest** model, and writes predictions to PostgreSQL.
4.  **Storage**: **PostgreSQL** stores raw data, predictions, and model metadata.
5.  **Visualization**: **Streamlit** provides a real-time dashboard for monitoring predictions and system health.
6.  **Orchestration**: **Apache Airflow** manages the lifecycle of streaming jobs and automates daily model retraining.

## 🚀 Quick Start

### Prerequisites
*   Docker & Docker Compose installed.
*   Git.

### Installation & Running

1.  **Start the Infrastructure**:
    ```bash
    docker-compose up -d
    ```

2.  **Initialize the Database**:
    ```bash
    bash config/setup_database.sh
    ```

3.  **Start the Streaming Pipeline**:
    *   **Option A (Recommended - via Airflow)**:
        1.  Access Airflow UI at [http://localhost:8080](http://localhost:8080) (User/Pass: `airflow`/`airflow`).
        2.  Trigger the DAG: `cardiac_streaming_lifecycle`.
    *   **Option B (Manual)**:
        ```bash
        # Start Producer
        docker exec -d airflow-airflow-worker-1 python3 /opt/airflow/projects/cardiac_prediction/scripts/producer.py
        
        # Start Spark Job
        docker exec -d airflow-airflow-worker-1 spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.postgresql:postgresql:42.6.0 /opt/airflow/projects/cardiac_prediction/scripts/spark_streaming.py
        ```

4.  **View the Dashboard**:
    *   Open [http://localhost:8501](http://localhost:8501) in your browser.

### 🔄 Model Retraining
The system includes an automated pipeline (`cardiac_model_retraining`) that runs daily to:
1.  Train a new model on the latest data.
2.  Evaluate it against the current production model.
3.  Automatically promote the new model if it performs better.

## 📂 Project Structure
```
projects/cardiac_prediction/
├── scripts/
│   ├── producer.py          # Kafka Data Generator
│   ├── spark_streaming.py   # Real-time Inference Job
│   ├── cardiac_model_train.py # Model Training Script
│   └── run_model_train.sh   # Training Wrapper
├── streamlit/
│   └── streamlit_app.py     # Dashboard
└── models/                  # Model Artifacts
```
