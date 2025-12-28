"""
redlight_detector.py - Red Light Violation Detection Logic
===========================================================
Shared detection logic for red light violations.
Used by both standalone scripts and Kafka consumers.
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional, Any

from .base import (
    centroid, bottom_center, clamp_box, point_in_polygon,
    draw_box, draw_stop_line, draw_detection_zone
)
from .tracker import CentroidTracker


# COCO Class IDs for YOLOv8
COCO_TRAFFIC_LIGHT_ID = 9
COCO_CAR_ID = 2
COCO_MOTORCYCLE_ID = 3
COCO_BUS_ID = 5
COCO_TRUCK_ID = 7

VEHICLE_CLASSES = [COCO_CAR_ID, COCO_MOTORCYCLE_ID, COCO_BUS_ID, COCO_TRUCK_ID]
VEHICLE_NAMES = {
    COCO_CAR_ID: "car",
    COCO_MOTORCYCLE_ID: "motorcycle",
    COCO_BUS_ID: "bus",
    COCO_TRUCK_ID: "truck"
}

# Default color detection config
DEFAULT_COLOR_CONFIG = {
    "red_lower1": [0, 100, 100],
    "red_upper1": [10, 255, 255],
    "red_lower2": [160, 100, 100],
    "red_upper2": [180, 255, 255],
    "green_lower": [40, 100, 100],
    "green_upper": [80, 255, 255],
    "yellow_lower": [20, 100, 100],
    "yellow_upper": [35, 255, 255]
}


class TrafficLightDetector:
    """Detects traffic light state using color analysis"""
    
    def __init__(self, yolo_model, config: Dict):
        """
        Args:
            yolo_model: YOLOv8 model instance
            config: Camera config with traffic_light_roi and color_detection
        """
        self.yolo_model = yolo_model
        self.config = config
        self.light_roi = config.get("traffic_light_roi", {})
        self.color_config = config.get("color_detection", DEFAULT_COLOR_CONFIG)
    
    def detect_light_state(self, frame: np.ndarray) -> str:
        """
        Detect traffic light state from frame.
        Returns: 'RED', 'GREEN', 'YELLOW', or 'UNKNOWN'
        """
        # Method 1: Try YOLO detection first
        if self.yolo_model:
            state = self._detect_with_yolo(frame)
            if state != "UNKNOWN":
                return state
        
        # Method 2: Fallback to color detection in ROI
        return self._detect_with_color(frame)
    
    def _detect_with_yolo(self, frame: np.ndarray) -> str:
        """Detect traffic light using YOLO"""
        results = self.yolo_model.predict(
            frame,
            classes=[COCO_TRAFFIC_LIGHT_ID],
            conf=0.3,
            verbose=False
        )
        
        for r in results:
            if len(r.boxes) > 0:
                for box_data in r.boxes:
                    x1, y1, x2, y2 = map(int, box_data.xyxy[0].cpu().numpy())
                    light_crop = frame[y1:y2, x1:x2]
                    if light_crop.size > 0:
                        return self._analyze_color(light_crop)
        
        return "UNKNOWN"
    
    def _detect_with_color(self, frame: np.ndarray) -> str:
        """Detect traffic light using color analysis in ROI"""
        roi = self.light_roi
        if not roi:
            return "UNKNOWN"
        
        x1 = max(0, roi.get("x1", 0))
        y1 = max(0, roi.get("y1", 0))
        x2 = min(frame.shape[1], roi.get("x2", frame.shape[1]))
        y2 = min(frame.shape[0], roi.get("y2", 150))
        
        if x2 <= x1 or y2 <= y1:
            return "UNKNOWN"
        
        roi_crop = frame[y1:y2, x1:x2]
        return self._analyze_color(roi_crop)
    
    def _analyze_color(self, img: np.ndarray) -> str:
        """Analyze color of traffic light image"""
        if img.size == 0:
            return "UNKNOWN"
        
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        cc = self.color_config
        
        # Red masks (two ranges because red wraps in HSV)
        mask_red1 = cv2.inRange(hsv, np.array(cc["red_lower1"]), np.array(cc["red_upper1"]))
        mask_red2 = cv2.inRange(hsv, np.array(cc["red_lower2"]), np.array(cc["red_upper2"]))
        mask_red = cv2.bitwise_or(mask_red1, mask_red2)
        
        # Green/Yellow masks
        mask_green = cv2.inRange(hsv, np.array(cc["green_lower"]), np.array(cc["green_upper"]))
        mask_yellow = cv2.inRange(hsv, np.array(cc["yellow_lower"]), np.array(cc["yellow_upper"]))
        
        # Count pixels
        red_count = cv2.countNonZero(mask_red)
        green_count = cv2.countNonZero(mask_green)
        yellow_count = cv2.countNonZero(mask_yellow)
        
        min_pixels = 50
        if red_count > green_count and red_count > yellow_count and red_count > min_pixels:
            return "RED"
        elif green_count > red_count and green_count > yellow_count and green_count > min_pixels:
            return "GREEN"
        elif yellow_count > min_pixels:
            return "YELLOW"
        
        return "UNKNOWN"
    
    def draw_debug(self, frame: np.ndarray, state: str) -> None:
        """Draw traffic light ROI and state on frame"""
        roi = self.light_roi
        if not roi:
            return
        
        x1, y1 = roi.get("x1", 0), roi.get("y1", 0)
        x2, y2 = roi.get("x2", 100), roi.get("y2", 100)
        
        color = (0, 0, 255) if state == "RED" else (0, 255, 0) if state == "GREEN" else (0, 255, 255)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, f"Light: {state}", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)


class RedLightViolationChecker:
    """Checks for red light violations"""
    
    def __init__(self, config: Dict):
        """
        Args:
            config: Camera config with stop_line settings
        """
        self.config = config
        stop_line = config.get("stop_line", {})
        self.stop_line_y = stop_line.get("y", 400)
        self.tolerance = stop_line.get("tolerance", 30)
        self.violation_direction = stop_line.get("violation_direction", "below")
    
    def check_violation(self, track_info: Dict, light_state: str) -> bool:
        """
        Check if vehicle violated red light.
        
        Args:
            track_info: Track info dict with 'box' and 'crossed' keys
            light_state: Current traffic light state
            
        Returns:
            True if violation detected
        """
        if light_state != "RED":
            return False
        
        box = track_info["box"]
        _, vehicle_y = bottom_center(box)
        
        # Check crossing based on direction
        if self.violation_direction == "above":
            crossed_now = vehicle_y < self.stop_line_y
        else:
            crossed_now = vehicle_y > self.stop_line_y
        
        previously_crossed = track_info.get("crossed", False)
        
        # Violation: just crossed the line while light is red
        if crossed_now and not previously_crossed:
            track_info["crossed"] = True
            return True
        
        if crossed_now:
            track_info["crossed"] = True
        
        return False


def detect_vehicles(yolo_model, frame: np.ndarray, 
                    detection_zone: Optional[List] = None,
                    conf_thres: float = 0.4) -> List[Tuple]:
    """
    Detect vehicles in frame.
    
    Args:
        yolo_model: YOLOv8 model instance
        frame: Input frame
        detection_zone: Optional polygon to filter detections
        conf_thres: Confidence threshold
        
    Returns:
        List of (box, vehicle_type) tuples
    """
    H, W = frame.shape[:2]
    results = yolo_model.predict(
        frame,
        classes=VEHICLE_CLASSES,
        conf=conf_thres,
        verbose=False
    )
    
    detections = []
    for r in results:
        for box_data in r.boxes:
            x1, y1, x2, y2 = map(int, box_data.xyxy[0].cpu().numpy())
            cls_id = int(box_data.cls[0].item())
            box = clamp_box([x1, y1, x2 - x1, y2 - y1], W, H)
            vehicle_type = VEHICLE_NAMES.get(cls_id, "vehicle")
            
            # Filter by detection zone if provided
            if detection_zone:
                vehicle_center = centroid(box)
                if not point_in_polygon(vehicle_center, detection_zone):
                    continue
            
            detections.append((box, vehicle_type))
    
    return detections


def annotate_violation_frame(frame: np.ndarray, config: Dict, 
                             light_state: str, tracked: Dict,
                             violations: List[Tuple]) -> np.ndarray:
    """
    Create annotated frame with all detection visualizations.
    
    Args:
        frame: Input frame
        config: Camera config
        light_state: Current light state
        tracked: Dict of tracked vehicles
        violations: List of (track_id, track_info) for violations
        
    Returns:
        Annotated frame
    """
    out = frame.copy()
    H, W = out.shape[:2]
    
    # Draw stop line
    stop_line_y = config.get("stop_line", {}).get("y", 400)
    draw_stop_line(out, stop_line_y)
    
    # Draw traffic light ROI
    roi = config.get("traffic_light_roi", {})
    if roi:
        x1, y1 = roi.get("x1", 0), roi.get("y1", 0)
        x2, y2 = roi.get("x2", 100), roi.get("y2", 100)
        color = (0, 0, 255) if light_state == "RED" else (0, 255, 0) if light_state == "GREEN" else (0, 255, 255)
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
        cv2.putText(out, f"Light: {light_state}", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    
    # Draw detection zone
    detection_zone = config.get("detection_zone", [])
    draw_detection_zone(out, detection_zone)
    
    # Draw all tracked vehicles
    for tid, track_info in tracked.items():
        box = track_info["box"]
        vehicle_type = track_info.get("vehicle_type", track_info.get("extra", "vehicle"))
        draw_box(out, box, f"{vehicle_type} #{tid}", color=(0, 255, 0))
    
    # Draw violations in red
    for tid, track_info in violations:
        box = track_info["box"]
        draw_box(out, box, f"VIOLATION #{tid}", color=(0, 0, 255), thickness=3)
    
    return out
