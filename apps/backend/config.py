"""
Configuration settings for the backend API
"""
import os

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
HELMET_VIOLATION_TOPIC = 'helmet_violations'
TRAFFIC_VIOLATION_TOPIC = 'traffic_violations'
VIDEO_FRAMES_TOPIC = 'helmet_video_frames'

# Database Configuration
DB_HOST = os.getenv('DB_HOST', 'postgres')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'traffic_monitoring')
DB_USER = os.getenv('DB_USER', 'airflow')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'airflow')

# Directory Configuration
VIOLATIONS_DIR = os.getenv('VIOLATIONS_DIR', '/app/violations')
VIDEO_DIR = os.getenv('VIDEO_DIR', '/app/data/video')
