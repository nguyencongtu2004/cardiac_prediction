import os
import time
import json
import base64
import cv2
import glob
import threading
from datetime import datetime
from kafka import KafkaProducer
from kafka.errors import KafkaError
import uuid

# ==========================
# CẤU HÌNH
# ==========================
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
KAFKA_TOPIC = 'helmet_video_frames'

# Support single video path OR directory with multiple videos
VIDEO_PATH = os.getenv('VIDEO_PATH', '')
VIDEO_DIR = os.getenv('VIDEO_DIR', '/app/data/video')
TARGET_FPS = float(os.getenv('TARGET_FPS', '7'))  # 5-10 fps
CAMERA_ID = os.getenv('CAMERA_ID', '')  # If empty, use filename as camera_id
LOOP_VIDEO = os.getenv('LOOP_VIDEO', 'false').lower() == 'true'  # Default: no loop

# ==========================
# KAFKA PRODUCER SETUP
# ==========================
def create_producer():
    """Tạo Kafka Producer với retry logic"""
    retries = 5
    for i in range(retries):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                max_request_size=10485760,  # 10MB for base64 images
                acks='all',
                retries=3,
                compression_type='gzip'
            )
            print(f"✓ Kết nối Kafka thành công tại {KAFKA_BOOTSTRAP_SERVERS}")
            return producer
        except KafkaError as e:
            print(f"✗ Lần {i+1}/{retries}: Không thể kết nối Kafka - {e}")
            if i < retries - 1:
                time.sleep(5)
            else:
                raise Exception("Không thể kết nối tới Kafka sau nhiều lần thử")

# ==========================
# VIDEO STREAMING
# ==========================
def stream_single_video(producer: KafkaProducer, video_path: str, camera_id: str):
    """Stream a single video file to Kafka"""
    
    if not os.path.exists(video_path):
        print(f"✗ Video file not found: {video_path}")
        return
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"✗ Cannot open video: {video_path}")
        return
    
    # Get video properties
    original_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = total_frames / original_fps if original_fps > 0 else 0
    
    print(f"\n[{camera_id}] Starting stream:")
    print(f"  Video: {os.path.basename(video_path)}")
    print(f"  FPS: {original_fps:.1f} → {TARGET_FPS:.1f}")
    print(f"  Frames: {total_frames} ({duration:.1f}s)")
    print(f"  Loop: {LOOP_VIDEO}")
    
    # Calculate frame skip to achieve target FPS
    frame_skip = max(1, int(original_fps / TARGET_FPS))
    frame_interval = 1.0 / TARGET_FPS
    
    frame_count = 0
    sent_count = 0
    start_time = time.time()
    
    try:
        while True:
            ret, frame = cap.read()
            
            # If video ended
            if not ret:
                if LOOP_VIDEO:
                    print(f"[{camera_id}] ⟳ Restarting video loop...")
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    frame_count = 0
                    continue
                else:
                    break
            
            frame_count += 1
            
            # Skip frames to match target FPS
            if frame_count % frame_skip != 0:
                continue
            
            # Resize for bandwidth
            height = frame.shape[0]
            if height > 720:
                scale = 720 / height
                frame = cv2.resize(frame, None, fx=scale, fy=scale)
            
            # Encode frame to JPEG then base64
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            image_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # Create message
            message = {
                "camera_id": camera_id,
                "frame_number": frame_count,
                "timestamp": datetime.now().isoformat(),
                "image_base64": image_base64,
                "width": frame.shape[1],
                "height": frame.shape[0]
            }
            
            # Send to Kafka
            try:
                future = producer.send(KAFKA_TOPIC, value=message)
                sent_count += 1
                
                # Progress every 50 frames
                if sent_count % 50 == 0:
                    print(f"[{camera_id}] Sent {sent_count} frames ({frame_count}/{total_frames})")
            except Exception as e:
                print(f"[{camera_id}] Error sending frame: {e}")
            
            # Control frame rate
            next_frame_time = start_time + (sent_count * frame_interval)
            sleep_time = next_frame_time - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    except KeyboardInterrupt:
        print(f"[{camera_id}] Interrupted")
    
    finally:
        cap.release()
        elapsed = time.time() - start_time
        avg_fps = sent_count / elapsed if elapsed > 0 else 0
        
        print(f"\n[{camera_id}] ✓ Completed:")
        print(f"  Frames sent: {sent_count}/{frame_count}")
        print(f"  Duration: {elapsed:.1f}s")
        print(f"  Avg FPS: {avg_fps:.1f}")

def get_video_files():
    """Get list of video files to stream"""
    videos = []
    
    # If single video path is specified
    if VIDEO_PATH and os.path.isfile(VIDEO_PATH):
        camera_id = CAMERA_ID or os.path.splitext(os.path.basename(VIDEO_PATH))[0]
        videos.append((VIDEO_PATH, camera_id))
    
    # Scan directory for all video files
    elif os.path.isdir(VIDEO_DIR):
        patterns = ['*.mp4', '*.avi', '*.mkv', '*.mov']
        for pattern in patterns:
            for video_path in glob.glob(os.path.join(VIDEO_DIR, pattern)):
                camera_id = os.path.splitext(os.path.basename(video_path))[0]
                videos.append((video_path, camera_id))
    
    return videos

def main():
    """Main function - stream all videos in parallel"""
    print("\n" + "="*70)
    print("Video Producer - Multi-Video Parallel Streaming")
    print("="*70)
    
    # Get video files
    videos = get_video_files()
    
    if not videos:
        print("✗ No video files found!")
        print(f"  VIDEO_PATH: {VIDEO_PATH}")
        print(f"  VIDEO_DIR: {VIDEO_DIR}")
        return
    
    print(f"Found {len(videos)} video(s):")
    for video_path, camera_id in videos:
        print(f"  - [{camera_id}] {os.path.basename(video_path)}")
    print("="*70 + "\n")
    
    # Create producer
    producer = create_producer()
    
    # Start thread for each video
    threads = []
    for video_path, camera_id in videos:
        t = threading.Thread(
            target=stream_single_video,
            args=(producer, video_path, camera_id),
            daemon=True
        )
        t.start()
        threads.append(t)
        time.sleep(0.5)  # Small delay between thread starts
    
    # Wait for all threads to complete
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("\n🛑 Stopping all streams...")
    
    # Cleanup
    producer.flush()
    producer.close()
    print("\n✓ All videos completed")

if __name__ == "__main__":
    main()

