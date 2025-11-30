import streamlit as st
import pandas as pd
import psycopg2
import time
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Cấu hình trang
st.set_page_config(
    page_title="Cardiac Prediction Dashboard",
    page_icon="❤️",
    layout="wide"
)

# Cấu hình Database
DB_CONFIG = {
    "dbname": "airflow",
    "user": "airflow",
    "password": "airflow",
    "host": "postgres",
    "port": "5432"
}

def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        return None

def load_data():
    conn = get_db_connection()
    if conn:
        query = "SELECT * FROM cardiac_predictions ORDER BY prediction_time DESC LIMIT 100"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    return pd.DataFrame()

def load_model_metrics():
    conn = get_db_connection()
    if conn:
        query = "SELECT * FROM model_performance_summary LIMIT 1"
        df = pd.read_sql(query, conn)
        conn.close()
        if not df.empty:
            return df.iloc[0]
    return None

# Header
st.title("❤️ Real-time Cardiac Admission Prediction")
st.markdown("Monitoring real-time patient data and prediction results.")

# Auto-refresh logic
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh > 5:
    st.rerun()
    st.session_state.last_refresh = time.time()

# Load Data
df = load_data()
metrics = load_model_metrics()

# Metrics Section
st.header("📊 System Performance")
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_predictions = len(df) if not df.empty else 0
    st.metric("Recent Predictions", total_predictions)

with col2:
    if not df.empty:
        positive_rate = (df['result_class'].sum() / total_predictions) * 100
        st.metric("High Risk Rate", f"{positive_rate:.1f}%")
    else:
        st.metric("High Risk Rate", "N/A")

with col3:
    if metrics is not None:
        st.metric("Current Model Accuracy", f"{float(metrics['accuracy']):.4f}")
    else:
        st.metric("Current Model Accuracy", "N/A")

with col4:
    if metrics is not None:
        st.metric("Model Version", "v1") # Placeholder or from DB
    else:
        st.metric("Model Version", "N/A")

# Charts Section
if not df.empty:
    st.header("📈 Real-time Analysis")
    
    c1, c2 = st.columns(2)
    
    with c1:
        # Pie chart for Risk Distribution
        risk_counts = df['result_class'].value_counts()
        fig_pie = px.pie(values=risk_counts.values, names=['Normal', 'High Risk'], title="Risk Distribution (Last 100)")
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with c2:
        # Scatter plot Age vs Heart Rate
        fig_scatter = px.scatter(df, x="age", y="heart_rate", color="result_class", 
                                 title="Age vs Heart Rate Correlation",
                                 labels={"result_class": "Risk Level"})
        st.plotly_chart(fig_scatter, use_container_width=True)

    # Recent Data Table
    st.header("📋 Recent Predictions Log")
    # Display columns matching new schema
    display_cols = ['prediction_time', 'age', 'sex', 'heart_rate', 'bp_sys', 'bp_dia', 'spo2', 'result_class']
    # Filter columns that actually exist in df
    valid_cols = [c for c in display_cols if c in df.columns]
    st.dataframe(df[valid_cols].head(10))

else:
    st.info("Waiting for data stream...")

# Footer
st.markdown("---")
st.markdown(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
