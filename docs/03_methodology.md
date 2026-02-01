# 3. PHƯƠNG PHÁP ĐỀ XUẤT (METHODOLOGY)

## 3.1 Kiến Trúc Hệ Thống Tổng Quan

Hệ thống được thiết kế theo kiến trúc **microservices** với các thành phần tách biệt, giao tiếp qua message queue. Kiến trúc này cho phép:

- **Horizontal scaling**: Thêm consumer instances khi cần
- **Fault tolerance**: Một service lỗi không ảnh hưởng toàn hệ thống
- **Flexibility**: Dễ dàng thêm loại vi phạm mới

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                                │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │ Camera API   │    │ Video Files  │    │ RTSP Stream  │          │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘          │
└─────────┼───────────────────┼───────────────────┼──────────────────┘
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      VIDEO PRODUCER                                 │
│  • Frame extraction at 15 FPS                                       │
│  • Base64 encoding                                                  │
│  • Kafka message production                                         │
└─────────────────────────────────────┬───────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    KAFKA MESSAGE BROKER                             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              helmet_video_frames (topic)                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────┬───────────────────────────────┘
          ┌───────────────────────────┼───────────────────────────┐
          ▼                           ▼                           ▼
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│ Helmet Consumer  │      │RedLight Consumer │      │  Lane Consumer   │
│ • best.pt model  │      │ • yolov8n.pt     │      │ • yolov8n.pt     │
│ • 8 classes      │      │ • HSV analysis   │      │ • Line geometry  │
└────────┬─────────┘      └────────┬─────────┘      └────────┬─────────┘
         │                         │                         │
         ▼                         ▼                         ▼
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│helmet_violations │      │redlight_violations│     │ lane_violations  │
└────────┬─────────┘      └────────┬─────────┘      └────────┬─────────┘
         └─────────────────────────┼─────────────────────────┘
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FASTAPI BACKEND                                │
│  • Consume violations from Kafka                                    │
│  • Save to PostgreSQL                                               │
│  • WebSocket broadcast to frontend                                  │
│  • REST API for queries                                             │
└─────────────────────────────────────┬───────────────────────────────┘
                                      │
                       ┌──────────────┴──────────────┐
                       ▼                              ▼
              ┌──────────────────┐          ┌──────────────────┐
              │   PostgreSQL     │          │  Next.js Frontend │
              │   Database       │          │  Dashboard        │
              └──────────────────┘          └──────────────────┘
```

## 3.2 Data Pipeline

### 3.2.1 Video Producer

Video Producer có nhiệm vụ đọc video từ các nguồn và gửi frames vào Kafka:

```python
# Cấu hình Producer
KAFKA_TOPIC = 'helmet_video_frames'
TARGET_FPS = 15
MAX_RESOLUTION = 720  # Resize nếu > 720p

# Message format
message = {
    "camera_id": "cam1",
    "frame_number": 1234,
    "timestamp": "2025-01-14T15:30:00Z",
    "image_base64": "<base64_encoded_jpeg>",
    "width": 1280,
    "height": 720
}
```

### 3.2.2 Kafka Configuration

| Tham số              | Giá trị  | Mục đích              |
| -------------------- | -------- | --------------------- |
| `num.partitions`     | 3        | Parallel processing   |
| `replication.factor` | 1        | Development setup     |
| `max.message.bytes`  | 10MB     | Large frame support   |
| `retention.ms`       | 86400000 | 24h replay capability |

## 3.3 Detection Modules

### 3.3.1 Base Utilities

Module `base.py` cung cấp các hàm tiện ích dùng chung:

**Box Utilities:**

- `clamp_box(box, W, H)`: Giới hạn box trong kích thước frame
- `box_xyxy(box)`: Chuyển đổi [x,y,w,h] sang (x1,y1,x2,y2)
- `centroid(box)`: Tính tâm điểm của box
- `bottom_center(box)`: Tính điểm giữa đáy (cho stop line crossing)
- `iou(a, b)`: Tính Intersection over Union

**Geometric Utilities:**

- `point_in_polygon(point, polygon)`: Ray casting algorithm
- `head_region(person_box, ratio)`: Trích xuất vùng đầu từ person box

### 3.3.2 CentroidTracker

Thuật toán tracking nhẹ, phù hợp cho real-time:

```python
class CentroidTracker:
    def __init__(self, max_dist=100, ttl_sec=2.0):
        """
        Args:
            max_dist: Khoảng cách tối đa (pixels) để match track
            ttl_sec: Thời gian sống của track khi không detect được
        """
        self.tracks = {}  # track_id -> track_info
        self.next_id = 1
```

**Thuật toán matching:**

1. Loại bỏ tracks đã quá TTL (2 giây không detect)
2. Với mỗi detection mới, tính Euclidean distance đến tất cả existing tracks
3. Match với track gần nhất nếu distance < max_dist (100px)
4. Nếu không match được, tạo track mới với ID tăng dần

**Công thức khoảng cách:**
$$d = \sqrt{(x_2 - x_1)^2 + (y_2 - y_1)^2}$$

## 3.4 ROI Configuration System

Hệ thống cho phép cấu hình ROI riêng cho từng camera:

```json
{
  "cam1": {
    "frame_width": 1920,
    "frame_height": 1080,
    "stop_line": {
      "y": 646,
      "tolerance": 30,
      "violation_direction": "above"
    },
    "traffic_light_roi": {
      "x1": 28,
      "y1": 9,
      "x2": 184,
      "y2": 190
    },
    "detection_zone": [
      [640, 406],
      [1167, 410],
      [1899, 1014],
      [52, 1018]
    ],
    "lane_lines": [
      { "x1": 640, "y1": 406, "x2": 52, "y2": 1018, "type": "solid" },
      { "x1": 900, "y1": 408, "x2": 950, "y2": 1016, "type": "dashed" }
    ]
  }
}
```

**Tính năng quan trọng:** Hàm `scale_config()` tự động scale tọa độ theo resolution thực tế của frame:

$$x_{scaled} = x_{config} \times \frac{W_{actual}}{W_{config}}$$
$$y_{scaled} = y_{config} \times \frac{H_{actual}}{H_{config}}$$
