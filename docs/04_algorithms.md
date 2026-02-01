# 4. THUẬT TOÁN PHÁT HIỆN VI PHẠM (DETECTION ALGORITHMS)

## 4.1 Phát Hiện Không Đội Mũ Bảo Hiểm

### 4.1.1 Unified Model Architecture

Sử dụng model `best.pt` được huấn luyện với 8 classes:

| Class ID | Tên lớp        | Mô tả               |
| -------- | -------------- | ------------------- |
| 0        | person         | Người đi bộ/ngồi xe |
| 1        | bicycle        | Xe đạp              |
| 2        | car            | Ô tô                |
| 3        | motorcycle     | Xe máy              |
| 4        | bus            | Xe buýt             |
| 5        | truck          | Xe tải              |
| 6        | with_helmet    | Người đội mũ        |
| 7        | without_helmet | Người không đội mũ  |

### 4.1.2 Detection Strategy

**Strategy 1 - Direct Detection** (ưu tiên):

1. Phát hiện boxes `without_helmet` trực tiếp từ model
2. Với mỗi `without_helmet` box, tìm person box chứa nó
3. Kiểm tra person đó có đang trên xe không (IoU check)
4. Nếu tất cả điều kiện thỏa → **VI PHẠM**

**Strategy 2 - Fallback** (khi Strategy 1 không phát hiện):

1. Liên kết riders với vehicles (associate_riders)
2. Với mỗi rider, kiểm tra vùng đầu có `with_helmet` không
3. Nếu không có `with_helmet` → **VI PHẠM**

### 4.1.3 Associate Riders Algorithm

```python
def associate_riders(persons, vehicles):
    """
    Điều kiện liên kết person với vehicle:
    - Bottom center của person nằm trong vehicle box
    - HOẶC IoU(person, vehicle) >= 0.15
    Mỗi xe tối đa 3 riders.
    """
    pairs = []
    for person in persons:
        bottom_pt = bottom_center(person.box)
        for vehicle in vehicles:
            if point_in_box(bottom_pt, vehicle.box):
                pairs.append((person, vehicle))
            elif iou(person.box, vehicle.box) >= 0.15:
                pairs.append((person, vehicle))
    return pairs
```

### 4.1.4 Head Region Check

```python
def is_head_inside_person(head_box, person_box, head_region_ratio=0.5):
    """
    Xác định head_box có trong vùng đầu của person không:
    - Head center X phải trong person width
    - Head center Y phải trong 50% phần trên của person
    """
    head_cx = head_box[0] + head_box[2] / 2
    head_cy = head_box[1] + head_box[3] / 2

    px, py, pw, ph = person_box
    head_region_height = ph * head_region_ratio

    in_x = px <= head_cx <= px + pw
    in_y = py <= head_cy <= py + head_region_height

    return in_x and in_y
```

### 4.1.5 Confidence Calculation

Độ tin cậy của vi phạm được tính theo công thức có trọng số:

$$C_{violation} = 0.25 \times C_{person} + 0.25 \times C_{vehicle} + 0.50 \times C_{no\_helmet} + bonus$$

Trong đó:

- $C_{person}$: Confidence của person detection
- $C_{vehicle}$: Confidence của vehicle detection
- $C_{no\_helmet}$: Factor từ head detection (0.8 nếu có `without_helmet`, 0.5 nếu không có `with_helmet`)
- $bonus = 0.1$ nếu person đang trên xe

### 4.1.6 Violation Deduplicator

Vấn đề: Khi track ID thay đổi (do occlusion), cùng một người có thể bị đếm nhiều lần.

Giải pháp:

```python
class ViolationDeduplicator:
    def __init__(self, time_threshold=3.0, distance_threshold=50):
        """
        time_threshold: Cooldown 3 giây giữa các vi phạm
        distance_threshold: 50 pixels để xác định cùng vị trí
        """

    def is_duplicate(self, track_id, person_box, current_time):
        """
        Check duplicate bằng 2 tiêu chí:
        1. Cùng track_id trong thời gian cooldown
        2. Khác track_id nhưng khoảng cách centroid < 50px
        """
```

## 4.2 Phát Hiện Vượt Đèn Đỏ

### 4.2.1 Traffic Light Detection

