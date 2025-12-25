from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from kafka import KafkaConsumer
import json
import asyncio
import os
import glob
import threading
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import uuid as uuid_lib

app = FastAPI(title="Helmet Violation Monitoring API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
HELMET_VIOLATION_TOPIC = 'helmet_violations'
TRAFFIC_VIOLATION_TOPIC = 'traffic_violations'
VIDEO_FRAMES_TOPIC = 'helmet_video_frames'  # Raw video frames for live camera view

# Database Configuration
DB_HOST = os.getenv('DB_HOST', 'postgres')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'traffic_monitoring')
DB_USER = os.getenv('DB_USER', 'airflow')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'airflow')

# Violations directory
VIOLATIONS_DIR = os.getenv('VIOLATIONS_DIR', '/app/violations')

# Video sources directory
VIDEO_DIR = os.getenv('VIDEO_DIR', '/app/data/video')

# Mount violations directory for serving images
if os.path.exists(VIOLATIONS_DIR):
    app.mount("/violations", StaticFiles(directory=VIOLATIONS_DIR), name="violations")

# Database connection
def get_db_connection():
    """Create database connection"""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        cursor_factory=RealDictCursor
    )

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"New WebSocket connection. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            try:
                self.active_connections.remove(conn)
            except:
                pass

manager = ConnectionManager()

# Camera stream manager for live video
class CameraStreamManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.latest_frames = {}  # camera_id -> frame_data

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"📹 New camera stream connection. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"📹 Camera stream disconnected. Total: {len(self.active_connections)}")

    async def broadcast_frame(self, frame_data: dict):
        """Broadcast frame to all connected clients"""
        # Store latest frame per camera
        camera_id = frame_data.get('camera_id', 'unknown')
        self.latest_frames[camera_id] = {
            'camera_id': camera_id,
            'timestamp': frame_data.get('timestamp'),
            'image_base64': frame_data.get('image_base64'),
            'frame_number': frame_data.get('frame_number')
        }
        
        if not self.active_connections:
            return
            
        message = json.dumps({
            'type': 'frame',
            'camera_id': camera_id,
            'timestamp': frame_data.get('timestamp'),
            'frame_number': frame_data.get('frame_number'),
            'image_base64': frame_data.get('image_base64')
        })
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)
        
        for conn in disconnected:
            self.disconnect(conn)

camera_manager = CameraStreamManager()

# Global variable to store latest violations (in-memory cache)
latest_violations = []

