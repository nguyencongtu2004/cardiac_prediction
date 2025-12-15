from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, udf, struct, to_json
from pyspark.sql.types import StructType, StructField, StringType, ArrayType, FloatType, IntegerType
import json
import os
import sys

# Ensure local modules can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    import traffic_logic
except ImportError:
    pass

# ==========================
# CẤU HÌNH
# ==========================
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
INPUT_TOPIC = 'camera_raw_frames'
OUTPUT_TOPIC = 'traffic_violations'
CHECKPOINT_DIR = '/tmp/spark_checkpoint'

# ROI Configuration
ROI_CONFIG_PATH = os.getenv('ROI_CONFIG_PATH', './roi.json')

# ==========================
# KHỞI TẠO SPARK SESSION
# ==========================
def create_spark_session():
    """Tạo Spark Session với Kafka package"""
    spark = SparkSession.builder \
        .appName("TrafficViolationMonitoring") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
        .config("spark.sql.streaming.checkpointLocation", CHECKPOINT_DIR) \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    return spark

# ==========================
# SCHEMA ĐỊNH NGHĨA
# ==========================
# Schema cho message từ Kafka
input_schema = StructType([
    StructField("camera_id", StringType(), True),
    StructField("timestamp", StringType(), True),
    StructField("image_path", StringType(), True),
    StructField("filename", StringType(), True)
])

# Schema cho detection result
detection_schema = ArrayType(StructType([
    StructField("class_id", IntegerType(), True),
    StructField("class_name", StringType(), True),
    StructField("confidence", FloatType(), True),
    StructField("bbox", ArrayType(FloatType()), True),  # [x1, y1, x2, y2]
    StructField("center", ArrayType(FloatType()), True),  # [cx, cy]
    StructField("state", StringType(), True) # ADDED: Traffic Light State (RED/GREEN/etc)
]))

# ==========================
# YOLO INFERENCE UDF
# ==========================
def create_yolo_detector():
    """Factory function để tạo YOLO detector (lazy loading)"""
    from ultralytics import YOLO
    import cv2
    import numpy as np
    
    # Import logic locally if needed (for worker nodes)
    try:
        import traffic_logic
    except ImportError:
        pass # Handle if not found or packaged differently

    model = YOLO('yolov8n.pt')
    target_classes = [2, 3, 5, 7, 9]  # car, motorcycle, bus, truck, traffic light
    
    def detect_objects(image_path):
        """Detect objects trong ảnh"""
        try:
            if not os.path.exists(image_path):
                return []
            
            frame = cv2.imread(image_path)
            if frame is None:
                return []
            
            results = model(frame, verbose=False)
            detections = []
            
            for box in results[0].boxes:
                cls_id = int(box.cls[0])
                if cls_id in target_classes:
                    x1, y1, x2, y2 = map(float, box.xyxy[0])
                    conf = float(box.conf[0])
                    cx = (x1 + x2) / 2
                    cy = (y1 + y2) / 2
                    
                    class_name = model.names[cls_id]
                    state = "UNKNOWN"

                    # Nếu là đèn giao thông, detect màu
                    if class_name == 'traffic light':
                        # Crop image
                        h, w = frame.shape[:2]
                        cx1, cy1, cx2, cy2 = int(x1), int(y1), int(x2), int(y2)
                        cx1, cx2 = max(0, cx1), min(w, cx2)
                        cy1, cy2 = max(0, cy1), min(h, cy2)
                        
                        crop = frame[cy1:cy2, cx1:cx2]
                        if 'traffic_logic' in locals() or 'traffic_logic' in globals():
                             state = traffic_logic.detect_traffic_light_color(crop)
                        else:
                             # Fallback internal logic if import fails on worker
                             # For now, duplicate logic or assume 'UNKNOWN'
                             # Ideally traffic_logic.py is distributed with --py-files
                             pass 

                    detections.append({
                        "class_id": cls_id,
                        "class_name": class_name,
                        "confidence": conf,
                        "bbox": [x1, y1, x2, y2],
                        "center": [cx, cy],
                        "state": state
                    })
            
            return detections
        except Exception as e:
            print(f"Error detecting objects: {e}")
            return []
    
    return detect_objects

# Tạo UDF
detect_objects_udf = udf(create_yolo_detector(), detection_schema)

