"""
helmet_detector.py - Helmet Violation Detection Logic
======================================================
Shared detection logic for helmet violations.
Used by both standalone scripts and Kafka consumers.
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional, Any

from .base import (
    centroid, bottom_center, clamp_box, iou, point_in_box, head_region, draw_box
)
from .tracker import CentroidTracker


# YOLOv8 Class IDs
COCO_PERSON_ID = 0
COCO_MOTORBIKE_ID = 3

# Detection thresholds
IOU_PERSON_BIKE_THRES = 0.02
BOTTOM_CENTER_IN_BIKE = True
HEAD_RATIO = 0.35
HELMET_HEAD_IOU_THRES = 0.02


def get_output_layer_names(net):
    """Get output layer names for YOLOv3 network"""
    names = net.getLayerNames()
    return [names[i - 1] for i in net.getUnconnectedOutLayers().flatten()]


def detect_yolov3(net, output_layers, image: np.ndarray, 
                  conf_thres: float = 0.5, nms_thres: float = 0.4, 
                  inp_size: int = 416) -> Tuple[List, List, List]:
    """
    Detect objects using YOLOv3.
    
    Returns:
        boxes: List of [x, y, w, h]
        class_ids: List of class IDs
        confs: List of confidences
    """
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
    """
    Detect helmets in frame using YOLOv3.
    
    Returns:
        List of helmet boxes [x, y, w, h]
    """
    H, W = frame.shape[:2]
    boxes, _, _ = detect_yolov3(helmet_net, helmet_out, frame, conf_thres, nms_thres, inp_size)
    return [clamp_box(b, W, H) for b in boxes]


def detect_persons_and_bikes(yolo_model, frame: np.ndarray,
                             conf_thres: float = 0.5) -> Tuple[List, List]:
    """
    Detect persons and motorbikes using YOLOv8.
    
    Returns:
        persons: List of person boxes
        bikes: List of motorbike boxes
    """
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
    """
    Associate persons with bikes to identify riders.
    
    Returns:
        List of (person_box, bike_box) tuples
    """
    riders = []
    
    for p in persons:
        pcx, pcy = bottom_center(p)
        matched = None
        best = 0.0
        
        for b in bikes:
            ok_in = (not BOTTOM_CENTER_IN_BIKE) or point_in_box(pcx, pcy, b)
            ov = iou(p, b)
            
            if ok_in or ov >= IOU_PERSON_BIKE_THRES:
                score = ov + (0.1 if ok_in else 0.0)
                if score > best:
                    best = score
                    matched = b
        
        if matched is not None:
            riders.append((p, matched))
    
    return riders


def check_helmet_violation(person_box: List[int], helmet_boxes: List[List[int]],
                           head_ratio: float = HEAD_RATIO,
                           iou_thres: float = HELMET_HEAD_IOU_THRES) -> bool:
    """
    Check if a rider has a helmet on their head.
    
    Args:
        person_box: Person bounding box
        helmet_boxes: List of detected helmet boxes
        head_ratio: Ratio of head region from top of person
        iou_thres: Minimum IoU threshold for helmet-head match
        
    Returns:
        True if NO helmet detected (violation)
    """
    hbox = head_region(person_box, head_ratio)
    
    for hb in helmet_boxes:
        if iou(hb, hbox) >= iou_thres:
            return False  # Has helmet
    
    return True  # No helmet - violation


def annotate_helmet_frame(frame: np.ndarray, 
                          helmet_boxes: List, 
                          bikes: List,
                          tracked_riders: Dict,
                          violations: List[Tuple]) -> np.ndarray:
    """
    Create annotated frame for helmet detection.
    
    Args:
        frame: Input frame
        helmet_boxes: Detected helmet boxes
        bikes: Detected motorbike boxes
        tracked_riders: Dict of tracked riders
        violations: List of (track_id, person_box) for violations
        
    Returns:
        Annotated frame
    """
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
        # Draw head region
        hreg = head_region(pbox, HEAD_RATIO)
        draw_box(out, hreg, "Head", color=(0, 0, 150))
    
    return out