**Bước 1 - YOLO Detection** (thử trước):

- Sử dụng `yolov8n.pt` để detect traffic light object
- Nếu tìm thấy, crop vùng đèn

**Bước 2 - ROI Fallback** (nếu YOLO không tìm thấy):

- Sử dụng `traffic_light_roi` từ config
- Crop vùng đèn theo tọa độ cố định

### 4.2.2 HSV Color Analysis

Xác định màu đèn bằng phân tích HSV với dual-range cho màu đỏ:

```python
COLOR_CONFIG = {
    "red_lower1": [0, 100, 100],    # Đỏ spectrum thấp (H: 0-10)
    "red_upper1": [10, 255, 255],
    "red_lower2": [160, 100, 100],  # Đỏ spectrum cao (H: 160-180)
    "red_upper2": [180, 255, 255],
    "green_lower": [40, 100, 100],  # Xanh (H: 40-80)
    "green_upper": [80, 255, 255],
    "yellow_lower": [20, 100, 100], # Vàng (H: 20-35)
    "yellow_upper": [35, 255, 255]
}

def analyze_color(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    red_mask1 = cv2.inRange(hsv, red_lower1, red_upper1)
    red_mask2 = cv2.inRange(hsv, red_lower2, red_upper2)
    red_count = cv2.countNonZero(red_mask1 | red_mask2)

    green_mask = cv2.inRange(hsv, green_lower, green_upper)
    green_count = cv2.countNonZero(green_mask)

    # Return color with max count > threshold (50 pixels)
    if red_count > 50 and red_count > green_count:
        return "RED"
    elif green_count > 50:
        return "GREEN"
    return "UNKNOWN"
```

### 4.2.3 Violation Logic

```python
def check_violation(track_info, light_state, config):
    if light_state != "RED":
        return False

    # Lấy điểm đáy xe
    _, vehicle_y = bottom_center(track_info["box"])
    stop_line_y = config["stop_line"]["y"]
    direction = config["stop_line"]["violation_direction"]

    # Check theo hướng vi phạm
    if direction == "above":
        crossed_now = vehicle_y < stop_line_y  # Xe vượt lên trên
    else:
        crossed_now = vehicle_y > stop_line_y  # Xe vượt xuống dưới

    # Vi phạm = vừa vượt line (chưa vượt trước đó)
    if crossed_now and not track_info.get("crossed", False):
        track_info["crossed"] = True
        return True

    return False
```

## 4.3 Phát Hiện Lấn Làn

### 4.3.1 Lane Line Representation

```python
class LaneLine:
    def __init__(self, config, line_id):
        self.id = line_id
        self.x1, self.y1 = config["x1"], config["y1"]
        self.x2, self.y2 = config["x2"], config["y2"]
        self.type = config.get("type", "solid")  # solid/dashed

    def get_side(self, px, py):
        """Xác định điểm nằm bên nào của đường"""
        d = (self.x2 - self.x1) * (py - self.y1) - \
            (self.y2 - self.y1) * (px - self.x1)
        return 1 if d > 0 else (-1 if d < 0 else 0)
```

### 4.3.2 Point-to-Line Side Formula

Công thức xác định vị trí tương đối của điểm P(px, py) với đường thẳng qua A(x1, y1) và B(x2, y2):

$$d = (x_2 - x_1)(p_y - y_1) - (y_2 - y_1)(p_x - x_1)$$

- $d > 0$: Điểm nằm bên phải đường
- $d < 0$: Điểm nằm bên trái đường
- $d = 0$: Điểm nằm trên đường

### 4.3.3 Violation Detection

```python
def check_lane_violation(track_id, track_info, lane_lines):
    px, py = bottom_center(track_info["box"])

    for line in lane_lines:
        if line.type != "solid":
            continue  # Chỉ check solid line

        current_side = line.get_side(px, py)
        previous_side = get_previous_side(track_id, line.id)

        # Vi phạm khi thay đổi bên (không qua 0)
        if previous_side != 0 and current_side != 0:
            if previous_side != current_side:
                return {
                    "line_id": line.id,
                    "from_side": "left" if previous_side < 0 else "right",
                    "to_side": "left" if current_side < 0 else "right"
                }

    return None
```
