import os
import time
import cv2
import numpy as np
import sys

# Try to import ultralytics
try:
    from ultralytics import YOLO
except ImportError:
    print("Error: 'ultralytics' module not found. Please install it using: pip install ultralytics")
    sys.exit(1)

# =========================
# CONFIG
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "models")
OUTPUT_DIR = os.path.join(BASE_DIR, "violations")
DATA_DIR = os.path.join(BASE_DIR, "data")

VIDEO_PATH = os.path.join(DATA_DIR, "video/bike-test.mp4")

# Helmet YOLOv3
HELMET_CFG = os.path.join(MODELS_DIR, "yolov3-helmet.cfg")
HELMET_WEIGHTS = os.path.join(MODELS_DIR, "yolov3-helmet.weights")
HELMET_NAMES = os.path.join(MODELS_DIR, "helmet.names")

# YOLOv8 (replaces YOLOv3 COCO)
YOLOV8_WEIGHTS = os.path.join(MODELS_DIR, "yolov8n.pt")

CONF_THRES = 0.5
NMS_THRES = 0.4
INPUT_SIZE = 416

# YOLOv8 Class IDs
COCO_PERSON_ID = 0
COCO_MOTORBIKE_ID = 3

# rider association
IOU_PERSON_BIKE_THRES = 0.02  
BOTTOM_CENTER_IN_BIKE = True

# helmet check
HEAD_RATIO = 0.35               # 35% of person height from top
HELMET_HEAD_IOU_THRES = 0.02    

# tracking & anti-spam saving
TRACK_MAX_DIST = 80            
TRACK_TTL_SEC = 1.0            
SAVE_COOLDOWN_SEC = 2.0        
SAVE_ANNOTATED = True          


# =========================
# UTILS
# =========================
def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def get_output_layer_names(net):
    names = net.getLayerNames()
    return [names[i - 1] for i in net.getUnconnectedOutLayers().flatten()]

def detect_yolov3(net, output_layers, image, conf_thres=0.5, nms_thres=0.4, inp_size=416):
    """
    Returns: boxes [x, y, w, h], class_ids, confs
    """
    (H, W) = image.shape[:2]
    blob = cv2.dnn.blobFromImage(image, 1/255.0, (inp_size, inp_size), swapRB=True, crop=False)
    net.setInput(blob)
    outs = net.forward(output_layers)

    boxes, class_ids, confs = [], [], []
    for out in outs:
        for det in out:
            scores = det[5:]
            cid = int(np.argmax(scores))
            conf = float(scores[cid])
            if conf < conf_thres:
                continue
            cx = int(det[0] * W)
            cy = int(det[1] * H)
            w = int(det[2] * W)
            h = int(det[3] * H)
            x = int(cx - w / 2)
            y = int(cy - h / 2)
            boxes.append([x, y, w, h])
            class_ids.append(cid)
            confs.append(conf)

    idxs = cv2.dnn.NMSBoxes(boxes, confs, conf_thres, nms_thres)
    if len(idxs) == 0:
        return [], [], []
    idxs = idxs.flatten().tolist()
    return [boxes[i] for i in idxs], [class_ids[i] for i in idxs], [confs[i] for i in idxs]

def clamp_box(box, W, H):
    x, y, w, h = box
    x = max(0, x); y = max(0, y)
    w = max(0, min(w, W - x))
    h = max(0, min(h, H - y))
    return [x, y, w, h]

def box_xyxy(box):
    x, y, w, h = box
    return (x, y, x + w, y + h)

def iou(a, b):
    ax1, ay1, ax2, ay2 = box_xyxy(a)
    bx1, by1, bx2, by2 = box_xyxy(b)
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    iw = max(0, inter_x2 - inter_x1)
    ih = max(0, inter_y2 - inter_y1)
    inter = iw * ih
    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
    denom = area_a + area_b - inter + 1e-9
    return inter / denom

def bottom_center(box):
    x, y, w, h = box
    return (x + w / 2.0, y + h * 1.0)

