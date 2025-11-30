import streamlit as st
import pandas as pd
import psycopg2
import time
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

# Cấu hình trang
st.set_page_config(
    page_title="Cardiac Prediction Dashboard",
    page_icon="❤️",
    layout="wide",
    initial_sidebar_state="expanded"
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

@st.cache_data(ttl=2)  # Cache for 2 seconds
def load_data(limit=100):
    conn = get_db_connection()
    if conn:
        query = f"SELECT * FROM cardiac_predictions ORDER BY prediction_time DESC LIMIT {limit}"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    return pd.DataFrame()

@st.cache_data(ttl=5)  # Cache for 5 seconds
def load_recent_stats():
    """Load statistics for last 5 minutes"""
    conn = get_db_connection()
    if conn:
        query = """
        SELECT 
            COUNT(*) as total_predictions,
            SUM(CASE WHEN result_class = 1 THEN 1 ELSE 0 END) as high_risk_count,
            AVG(CASE WHEN result_class = 1 THEN 1.0 ELSE 0.0 END) * 100 as high_risk_rate,
            AVG(heart_rate) as avg_heart_rate,
            AVG(bp_sys) as avg_bp_sys,
            AVG(spo2) as avg_spo2
        FROM cardiac_predictions 
        WHERE prediction_time > NOW() - INTERVAL '5 minutes'
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df.iloc[0] if not df.empty else None
    return None

@st.cache_data(ttl=10)  # Cache for 10 seconds
def load_time_series_data():
    """Load time series data for charts"""
    conn = get_db_connection()
    if conn:
        query = """
        SELECT 
            DATE_TRUNC('minute', prediction_time) as time_bucket,
            COUNT(*) as prediction_count,
            SUM(CASE WHEN result_class = 1 THEN 1 ELSE 0 END) as high_risk_count,
            AVG(heart_rate) as avg_heart_rate,
            AVG(bp_sys) as avg_bp_sys
        FROM cardiac_predictions 
        WHERE prediction_time > NOW() - INTERVAL '30 minutes'
        GROUP BY time_bucket
        ORDER BY time_bucket DESC
        """
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

# Custom CSS for modern UI
st.markdown("""
<style>
    .block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
    div[data-testid="stMetricValue"] {font-size: 2rem; font-weight: 700; color: #1f77b4;}
    div[data-testid="stMetricLabel"] {font-size: 1rem; font-weight: 600; color: #555;}
    .risk-high {background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 0.3rem 0.8rem; border-radius: 20px; color: white; font-weight: 600;}
    .risk-low {background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); padding: 0.3rem 0.8rem; border-radius: 20px; color: white; font-weight: 600;}
    .dataframe thead th {background-color: #667eea !important; color: white !important; font-weight: 600 !important;}
    h1 {background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800;}
</style>
""", unsafe_allow_html=True)

# Auto-refresh setup (every 2 seconds)
if 'last_update' not in st.session_state:
    st.session_state.last_update = time.time()

if time.time() - st.session_state.last_update > 2:
    st.session_state.last_update = time.time()
    st.rerun()

# Header
st.title("🫀 Dashboard Dự Đoán Tái Nhập Viện Tim Mạch")
st.markdown("**Cập nhật tự động mỗi 2 giây** | Dữ liệu thời gian thực từ Kafka Stream")

# Load Data
df = load_data(limit=100)
stats = load_recent_stats()
time_series = load_time_series_data()

if df.empty:
    st.warning("⚠️ Chưa có dữ liệu dự đoán. Vui lòng kiểm tra Kafka producer.")
    st.stop()

# Metrics Section
st.markdown("### 📊 Thống Kê 5 Phút Gần Nhất")
col1, col2, col3, col4 = st.columns(4)

if stats is not None:
    with col1:
        st.metric("Tổng Dự Đoán", f"{int(stats['total_predictions']):,}")
    with col2:
        st.metric("⚠️ Nguy Cơ Cao", int(stats['high_risk_count']), delta=f"{stats['high_risk_rate']:.1f}%")
    with col3:
        st.metric("✅ Nguy Cơ Thấp", int(stats['total_predictions'] - stats['high_risk_count']))
    with col4:
        st.metric("❤️ Nhịp Tim TB", f"{stats['avg_heart_rate']:.0f} bpm", delta=f"SpO2: {stats['avg_spo2']:.1f}%")
else:
    with col1:
        st.metric("Tổng Dự Đoán", len(df))
    with col2:
        high_risk = len(df[df['result_class'] == 1])
        st.metric("⚠️ Nguy Cơ Cao", high_risk, delta=f"{high_risk/len(df)*100:.1f}%")
    with col3:
        st.metric("✅ Nguy Cơ Thấp", len(df) - high_risk)
    with col4:
        avg_hr = df['heart_rate'].mean() if 'heart_rate' in df.columns else 0
        st.metric("❤️ Nhịp Tim TB", f"{avg_hr:.0f} bpm")

# Time Series Chart
if not time_series.empty:
    st.markdown("### 📈 Xu Hướng Dự Đoán Theo Thời Gian (30 Phút Gần Nhất)")
    
    fig_time = px.line(
        time_series, 
        x='time_bucket', 
        y=['prediction_count', 'high_risk_count'],
        labels={'value': 'Số lượng', 'time_bucket': 'Thời gian', 'variable': 'Loại'},
        title="Dự đoán theo phút"
    )
    fig_time.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(size=12),
        legend=dict(title="", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_time, use_container_width=True)

# Charts Section
st.markdown("### 📊 Phân Tích Dữ Liệu")
c1, c2 = st.columns(2)

with c1:
    # Pie chart for Risk Distribution
    risk_counts = df['result_class'].value_counts()
    fig_pie = px.pie(
        values=risk_counts.values, 
        names=['Bình thường', 'Nguy cơ cao'], 
        title="Phân Bố Nguy Cơ (100 dự đoán gần nhất)",
        color_discrete_sequence=['#4facfe', '#f5576c']
    )
    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig_pie, use_container_width=True)
    
with c2:
    # Scatter plot Age vs Heart Rate
    fig_scatter = px.scatter(
        df, 
        x="age", 
        y="heart_rate", 
        color="result_class", 
        title="Tuổi & Nhịp Tim",
        labels={"result_class": "Nguy cơ", "age": "Tuổi", "heart_rate": "Nhịp tim"},
        color_discrete_map={0: '#4facfe', 1: '#f5576c'}
    )
    fig_scatter.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_scatter, use_container_width=True)

# Recent Predictions Table with Enhanced Styling
st.markdown("### 📋 Nhật Ký Dự Đoán Gần Nhất")

# Prepare display data with Vietnamese labels
df_display = df.head(20).copy()
df_display['Thời gian'] = df_display['prediction_time'].dt.strftime('%H:%M:%S')
df_display['Tuổi'] = df_display['age']
df_display['Giới tính'] = df_display['sex'].map({0: 'Nữ', 1: 'Nam'})
df_display['Nhịp tim'] = df_display['heart_rate'].astype(int)
df_display['Huyết áp'] = df_display['bp_sys'].astype(int).astype(str) + '/' + df_display['bp_dia'].astype(int).astype(str)
df_display['SpO2'] = df_display['spo2'].round(1).astype(str) + '%'

# Risk level with color coding
def format_risk(row):
    if row['result_class'] == 1:
        return f'<span class="risk-high">NGUY CƠ CAO</span>'
    else:
        return f'<span class="risk-low">BÌNH THƯỜNG</span>'

df_display['Kết quả'] = df_display.apply(format_risk, axis=1)

# Select columns to display
display_cols = ['Thời gian', 'Tuổi', 'Giới tính', 'Nhịp tim', 'Huyết áp', 'SpO2', 'Kết quả']
df_final = df_display[display_cols]

# Display with custom styling
st.markdown(df_final.to_html(escape=False, index=False), unsafe_allow_html=True)

# Footer with refresh indicator
st.markdown("---")
col_a, col_b, col_c = st.columns([2, 1, 1])
with col_a:
    st.markdown(f"**Cập nhật lần cuối:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
with col_b:
    st.markdown(f"**Model:** v1 (RF Ensemble)")
with col_c:
    st.markdown(f"**🟢 Đang chạy**")
