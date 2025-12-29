# Báo Cáo Hệ Thống Phát Hiện Vi Phạm Giao Thông Thời Gian Thực

## 1. Tổng Quan Hệ Thống

Hệ thống sử dụng **YOLOv8** kết hợp với **Apache Kafka** để phát hiện vi phạm giao thông real-time từ camera giám sát.

### Các Loại Vi Phạm Được Phát Hiện

| Vi phạm               | Model               | Logic                              |
| --------------------- | ------------------- | ---------------------------------- |
| Không đội mũ bảo hiểm | best.pt (8 classes) | Person + Motorcycle + No Helmet    |
| Vượt đèn đỏ           | yolov8n.pt          | Vehicle crosses stop line when RED |
| Lấn làn               | yolov8n.pt          | Vehicle crosses solid lane line    |

---

## 2. Kiến Trúc Pipeline

```mermaid
flowchart LR
    subgraph Input
        V[Video/Camera]
    end

    subgraph Ingestion
        P[Kafka Producer]
        K[(Kafka Topic)]
    end

    subgraph Detection
        H[Helmet Detector]
        R[RedLight Detector]
        L[Lane Detector]
    end

    subgraph Output
        DB[(PostgreSQL)]
        WS[WebSocket]
        FE[Dashboard]
    end

    V --> P --> K
    K --> H & R & L
    H & R & L --> DB --> WS --> FE
```

---

## 3. Luồng Phát Hiện Vi Phạm Mũ Bảo Hiểm

**Model**: `best.pt` - Unified model với 8 classes

```mermaid
flowchart TD
    A[Frame Input] --> B[YOLO Inference]
    B --> C{Detect Objects}

    C --> D[Person boxes]
    C --> E[Motorcycle boxes]
    C --> F[with_helmet boxes]
    C --> G[without_helmet boxes]

    D & E --> H[Associate Person ↔ Motorcycle]
    H --> I{Person on Motorcycle?}

    I -->|Yes| J[Extract Head Region<br>Top 35% of person box]
    J --> K{Check Head Region}

    K --> L[Match with_helmet?]
    K --> M[Match without_helmet?]

    L -->|Yes| N[✓ Has Helmet]
    M -->|Yes| O[⚠️ VIOLATION]

    L & M -->|No match| P[Check IoU with helmet boxes]
    P --> Q{IoU > threshold?}
    Q -->|No| O
    Q -->|Yes| N
```

### Logic Chính

```python
# Pseudo-code
if person.on_motorcycle:
    head_region = person.box.top_35_percent()
    if head_region.overlaps(without_helmet_box):
        return VIOLATION
    if not head_region.overlaps(with_helmet_box):
        return VIOLATION
```

---

## 4. Luồng Phát Hiện Vượt Đèn Đỏ

**Model**: `yolov8n.pt` - COCO pretrained

```mermaid
flowchart TD
    A[Frame Input] --> B[Detect Traffic Light State]
    A --> C[Detect Vehicles]

    B --> D{Light State}
    D -->|GREEN/YELLOW| E[No Violation Check]
    D -->|RED| F[Check Vehicles]

    C --> G[Track with CentroidTracker]
    G --> H[Get Vehicle Position]

    F --> H
    H --> I{Bottom Center vs Stop Line}

    I -->|Previously Above, Now Below| J[⚠️ VIOLATION]
    I -->|No Crossing| K[Continue Tracking]

    subgraph Traffic Light Detection
        B --> B1[YOLO detect traffic_light]
        B1 --> B2[Crop ROI]
        B2 --> B3[HSV Color Analysis]
        B3 --> B4[Count Red/Green/Yellow pixels]
        B4 --> D
    end
```

### Cấu Hình ROI

```json
{
  "stop_line": { "y": 646, "violation_direction": "above" },
  "traffic_light_roi": { "x1": 28, "y1": 9, "x2": 184, "y2": 190 },
  "detection_zone": [
    [640, 406],
    [1167, 410],
    [1899, 1014],
    [52, 1018]
  ]
}
```

---

## 5. Luồng Phát Hiện Lấn Làn

**Model**: `yolov8n.pt` + Image Processing

```mermaid
flowchart TD
    A[Frame Input] --> B[Detect Vehicles]
    B --> C[Track with CentroidTracker]

    C --> D[Get Vehicle Bottom Center]
    D --> E[Check Against Lane Lines]

    E --> F{For Each Solid Line}
    F --> G[Calculate Side of Line]
    G --> H{Side Changed?}

    H -->|No| I[Update Position]
    H -->|Yes| J{Line Type?}

    J -->|Solid| K[⚠️ VIOLATION]
    J -->|Dashed| L[Allowed - Update]

    subgraph "Side Calculation"
        G --> G1["d = (x2-x1)(py-y1) - (y2-y1)(px-x1)"]
        G1 --> G2["side = sign(d)"]
    end
```

### Công Thức Tính Khoảng Cách Điểm-Đường

$$d = \frac{|(x_2-x_1)(y_1-y_p) - (x_1-x_p)(y_2-y_1)|}{\sqrt{(x_2-x_1)^2 + (y_2-y_1)^2}}$$

---

## 6. Object Tracking: CentroidTracker

```mermaid
flowchart LR
    subgraph "Frame N"
        D1[Detection 1]
        D2[Detection 2]
    end

    subgraph "Tracked Objects"
        T1[Track ID=1<br>History]
        T2[Track ID=2<br>History]
    end

    subgraph "Frame N+1"
        D3[Detection A]
        D4[Detection B]
    end

    D1 --> T1
    D2 --> T2

    T1 -.->|Euclidean Distance| D3
    T2 -.->|Euclidean Distance| D4

    D3 -->|"dist < max_dist"| T1
    D4 -->|"dist < max_dist"| T2
```

**Thuật toán**: Hungarian Assignment với Euclidean Distance

---

## 7. Tech Stack

| Layer         | Technology           |
| ------------- | -------------------- |
| AI Model      | YOLOv8 (Ultralytics) |
| Message Queue | Apache Kafka         |
| Orchestration | Apache Airflow       |
| Database      | PostgreSQL           |
| Backend       | FastAPI + WebSocket  |
| Frontend      | Next.js              |

---

## 8. Hiệu Suất

| Metric             | Value         |
| ------------------ | ------------- |
| Inference Speed    | ~30 FPS (CPU) |
| End-to-End Latency | < 500ms       |
| Detection Accuracy | ~85% mAP@0.5  |

---

## 9. Hạn Chế & Hướng Phát Triển

- **Hiện tại**: Phụ thuộc vào góc camera cố định, cần cấu hình ROI thủ công
- **Tương lai**:
  - OCR nhận dạng biển số
  - Ước lượng tốc độ
  - GPU acceleration với TensorRT