def point_in_box(px, py, box):
    x, y, w, h = box
    return (px >= x) and (px <= x + w) and (py >= y) and (py <= y + h)

def head_region(person_box, head_ratio=0.35):
    x, y, w, h = person_box
    hh = int(h * head_ratio)
    return [x, y, w, max(1, hh)]

def centroid(box):
    x, y, w, h = box
    return (x + w / 2.0, y + h / 2.0)

def draw_box(img, box, label, color=(0, 255, 0)):
    x, y, w, h = box
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(img.shape[1] - 1, x + w), min(img.shape[0] - 1, y + h)
    cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
    cv2.putText(img, label, (x1, max(0, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)

# =========================
# SIMPLE TRACKER (Centroid)
# =========================
class CentroidTracker:
    def __init__(self, max_dist=80, ttl_sec=1.0):
        self.max_dist = max_dist
        self.ttl_sec = ttl_sec
        self.next_id = 1
        self.tracks = {}  # id -> {"c":(x,y), "t":last_seen, "box":box}

    def update(self, boxes, now_ts):
        # remove old
        to_del = [tid for tid, tr in self.tracks.items() if (now_ts - tr["t"]) > self.ttl_sec]
        for tid in to_del:
            del self.tracks[tid]

        assigned = {}
        used_tracks = set()

        # greedy assign by nearest centroid
        for box in boxes:
            cx, cy = centroid(box)
            best_id = None
            best_d = 1e18
            for tid, tr in self.tracks.items():
                if tid in used_tracks:
                    continue
                tx, ty = tr["c"]
                d = (cx - tx) ** 2 + (cy - ty) ** 2
                if d < best_d:
                    best_d = d
                    best_id = tid
            if best_id is not None and np.sqrt(best_d) <= self.max_dist:
                self.tracks[best_id] = {"c": (cx, cy), "t": now_ts, "box": box}
                assigned[best_id] = box
                used_tracks.add(best_id)
            else:
                tid = self.next_id
                self.next_id += 1
                self.tracks[tid] = {"c": (cx, cy), "t": now_ts, "box": box}
                assigned[tid] = box
                used_tracks.add(tid)

        return assigned  # id -> box


# =========================
# MAIN
# =========================
def main():
    ensure_dir(OUTPUT_DIR)
    
    # 1. Load YOLOv3 Helmet
    print("[INFO] Loading YOLOv3 (Helmet)...")
    if not os.path.exists(HELMET_CFG) or not os.path.exists(HELMET_WEIGHTS):
        print(f"Error: Helmet model files missing: {HELMET_CFG} or {HELMET_WEIGHTS}")
        return

    helmet_net = cv2.dnn.readNetFromDarknet(HELMET_CFG, HELMET_WEIGHTS)
    helmet_net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
    helmet_net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
    helmet_out = get_output_layer_names(helmet_net)

    # 2. Load YOLOv8 for Person/Bike
    print(f"[INFO] Loading YOLOv8 from {YOLOV8_WEIGHTS}...")
    try:
        yolo8_model = YOLO(YOLOV8_WEIGHTS)
    except Exception as e:
        print(f"Error loading YOLOv8: {e}")
        return

    # 3. Open Video
    print(f"[INFO] Opening video {VIDEO_PATH}...")
    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {VIDEO_PATH}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 10.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    print(f"[INFO] FPS={fps:.2f}, total_frames={total}")

    tracker = CentroidTracker(max_dist=TRACK_MAX_DIST, ttl_sec=TRACK_TTL_SEC)
    last_saved = {}  # track_id -> ts
    frame_idx = 0
    saved = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame_idx += 1
        H, W = frame.shape[:2]
        now_ts = time.time()
        video_ts = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0

        # --- A. Detect Helmet (YOLOv3) ---
        helmet_boxes, _, _ = detect_yolov3(helmet_net, helmet_out, frame, CONF_THRES, NMS_THRES, INPUT_SIZE)
        helmet_boxes = [clamp_box(b, W, H) for b in helmet_boxes]

        # --- B. Detect Person + Motorbike (YOLOv8) ---
        results = yolo8_model.predict(frame, classes=[COCO_PERSON_ID, COCO_MOTORBIKE_ID], conf=CONF_THRES, verbose=False)
        
        persons = []
        bikes = []
        
        for r in results:
            boxes = r.boxes
            for i, box_data in enumerate(boxes):
                # box.xyxy format
                x1, y1, x2, y2 = box_data.xyxy[0].cpu().numpy()
                cls_id = int(box_data.cls[0].item())
                
                # Convert to [x, y, w, h]
                w = x2 - x1
                h = y2 - y1
                b = [int(x1), int(y1), int(w), int(h)]
                b = clamp_box(b, W, H)
                
                if cls_id == COCO_PERSON_ID:
                    persons.append(b)
                elif cls_id == COCO_MOTORBIKE_ID:
                    bikes.append(b)

        if len(persons) == 0 or len(bikes) == 0:
            continue

        # --- C. Associate Person -> Bike (Rider) ---
        riders = []  # list of (person_box, bike_box)
        for p in persons:
            pcx, pcy = bottom_center(p)
            matched = None
            best = 0.0
            for b in bikes:
                # Logic: Either bottom-center of person is INSIDE bike box
                # OR significant overlap (IoU)
                ok_in = (not BOTTOM_CENTER_IN_BIKE) or point_in_box(pcx, pcy, b)
                ov = iou(p, b)
                
                if ok_in or ov >= IOU_PERSON_BIKE_THRES:
                    # Score based on overlap
                    score = ov + (0.1 if ok_in else 0.0)
                    if score > best:
                        best = score
                        matched = b
            
            if matched is not None:
                riders.append((p, matched))

        if len(riders) == 0:
            continue

        # --- D. Track Riders ---
        # We track based on the Person box of the rider
        rider_person_boxes = [rp[0] for rp in riders]
        id_to_person = tracker.update(rider_person_boxes, now_ts)  # id -> person_box

        # --- E. Violation Check (No Helmet on Head) ---
        violations = []  # list of (track_id, person_box)
        
        for tid, pbox in id_to_person.items():
            # Define head region (upper 35%)
            hbox = head_region(pbox, HEAD_RATIO)
            
            has_helmet = False
            for hb in helmet_boxes:
                # Check intersection between helmet box and head region
                if iou(hb, hbox) >= HELMET_HEAD_IOU_THRES:
                    has_helmet = True
                    break
            
            if not has_helmet:
                violations.append((tid, pbox))

        if len(violations) == 0:
            continue

        # --- F. Output ---
        out = frame.copy()
        
        # Draw all helmets (Green)
        for hb in helmet_boxes:
            draw_box(out, hb, "Helmet", color=(0, 255, 0))
            
        # Draw tracked riders (Yellow defaults)
        for tid, pbox in id_to_person.items():
             draw_box(out, pbox, f"Rider {tid}", color=(0, 255, 255))

        # Handle Violations
        for tid, pbox in violations:
            # spam check
            last = last_saved.get(tid, 0)
            if (now_ts - last) < SAVE_COOLDOWN_SEC:
                continue

            last_saved[tid] = now_ts

            # Red box for violation
            draw_box(out, pbox, f"NO HELMET {tid}", color=(0, 0, 255))
            
            # Draw head region (debug)
            hreg = head_region(pbox, HEAD_RATIO)
            draw_box(out, hreg, "Head", color=(0, 0, 150))

            print(f"[VIOLATION] Frame {frame_idx} (t={video_ts:.2f}s) TrackID={tid}")

            filename = os.path.join(OUTPUT_DIR, f"violation_t{video_ts:07.2f}_f{frame_idx:06d}_id{tid}.jpg")
            if SAVE_ANNOTATED:
                cv2.imwrite(filename, out)
            else:
                cv2.imwrite(filename, frame)
                
            saved += 1

    cap.release()
    print(f"[DONE] Saved {saved} violation images to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