# ==========================
# VIOLATION DETECTION LOGIC
# ==========================
def load_roi_config():
    """Load ROI configuration"""
    try:
        with open(ROI_CONFIG_PATH, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

def check_violations(camera_id, detections_json):
    """Kiểm tra vi phạm dựa trên detections"""
    try:
        detections = json.loads(detections_json) if isinstance(detections_json, str) else detections_json
        roi_config = load_roi_config()
        cam_config = roi_config.get(camera_id, {})
        
        violations = []
        
        # Lấy stop line
        stop_line = cam_config.get("stop_line", [])
        if not stop_line or len(stop_line) < 2:
            return json.dumps([])
        
        # Stop line là đường thẳng từ (x1, y1) đến (x2, y2)
        # Giả sử stop line nằm ngang, y = stop_y
        stop_y = stop_line[0][1]
        
        # -- UPDATED LOGIC --
        # 1. Determine Global Traffic Light State
        # Ưu tiên lấy state từ detection đèn giao thông
        traffic_lights = [d for d in detections if d['class_name'] == 'traffic light']
        
        current_state = 'UNKNOWN'
        # Simple Logic: If ANY light is RED, consider it Red. If ANY Green, Green.
        # Priority: Red > Green > Yellow
        states = [d.get('state', 'UNKNOWN') for d in traffic_lights]
        if 'RED' in states:
            current_state = 'RED'
        elif 'GREEN' in states:
            current_state = 'GREEN'
        elif 'YELLOW' in states:
            current_state = 'YELLOW'
            
        # Nếu không phải RED, không bắt lỗi.
        if current_state != 'RED':
             return json.dumps([])

        vehicles = [d for d in detections if d['class_name'] in ['car', 'motorcycle', 'bus', 'truck']]
        
        # Simplified logic: Nếu có xe vượt qua stop line (center_y > stop_y)
        for vehicle in vehicles:
            cx, cy = vehicle['center'][0], vehicle['center'][1] # Array returned by UDF
            
            # Kiểm tra xe có vượt stop line không
            # Note: Cần cẩn thận logic vượt (center đã qua dòng)
            if cy > stop_y:
                violations.append({
                    "type": "stop_line_crossing",
                    "vehicle": vehicle['class_name'],
                    "confidence": vehicle['confidence'],
                    "position": vehicle['center'],
                    "traffic_light_state": current_state
                })
        
        return json.dumps(violations)
    
    except Exception as e:
        print(f"Error checking violations: {e}")
        return json.dumps([])

check_violations_udf = udf(check_violations, StringType())

# ==========================
# MAIN STREAMING PIPELINE
# ==========================
def main():
    print("🚀 Starting Traffic Violation Monitoring with Spark Streaming...")
    
    spark = create_spark_session()
    
    # Đọc stream từ Kafka
    df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", INPUT_TOPIC) \
        .option("startingOffsets", "latest") \
        .load()
    
    # Parse JSON từ Kafka
    parsed_df = df.select(
        from_json(col("value").cast("string"), input_schema).alias("data")
    ).select("data.*")
    
    # Apply YOLO detection
    detected_df = parsed_df.withColumn(
        "detections",
        detect_objects_udf(col("image_path"))
    )
    
    # Check violations
    violations_df = detected_df.withColumn(
        "violations",
        check_violations_udf(col("camera_id"), to_json(col("detections")))
    )
    
    # Filter chỉ lấy những frame có vi phạm
    violations_only = violations_df.filter(
        col("violations") != "[]"
    )
    
    # Prepare output
    output_df = violations_only.select(
        col("camera_id"),
        col("timestamp"),
        col("image_path"),
        col("violations")
    )
    
    # Write to Kafka
    query = output_df \
        .selectExpr("to_json(struct(*)) AS value") \
        .writeStream \
        .outputMode("append") \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("topic", OUTPUT_TOPIC) \
        .option("checkpointLocation", CHECKPOINT_DIR + "/kafka_prod") \
        .start()
    
    print("✓ Streaming started. Waiting for data...")
    print(f"  - Input Topic: {INPUT_TOPIC}")
    print(f"  - Kafka Servers: {KAFKA_BOOTSTRAP_SERVERS}")
    print("\nPress Ctrl+C to stop.\n")
    
    query.awaitTermination()

if __name__ == "__main__":
    main()
