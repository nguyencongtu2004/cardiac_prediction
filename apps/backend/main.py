from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from kafka import KafkaConsumer
import json
import asyncio
import os
import threading
from typing import List

app = FastAPI()

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
VIOLATION_TOPIC = 'traffic_violations'

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass

manager = ConnectionManager()

# Global variable to store latest violations
latest_violations = []

# Kafka Consumer Thread
def kafka_consumer_thread():
    consumer = KafkaConsumer(
        VIOLATION_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        auto_offset_reset='latest'
    )
    
    print(f"Connected to Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
    
    for message in consumer:
        violation = message.value
        # Broadcast to WebSockets
        asyncio.run(manager.broadcast(json.dumps(violation)))
        
        # Update latest list (keep last 50)
        global latest_violations
        latest_violations.insert(0, violation)
        if len(latest_violations) > 50:
            latest_violations.pop()

# Start Consumer in background
@app.on_event("startup")
async def startup_event():
    t = threading.Thread(target=kafka_consumer_thread, daemon=True)
    t.start()

@app.get("/")
def read_root():
    return {"status": "Traffic Monitoring Backend Running"}

@app.get("/violations")
def get_violations():
    return latest_violations

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
