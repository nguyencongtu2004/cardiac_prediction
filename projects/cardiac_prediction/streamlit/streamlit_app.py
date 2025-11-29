import streamlit as st
import json
import os
from datetime import datetime

st.set_page_config(
    page_title="Cardiac Admission Prediction Dashboard",
    page_icon="❤️",
    layout="wide"
)

# Title
st.title("❤️ Cardiac Admission Outcome Prediction")
st.markdown("Real-time ML prediction system for cardiac readmission risk")

# Load model metrics
metrics_path = "/opt/airflow/projects/cardiac_prediction/models/cardiac_rf_model_metrics.json"

if os.path.exists(metrics_path):
    with open(metrics_path, 'r') as f:
        metrics = json.load(f)
    
    # Display metrics in columns
    st.header("📊 Model Performance Metrics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("AUC-ROC", f"{metrics.get('AUC-ROC', 0):.4f}")
        st.metric("F1 Score", f"{metrics.get('F1', 0):.4f}")
    
    with col2:
        st.metric("Precision", f"{metrics.get('Precision', 0):.4f}")
        st.metric("Recall", f"{metrics.get('Recall', 0):.4f}")
    
    with col3:
        st.metric("Accuracy", f"{metrics.get('Accuracy', 0):.4f}")
        st.metric("AUC-PR", f"{metrics.get('AUC-PR', 0):.4f}")
    
    st.success("✅ Model loaded successfully")
else:
    st.error("❌ Model metrics not found. Please train the model first.")

# System Status
st.header("🔧 System Status")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**Kafka Status**")
    st.success("🟢 Running")

with col2:
    st.markdown("**Spark Streaming**")
    st.info("🔵 Ready")

with col3:
    st.markdown("**Model Version**")
    st.info(f"v{datetime.now().strftime('%Y%m%d')}")

# Dataset Info
st.header("📁 Dataset Information")

metadata_path = "/opt/airflow/projects/cardiac_prediction/data/metadata.json"
if os.path.exists(metadata_path):
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Records", f"{metadata.get('total_records', 0):,}")
    
    with col2:
        st.metric("Class 0 (Normal)", f"{metadata.get('class_0_count', 0):,}")
    
    with col3:
        st.metric("Class 1 (High Risk)", f"{metadata.get('class_1_count', 0):,}")
    
    # Class distribution
    st.markdown(f"**Class Imbalance Ratio:** {metadata.get('class_weight', 0):.2f}:1")
    
    # Feature info
    st.markdown("**Features:**")
    st.markdown(f"- Continuous: {len(metadata.get('continuous_features', []))}")
    st.markdown(f"- Binary: {len(metadata.get('binary_features', []))}")

# Instructions
st.header("🚀 Quick Start Guide")

st.markdown("""
### Run the streaming pipeline:

1. **Start Producer & Consumer:**
   ```bash
   docker exec -it airflow-airflow-worker-1 bash
   bash /opt/airflow/projects/cardiac_prediction/scripts/run_streaming.sh
   ```

2. **Trigger Airflow DAG:**
   - Go to Airflow UI: http://localhost:8080
   - Enable and trigger `cardiac_streaming_lifecycle`

3. **Retrain Model (Daily):**
   - DAG: `cardiac_model_retraining` runs daily automatically
   - Manual trigger available in Airflow UI

### Project Structure:
- **Data:** `/projects/cardiac_prediction/data/`
- **Model:** `/projects/cardiac_prediction/models/cardiac_rf_model/`
- **Scripts:** `/projects/cardiac_prediction/scripts/`
""")

# Footer
st.markdown("---")
st.markdown("**Cardiac Admission Outcome Prediction** | Built with PySpark, Kafka, Airflow & Streamlit")
