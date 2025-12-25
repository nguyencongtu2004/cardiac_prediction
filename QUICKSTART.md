# Quick Start Guide - Helmet Violation Detection System

## 📋 Prerequisites

Ensure you have:

- ✅ Docker and Docker Compose installed
- ✅ Video file: `data/video/bike-test.mp4`
- ✅ YOLO models in `models/` directory:
  - `yolov3-helmet.cfg`
  - `yolov3-helmet.weights`
  - `helmet.names`
  - `yolov8n.pt`

## 🚀 Quick Start (3 Steps)

### Step 1: Start the System

```bash
# From the project root directory
docker-compose up -d
```

This will start:

- ✅ Kafka & Zookeeper
- ✅ PostgreSQL database
- ✅ Video producer (streaming at 7 FPS)
- ✅ Helmet detector consumer
- ✅ Backend API
- ✅ Frontend dashboard

### Step 2: Wait for Services to Initialize

```bash
# Check service status
docker-compose ps

# All services should show "Up" or "healthy"
```

Wait for ~30 seconds for all services to be ready.

### Step 3: Open the Dashboard

Open your browser and navigate to:

```
http://localhost:3000
```

You should see:

- Real-time connection status (green ● Kết nối)
- Statistics dashboard
- Live violation updates

## 🔍 Monitoring

### View Logs

```bash
# All services
docker-compose logs -f

# Specific services
docker-compose logs -f helmet-video-producer
docker-compose logs -f helmet-detector-consumer
docker-compose logs -f traffic-backend
```

### Check Database

```bash
# Connect to PostgreSQL
docker exec -it postgres psql -U airflow -d traffic_monitoring

# Query violations
SELECT COUNT(*) FROM helmet_violations;
SELECT * FROM helmet_violations ORDER BY timestamp DESC LIMIT 5;
```

### Test API

```bash
# Get statistics
curl http://localhost:8000/api/stats

# Get latest violations
curl http://localhost:8000/api/violations/latest
```

## 🛑 Stop the System

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (reset database)
docker-compose down -v
```

## ⚡ Quick Testing

### Test Only Detection (Without Docker)

If you just want to test the detection on the video file:

```bash
# Install dependencies
pip install opencv-python numpy ultralytics kafka-python

# Run detector consumer (requires Kafka running)
python pipeline/consumers/helmet_detector_consumer.py
```

## 🎯 Key URLs

- **Dashboard**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (FastAPI automatic docs)
- **Kafka**: localhost:9092
- **PostgreSQL**: localhost:5432

## 📊 Expected Behavior

1. **Video Producer**: Streams frames at ~7 FPS

   - Check logs for: `[Frame XXXXXX] Sent #XXX | FPS: 7.XX`

2. **Detector**: Processes frames and detects violations

   - Check logs for: `[Frame XXX] ⚠️ X violation(s) detected!`

3. **Database**: Stores violations

   - Check with: `SELECT COUNT(*) FROM helmet_violations;`

4. **Dashboard**: Shows real-time updates
   - New violations appear automatically
   - Stats update every 10 seconds

## 🐛 Troubleshooting

### No violations detected?

- Check if video file exists: `ls -la data/video/bike-test.mp4`
- Check if models exist: `ls -la models/*.weights models/*.pt`
- View detector logs: `docker-compose logs helmet-detector-consumer`

### Dashboard not updating?

- Check WebSocket connection status (should be green)
- Check backend logs: `docker-compose logs traffic-backend`
- Refresh the page

### Services not starting?

- Check ports are not in use: `netstat -an | grep -E '(3000|8000|9092|5432)'`
- Check Docker resources (memory, CPU)
- View service logs: `docker-compose logs`

## 💡 Tips

- **Performance**: Adjust `TARGET_FPS` in docker-compose.yaml (5-10 recommended)
- **Loop Video**: Set `LOOP_VIDEO=true` for continuous testing
- **Database**: Data persists in Docker volume `postgres-db-volume`
- **Images**: Violation images saved in `./violations/` directory

## 📚 More Information

See [walkthrough.md](file:///C:/Users/LENOVO/.gemini/antigravity/brain/47e80830-6e41-4a51-a86e-2e6f07b8e17b/walkthrough.md) for complete documentation and verification steps.
