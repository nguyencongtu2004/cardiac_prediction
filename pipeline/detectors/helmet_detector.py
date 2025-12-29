"""
helmet_detector.py - Helmet Violation Detection Logic
======================================================
Shared detection logic for helmet violations.
Used by both standalone scripts and Kafka consumers.

Uses UNIFIED model (best.pt) with 8 classes:
0: person, 1: bicycle, 2: car, 3: motorcycle,
4: bus, 5: truck, 6: with_helmet, 7: without_helmet
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional, Any

from .base import (
    centroid, bottom_center, clamp_box, iou, point_in_box, head_region, draw_box
)
from .tracker import CentroidTracker


# ============================================================
# UNIFIED MODEL CLASS MAPPING
# ============================================================
# Classes from unified model (best.pt)
CLASS_PERSON = 0
CLASS_BICYCLE = 1
CLASS_CAR = 2
CLASS_MOTORCYCLE = 3
CLASS_BUS = 4
CLASS_TRUCK = 5
CLASS_WITH_HELMET = 6
CLASS_WITHOUT_HELMET = 7  # Direct violation detection!

# Vehicle classes for rider detection
VEHICLE_CLASSES = [CLASS_BICYCLE, CLASS_MOTORCYCLE]

# Legacy COCO class IDs (for fallback)
COCO_PERSON_ID = 0
COCO_MOTORBIKE_ID = 3

# Detection thresholds
IOU_PERSON_BIKE_THRES = 0.15
BOTTOM_CENTER_IN_BIKE = True
HEAD_RATIO = 0.40
HELMET_HEAD_IOU_THRES = 0.15

# Dynamic confidence weights
CONFIDENCE_WEIGHT_PERSON = 0.25
CONFIDENCE_WEIGHT_VEHICLE = 0.25
CONFIDENCE_WEIGHT_NO_HELMET = 0.50


def get_output_layer_names(net):
    """Get output layer names for YOLOv3 network"""
    names = net.getLayerNames()
    return [names[i - 1] for i in net.getUnconnectedOutLayers().flatten()]


# ============================================================
# UNIFIED MODEL DETECTION (NEW - from helmet_detector_consumer.py)
# ============================================================

def detect_all_unified(model, frame: np.ndarray, conf_threshold: float = 0.25) -> Dict:
    """
    Detect all classes using the unified model (8 classes).
    
    Returns dict with all detections organized by class:
    {
        'persons': [(box, conf), ...],
        'vehicles': [(box, conf), ...],
        'with_helmet': [(box, conf), ...],
        'without_helmet': [(box, conf), ...],  # Direct violations!
    }
    """
    H, W = frame.shape[:2]
    
    results = model.predict(
        frame,
        conf=conf_threshold,
        verbose=False
    )
    
    detections = {
        'persons': [],
        'vehicles': [],
        'with_helmet': [],
        'without_helmet': [],
    }
    
    for result in results:
        for box_data in result.boxes:
            x1, y1, x2, y2 = box_data.xyxy[0].cpu().numpy()
            class_id = int(box_data.cls[0].item())
            conf = float(box_data.conf[0].item())
            
            box = [int(x1), int(y1), int(x2 - x1), int(y2 - y1)]
            box = clamp_box(box, W, H)
            
            if class_id == CLASS_PERSON:
                detections['persons'].append((box, conf))
            elif class_id in VEHICLE_CLASSES:
                detections['vehicles'].append((box, conf))
            elif class_id == CLASS_WITH_HELMET:
                detections['with_helmet'].append((box, conf))
            elif class_id == CLASS_WITHOUT_HELMET:
                detections['without_helmet'].append((box, conf))
    
    return detections


def is_head_inside_person(head_box: List[int], person_box: List[int], 
                          head_region_ratio: float = 0.5) -> bool:
    """
    Check if a head bounding box is inside the upper portion of a person box.
    """
    hx, hy, hw, hh = head_box
    px, py, pw, ph = person_box
    
    head_center_x = hx + hw / 2
    head_center_y = hy + hh / 2
    
    # Check horizontal overlap
    if not (px <= head_center_x <= px + pw):
        return False
    
    # Check if head is in upper portion of person
    head_region_bottom = py + ph * head_region_ratio
    if not (py <= head_center_y <= head_region_bottom):
        return False
    
    return True


def calculate_violation_confidence(person_conf: float, vehicle_conf: float, 
                                   no_helmet_factor: float) -> float:
    """
    Calculate dynamic confidence score for a violation.
    
    Returns: confidence score (0.1 - 0.99)
    """
    confidence = (
        person_conf * CONFIDENCE_WEIGHT_PERSON +
        vehicle_conf * CONFIDENCE_WEIGHT_VEHICLE +
        no_helmet_factor * CONFIDENCE_WEIGHT_NO_HELMET
    )
    return min(0.99, max(0.1, confidence))


def detect_violations_unified(model, frame: np.ndarray, tracker: CentroidTracker,
                              deduplicator, current_time: float,
                              conf_threshold: float = 0.25) -> Tuple[List, Dict]:
    """
    Detect violations using unified model.
    
    KEY INSIGHT: 'without_helmet' and 'with_helmet' boxes are HEAD REGIONS,
    not full person bounding boxes!
    
    Strategy:
    1. Find 'without_helmet' head boxes
    2. Match each head box to a 'person' box (head inside person's upper region)
    3. Check if that person is on a 'vehicle' (motorcycle/bicycle)
    4. If all match → VIOLATION
    
    Fallback: Find riders (person on vehicle) without 'with_helmet' near head
    
    Returns: (violations, all_detections)
    """
    detections = detect_all_unified(model, frame, conf_threshold)
    
    person_boxes_with_conf = detections['persons']
    vehicle_boxes_with_conf = detections['vehicles']
    helmet_boxes_with_conf = detections['with_helmet']
    no_helmet_boxes_with_conf = detections['without_helmet']
    
    person_boxes = [box for box, _ in person_boxes_with_conf]
    vehicle_boxes = [box for box, _ in vehicle_boxes_with_conf]
    helmet_boxes = [box for box, _ in helmet_boxes_with_conf]
    
    all_detections = {
        'person_boxes': person_boxes,
        'motorcycle_boxes': vehicle_boxes,
        'helmet_boxes': helmet_boxes,
        'no_helmet_boxes': [box for box, _ in no_helmet_boxes_with_conf],
        'riders_with_helmet': [],
        'riders_without_helmet': [],
    }
    
    violations = []
    processed_persons = set()  # Avoid double-counting
    
    # STRATEGY 1: Direct without_helmet HEAD detection
    for no_helmet_box, no_helmet_conf in no_helmet_boxes_with_conf:
        
        # Find the person that contains this head box
        matched_person = None
        matched_person_conf = 0.5
        for idx, (person_box, p_conf) in enumerate(person_boxes_with_conf):
            if idx in processed_persons:
                continue
            if is_head_inside_person(no_helmet_box, person_box):
                matched_person = person_box
                matched_person_conf = p_conf
                processed_persons.add(idx)
                break
        
        if matched_person is None:
            # No person found for this head → still a potential violation
            matched_person = no_helmet_box
            matched_person_conf = 0.6
        
        # Check if person is on a vehicle
        vehicle_conf = 0.3
        is_on_vehicle = False
        for vehicle_box, v_conf in vehicle_boxes_with_conf:
            if iou(matched_person, vehicle_box) >= IOU_PERSON_BIKE_THRES:
                vehicle_conf = v_conf
                is_on_vehicle = True
                break
            # Also check bottom-center
            bc_x, bc_y = bottom_center(matched_person)
            if point_in_box(bc_x, bc_y, vehicle_box):
                vehicle_conf = v_conf
                is_on_vehicle = True
                break
        
        # Calculate confidence
        confidence = calculate_violation_confidence(
            person_conf=matched_person_conf,
            vehicle_conf=vehicle_conf if is_on_vehicle else 0.3,
            no_helmet_factor=no_helmet_conf
        )
        
        # Boost confidence if on vehicle
        if is_on_vehicle:
            confidence = min(0.99, confidence + 0.1)
        
        # Deduplication check
        track_id = tracker.next_id
        if not deduplicator.is_duplicate(track_id, no_helmet_box, current_time):
            deduplicator.record(track_id, no_helmet_box, current_time)
            tracker.next_id += 1
            
            violations.append({
                'track_id': track_id,
                'box': matched_person if matched_person != no_helmet_box else no_helmet_box,
                'head_box': no_helmet_box,
                'confidence': confidence,
                'method': 'direct_no_helmet' if is_on_vehicle else 'head_only_detection',
                'on_vehicle': is_on_vehicle
            })
            all_detections['riders_without_helmet'].append((track_id, matched_person))
    
    # STRATEGY 2: Fallback - riders without with_helmet near head
    if person_boxes and vehicle_boxes:
        riders = associate_riders(person_boxes, vehicle_boxes)
        
        for person_box, vehicle_box in riders:
            # Skip if already processed
            person_idx = next(
                (i for i, (pb, _) in enumerate(person_boxes_with_conf) if pb == person_box), 
                -1
            )
            if person_idx in processed_persons:
                continue
            
            # Check if any with_helmet box is in this person's head region
            head_region_box = head_region(person_box, HEAD_RATIO)
            has_helmet = any(
                iou(helmet_box, head_region_box) >= HELMET_HEAD_IOU_THRES
                for helmet_box in helmet_boxes
            )
            
            # Get confidences
            person_conf = next((c for b, c in person_boxes_with_conf if b == person_box), 0.5)
            vehicle_conf = next((c for b, c in vehicle_boxes_with_conf if b == vehicle_box), 0.5)
            
            tracked = tracker.update([(person_box, "rider")], current_time)
            track_id = list(tracked.keys())[0] if tracked else tracker.next_id
            
            if has_helmet:
                all_detections['riders_with_helmet'].append((track_id, person_box))
                processed_persons.add(person_idx)
            else:
                # No helmet detected - violation (lower confidence than direct detection)
                confidence = calculate_violation_confidence(person_conf, vehicle_conf, 0.6)
                
                if not deduplicator.is_duplicate(track_id, person_box, current_time):
                    deduplicator.record(track_id, person_box, current_time)
                    
                    violations.append({
                        'track_id': track_id,
                        'box': person_box,
                        'head_box': head_region_box,
                        'confidence': confidence,
                        'method': 'fallback_no_helmet',
                        'on_vehicle': True
                    })
                    all_detections['riders_without_helmet'].append((track_id, person_box))
                    processed_persons.add(person_idx)
    
    return violations, all_detections


# ============================================================
# VIOLATION DEDUPLICATOR
# ============================================================

class ViolationDeduplicator:
    """
    Prevent duplicate violations when track ID changes.
    
    Problem: When a person is occluded and reappears, they get a new track ID,
    causing the same violation to be recorded multiple times.
    
    Solution: Track violations by both track_id AND position.
    """
    
    def __init__(self, time_threshold: float = 3.0, distance_threshold: float = 50):
        self.time_threshold = time_threshold
        self.distance_threshold = distance_threshold
        self.recent_violations = []  # [(timestamp, track_id, center_x, center_y)]
    
    def is_duplicate(self, track_id: int, person_box: List[int], current_time: float) -> bool:
        """Check if this violation is a duplicate of a recent one."""
        # Cleanup old entries
        self.recent_violations = [
            v for v in self.recent_violations
            if (current_time - v[0]) < self.time_threshold * 2
        ]
        
        cx, cy = centroid(person_box)
        
        for timestamp, vid_track_id, vx, vy in self.recent_violations:
            time_diff = current_time - timestamp
            
            if time_diff >= self.time_threshold:
                continue
            
            # Same track ID within cooldown
            if vid_track_id == track_id:
                return True
            
            # Different track ID but same position
            distance = np.sqrt((cx - vx)**2 + (cy - vy)**2)
            if distance < self.distance_threshold:
                return True
        
        return False
    
    def record(self, track_id: int, person_box: List[int], current_time: float):
        """Record a new violation."""
        cx, cy = centroid(person_box)
        self.recent_violations.append((current_time, track_id, cx, cy))


# ============================================================
# LEGACY FUNCTIONS (kept for backward compatibility)
# ============================================================

def detect_yolov3(net, output_layers, image: np.ndarray, 
                  conf_thres: float = 0.5, nms_thres: float = 0.4, 
                  inp_size: int = 416) -> Tuple[List, List, List]:
    """Detect objects using YOLOv3 (legacy)."""
    H, W = image.shape[:2]
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


def detect_helmets(helmet_net, helmet_out, frame: np.ndarray,
                   conf_thres: float = 0.5, nms_thres: float = 0.4,
                   inp_size: int = 416) -> List[List[int]]:
    """Detect helmets using YOLOv3 (legacy)."""
    H, W = frame.shape[:2]
    boxes, _, _ = detect_yolov3(helmet_net, helmet_out, frame, conf_thres, nms_thres, inp_size)
    return [clamp_box(b, W, H) for b in boxes]


def detect_persons_and_bikes(yolo_model, frame: np.ndarray,
                             conf_thres: float = 0.5) -> Tuple[List, List]:
    """Detect persons and motorbikes using YOLOv8 (legacy)."""
    H, W = frame.shape[:2]
    results = yolo_model.predict(
        frame,
        classes=[COCO_PERSON_ID, COCO_MOTORBIKE_ID],
        conf=conf_thres,
        verbose=False
    )
    
    persons = []
    bikes = []
    
    for r in results:
        for box_data in r.boxes:
            x1, y1, x2, y2 = box_data.xyxy[0].cpu().numpy()
            cls_id = int(box_data.cls[0].item())
            
            w = x2 - x1
            h = y2 - y1
            box = [int(x1), int(y1), int(w), int(h)]
            box = clamp_box(box, W, H)
            
            if cls_id == COCO_PERSON_ID:
                persons.append(box)
            elif cls_id == COCO_MOTORBIKE_ID:
                bikes.append(box)
    
    return persons, bikes


def associate_riders(persons: List, bikes: List) -> List[Tuple]:
    """Associate persons with bikes to identify riders."""
    riders = []
    assigned_persons = set()
    
    for bike in bikes:
        matching_persons = []
        
        for idx, p in enumerate(persons):
            if idx in assigned_persons:
                continue
            
            pcx, pcy = bottom_center(p)
            ok_in = (not BOTTOM_CENTER_IN_BIKE) or point_in_box(pcx, pcy, bike)
            ov = iou(p, bike)
            
            if ok_in or ov >= IOU_PERSON_BIKE_THRES:
                score = ov + (0.1 if ok_in else 0.0)
                matching_persons.append((idx, p, score))
        
        # Sort by score
        matching_persons.sort(key=lambda x: x[2], reverse=True)
        
        # Add up to 3 riders per bike
        for i, (idx, p, score) in enumerate(matching_persons[:3]):
            riders.append((p, bike))
            assigned_persons.add(idx)
    
    return riders


def check_helmet_violation(person_box: List[int], helmet_boxes: List[List[int]],
                           head_ratio: float = HEAD_RATIO,
                           iou_thres: float = HELMET_HEAD_IOU_THRES) -> bool:
    """Check if a rider has NO helmet (violation)."""
    hbox = head_region(person_box, head_ratio)
    
    for hb in helmet_boxes:
        if iou(hb, hbox) >= iou_thres:
            return False  # Has helmet
        # Also check center
        hb_cx = hb[0] + hb[2] / 2
        hb_cy = hb[1] + hb[3] / 2
        if (hbox[0] <= hb_cx <= hbox[0] + hbox[2]) and (hbox[1] <= hb_cy <= hbox[1] + hbox[3]):
            return False
    
    return True  # No helmet - violation


def annotate_helmet_frame(frame: np.ndarray, 
                          helmet_boxes: List, 
                          bikes: List,
                          tracked_riders: Dict,
                          violations: List[Tuple]) -> np.ndarray:
    """Create annotated frame for helmet detection."""
    out = frame.copy()
    
    # Draw helmets (green)
    for hb in helmet_boxes:
        draw_box(out, hb, "Helmet", color=(0, 255, 0))
    
    # Draw bikes (blue)
    for b in bikes:
        draw_box(out, b, "Bike", color=(255, 150, 0))
    
    # Draw tracked riders (yellow)
    for tid, pbox in tracked_riders.items():
        draw_box(out, pbox, f"Rider {tid}", color=(0, 255, 255))
    
    # Draw violations (red)
    for tid, pbox in violations:
        draw_box(out, pbox, f"NO HELMET {tid}", color=(0, 0, 255), thickness=3)
        hreg = head_region(pbox, HEAD_RATIO)
        draw_box(out, hreg, "Head", color=(0, 0, 150))
    
    return out


def annotate_unified_frame(frame: np.ndarray, all_detections: Dict,
                           violations: List[Dict]) -> np.ndarray:
    """Create annotated frame for unified model detection."""
    out = frame.copy()
    
    # Draw motorcycles (orange)
    for moto_box in all_detections.get('motorcycle_boxes', []):
        draw_box(out, moto_box, "", color=(0, 165, 255))
    
    # Draw riders WITH helmet (blue)
    for rid, rider_box in all_detections.get('riders_with_helmet', []):
        draw_box(out, rider_box, "", color=(255, 191, 0))
    
    # Draw helmet boxes (green)
    for helmet_box in all_detections.get('helmet_boxes', []):
        draw_box(out, helmet_box, "", color=(0, 255, 0))
    
    # Draw riders WITHOUT helmet (pink) - violations
    for rid, rider_box in all_detections.get('riders_without_helmet', []):
        draw_box(out, rider_box, "", color=(180, 105, 255))
        hreg = head_region(rider_box, HEAD_RATIO)
        draw_box(out, hreg, "", color=(128, 0, 128))
    
    return out
