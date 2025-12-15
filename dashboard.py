import streamlit as st
from kafka import KafkaConsumer
import json
import time
import os
import pandas as pd
from PIL import Image

# ==========================
# CONFIG
# ==========================
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
VIOLATION_TOPIC = 'traffic_violations'
IMAGE_TOPIC = 'camera_raw_frames'

st.set_page_config(page_title="Traffic Violation Monitor", layout="wide")

# ==========================
# SIDEBAR
# ==========================
st.sidebar.title("Configuration")
kafka_server = st.sidebar.text_input("Kafka Server", KAFKA_BOOTSTRAP_SERVERS)
auto_refresh = st.sidebar.checkbox("Auto Refresh", value=True)
show_raw_feed = st.sidebar.checkbox("Show Raw Camera Feed", value=True)

# ==========================
# MAIN LAYOUT
# ==========================
st.title("🚦 Real-Time Traffic Violation Monitoring")

col1, col2 = st.columns([2, 1])

with col1:
    st.header("Live Camera Feed")
    image_placeholder = st.empty()
    image_info_placeholder = st.empty()

with col2:
    st.header("Recent Violations")
    violations_placeholder = st.empty()

# Stats row
stat_col1, stat_col2, stat_col3 = st.columns(3)
with stat_col1:
    frames_metric = st.empty()
with stat_col2:
    violations_metric = st.empty()
with stat_col3:
    cameras_metric = st.empty()

# ==========================
# STATE
# ==========================
if 'violations' not in st.session_state:
    st.session_state.violations = []
if 'frames' not in st.session_state:
    st.session_state.frames = []
if 'frame_count' not in st.session_state:
    st.session_state.frame_count = 0

def process_raw_frames():
    """Process raw camera frames for live feed"""
    try:
        consumer = KafkaConsumer(
            IMAGE_TOPIC,
            bootstrap_servers=kafka_server,
            auto_offset_reset='latest',  # Only latest frames
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            consumer_timeout_ms=1000
        )
        
        latest_frame = None
        for message in consumer:
            data = message.value
            latest_frame = data
            st.session_state.frame_count += 1
        
        consumer.close()
        
        if latest_frame and 'image_path' in latest_frame:
            if os.path.exists(latest_frame['image_path']):
                try:
                    img = Image.open(latest_frame['image_path'])
                    image_placeholder.image(img, caption=f"📷 Camera: {latest_frame.get('camera_id')} | {latest_frame.get('timestamp', '')}", use_column_width=True)
                    image_info_placeholder.success(f"✅ Live feed active - Frame #{st.session_state.frame_count}")
                except Exception as e:
                    image_info_placeholder.error(f"Error loading image: {e}")
            else:
                image_info_placeholder.warning(f"Image not found: {latest_frame['image_path']}")
                
    except Exception as e:
        if "NoBrokersAvailable" in str(e):
            st.sidebar.error(f"❌ Cannot connect to Kafka at {kafka_server}")
        else:
            st.sidebar.warning(f"Raw frames: {e}")

def process_violations():
    """Process violation messages"""
    try:
        consumer = KafkaConsumer(
            VIOLATION_TOPIC,
            bootstrap_servers=kafka_server,
            auto_offset_reset='earliest',
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            consumer_timeout_ms=1000
        )
        
        new_events = []
        for message in consumer:
            data = message.value
            new_events.append(data)
            
            # Update Image with violation
            if 'image_path' in data and os.path.exists(data['image_path']):
                try:
                    img = Image.open(data['image_path'])
                    image_placeholder.image(img, caption=f"⚠️ VIOLATION - Camera: {data.get('camera_id')}", use_column_width=True)
                    
                    violations = json.loads(data['violations']) if isinstance(data['violations'], str) else data['violations']
                    if violations:
                        v_text = ""
                        for v in violations:
                            v_text += f"❌ **{v['type']}**: {v['vehicle']} (Conf: {v['confidence']:.2f})\n"
                        image_info_placeholder.markdown(v_text)
                        
                except Exception as e:
                    pass

        consumer.close()
        
        if new_events:
            st.session_state.violations = new_events + st.session_state.violations
            st.session_state.violations = st.session_state.violations[:50]
            
    except Exception as e:
        pass  # Silently fail for violations if no data

# ==========================
# DISPLAY LOOP
# ==========================
# Process raw frames first for live feed
if show_raw_feed:
    process_raw_frames()

# Then check for violations
process_violations()

# Update metrics
frames_metric.metric("📸 Frames Received", st.session_state.frame_count)
violations_metric.metric("⚠️ Violations", len(st.session_state.violations))
cameras_metric.metric("📹 Active Cameras", len(set(v.get('camera_id') for v in st.session_state.violations)) if st.session_state.violations else 0)

# Display Violation Log
df_violations = []
for v in st.session_state.violations:
    try:
        violation_list = json.loads(v['violations']) if isinstance(v['violations'], str) else v['violations']
        for viol in violation_list:
            df_violations.append({
                "Timestamp": v.get('timestamp'),
                "Camera": v.get('camera_id'),
                "Type": viol.get('type'),
                "Vehicle": viol.get('vehicle'),
                "Confidence": viol.get('confidence')
            })
    except:
        pass

if df_violations:
    df = pd.DataFrame(df_violations)
    violations_placeholder.dataframe(df, height=400)
else:
    violations_placeholder.info("🔍 Listening for violations...\n\nNo violations detected yet. The system is actively monitoring traffic.")

if auto_refresh:
    time.sleep(30)
    st.rerun()