# Database operations
def save_violation_to_db(violation: dict):
    """Save violation to database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        bbox = violation.get('bounding_box', {})
        
        cursor.execute("""
            INSERT INTO helmet_violations 
            (violation_id, timestamp, camera_id, track_id, frame_number, confidence, 
             bbox_x, bbox_y, bbox_w, bbox_h, image_path, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (violation_id) DO NOTHING
        """, (
            violation.get('violation_id'),
            violation.get('timestamp'),
            violation.get('camera_id'),
            violation.get('track_id'),
            violation.get('frame_number'),
            violation.get('confidence'),
            bbox.get('x'),
            bbox.get('y'),
            bbox.get('w'),
            bbox.get('h'),
            violation.get('image_path'),
            json.dumps(violation.get('metadata', {}))
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        print(f"✓ Saved violation {violation.get('violation_id')} to database")
        return True
        
    except Exception as e:
        print(f"✗ Error saving violation to database: {e}")
        return False

# Kafka Consumer Thread for Helmet Violations
def helmet_kafka_consumer_thread():
    """Consume helmet violations from Kafka"""
    retries = 5
    for i in range(retries):
        try:
            consumer = KafkaConsumer(
                HELMET_VIOLATION_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                auto_offset_reset='latest',
                group_id='helmet-backend-group'
            )
            print(f"✓ Connected to Kafka (Helmet Violations): {KAFKA_BOOTSTRAP_SERVERS}")
            break
        except Exception as e:
            print(f"✗ Attempt {i+1}/{retries}: Cannot connect to Kafka - {e}")
            if i < retries - 1:
                import time
                time.sleep(5)
            else:
                print("Failed to connect to Kafka. Exiting consumer thread.")
                return
    
    for message in consumer:
        violation = message.value
        
        # Save to database
        save_violation_to_db(violation)
        
        # Broadcast to WebSockets
        asyncio.run(manager.broadcast(json.dumps(violation)))
        
        # Update in-memory cache (keep last 100)
        global latest_violations
        latest_violations.insert(0, violation)
        if len(latest_violations) > 100:
            latest_violations.pop()

# Kafka Consumer Thread for Traffic Violations (existing)
def traffic_kafka_consumer_thread():
    """Consume traffic violations from Kafka"""
    try:
        consumer = KafkaConsumer(
            TRAFFIC_VIOLATION_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            auto_offset_reset='latest',
            group_id='traffic-backend-group'
        )
        print(f"✓ Connected to Kafka (Traffic Violations): {KAFKA_BOOTSTRAP_SERVERS}")
        
        for message in consumer:
            violation = message.value
            asyncio.run(manager.broadcast(json.dumps(violation)))
    except Exception as e:
        print(f"✗ Traffic Kafka consumer error: {e}")

# Kafka Consumer for Video Frames (Live Camera)
def video_kafka_consumer_thread():
    """Consume video frames from Kafka for live camera view"""
    import time
    retries = 5
    for i in range(retries):
        try:
            consumer = KafkaConsumer(
                VIDEO_FRAMES_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                auto_offset_reset='latest',
                group_id='video-stream-backend-group',
                max_poll_records=1,  # Only get latest frame
                fetch_max_wait_ms=100
            )
            print(f"✓ Connected to Kafka (Video Frames): {KAFKA_BOOTSTRAP_SERVERS}")
            break
        except Exception as e:
            print(f"✗ Attempt {i+1}/{retries}: Cannot connect to Kafka Video Frames - {e}")
            if i < retries - 1:
                time.sleep(5)
            else:
                print("Failed to connect to Kafka Video Frames. Exiting consumer thread.")
                return
    
    for message in consumer:
        frame_data = message.value
        # Broadcast to connected WebSocket clients
        try:
            asyncio.run(camera_manager.broadcast_frame(frame_data))
        except Exception as e:
            pass  # Ignore broadcast errors

# Start Consumers in background
@app.on_event("startup")
async def startup_event():
    # Start helmet violations consumer
    t1 = threading.Thread(target=helmet_kafka_consumer_thread, daemon=True)
    t1.start()
    
    # Start traffic violations consumer (existing)
    t2 = threading.Thread(target=traffic_kafka_consumer_thread, daemon=True)
    t2.start()
    
    # Start video frames consumer for live camera
    t3 = threading.Thread(target=video_kafka_consumer_thread, daemon=True)
    t3.start()
    
    print("✓ Backend started successfully")

@app.get("/")
def read_root():
    return {
        "status": "Helmet Violation Monitoring Backend Running",
        "version": "1.0.0",
        "endpoints": {
            "violations": "/api/violations",
            "stats": "/api/stats",
            "websocket": "/ws"
        }
    }

@app.get("/api/violations")
def get_violations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    camera_id: Optional[str] = None
):
    """Get violations from database with pagination"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build query
        query = "SELECT * FROM helmet_violations"
        params = []
        
        if camera_id:
            query += " WHERE camera_id = %s"
            params.append(camera_id)
        
        query += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
        params.extend([limit, skip])
        
        cursor.execute(query, params)
        violations = cursor.fetchall()
        
        # Get total count
        count_query = "SELECT COUNT(*) as total FROM helmet_violations"
        if camera_id:
            count_query += " WHERE camera_id = %s"
            cursor.execute(count_query, [camera_id] if camera_id else [])
        else:
            cursor.execute(count_query)
        
        total = cursor.fetchone()['total']
        
        cursor.close()
        conn.close()
        
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "violations": violations
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/violations/latest")
def get_latest_violations():
    """Get latest violations from in-memory cache"""
    return {
        "total": len(latest_violations),
        "violations": latest_violations
    }

@app.get("/api/violations/{violation_id}")
def get_violation(violation_id: str):
    """Get specific violation by ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM helmet_violations WHERE violation_id = %s",
            (violation_id,)
        )
        violation = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not violation:
            raise HTTPException(status_code=404, detail="Violation not found")
        
        return violation
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/stats")
def get_stats():
    """Get violation statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total violations
        cursor.execute("SELECT COUNT(*) as total FROM helmet_violations")
        total = cursor.fetchone()['total']
        
        # Violations by camera
        cursor.execute("""
            SELECT camera_id, COUNT(*) as count 
            FROM helmet_violations 
            GROUP BY camera_id
        """)
        by_camera = cursor.fetchall()
        
        # Violations today
        cursor.execute("""
            SELECT COUNT(*) as today 
            FROM helmet_violations 
            WHERE DATE(timestamp) = CURRENT_DATE
        """)
        today = cursor.fetchone()['today']
        
        # Recent violations (last hour)
        cursor.execute("""
            SELECT COUNT(*) as recent 
            FROM helmet_violations 
            WHERE timestamp >= NOW() - INTERVAL '1 hour'
        """)
        recent = cursor.fetchone()['recent']
        
        cursor.close()
        conn.close()
        
        return {
            "total_violations": total,
            "violations_today": today,
            "violations_last_hour": recent,
            "by_camera": by_camera
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time violation updates"""
    await manager.connect(websocket)
    try:
        # Send initial latest violations
        await websocket.send_text(json.dumps({
            "type": "init",
            "violations": latest_violations[:10]
        }))
        
        # Keep connection alive
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.websocket("/ws/camera")
async def camera_stream_endpoint(websocket: WebSocket):
    """WebSocket endpoint for live camera video stream"""
    await camera_manager.connect(websocket)
    try:
        # Send initial message with available cameras
        await websocket.send_text(json.dumps({
            "type": "init",
            "message": "Connected to camera stream",
            "cameras": list(camera_manager.latest_frames.keys())
        }))
        
        # Keep connection alive and handle client messages
        while True:
            data = await websocket.receive_text()
            # Client can request latest frame for specific camera
            try:
                request = json.loads(data)
                if request.get('action') == 'get_frame':
                    camera_id = request.get('camera_id')
                    if camera_id and camera_id in camera_manager.latest_frames:
                        await websocket.send_text(json.dumps({
                            "type": "frame",
                            **camera_manager.latest_frames[camera_id]
                        }))
            except:
                pass
    except WebSocketDisconnect:
        camera_manager.disconnect(websocket)

@app.get("/api/cameras")
def get_cameras():
    """Get list of active cameras with latest frame info"""
    return {
        "cameras": [
            {
                "camera_id": camera_id,
                "timestamp": frame.get('timestamp'),
                "frame_number": frame.get('frame_number')
            }
            for camera_id, frame in camera_manager.latest_frames.items()
        ]
    }

@app.get("/api/videos")
def get_available_videos():
    """Get list of available video files that can be used for streaming"""
    videos = []
    
    if not os.path.isdir(VIDEO_DIR):
        return {"videos": [], "video_dir": VIDEO_DIR, "error": "Directory not found"}
    
    # Scan for video files
    video_extensions = ['*.mp4', '*.avi', '*.mkv', '*.mov']
    for pattern in video_extensions:
        for video_path in glob.glob(os.path.join(VIDEO_DIR, pattern)):
            filename = os.path.basename(video_path)
            name_without_ext = os.path.splitext(filename)[0]
            
            # Get file stats
            try:
                stat = os.stat(video_path)
                size_mb = stat.st_size / (1024 * 1024)
            except:
                size_mb = 0
            
            videos.append({
                "id": name_without_ext,
                "filename": filename,
                "path": video_path,
                "size_mb": round(size_mb, 2),
                "camera_id": name_without_ext  # Default camera ID = filename
            })
    
    # Sort by filename
    videos.sort(key=lambda x: x['filename'])
    
    return {
        "videos": videos,
        "count": len(videos),
        "video_dir": VIDEO_DIR
    }

