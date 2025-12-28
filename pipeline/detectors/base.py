"""
base.py - Shared utilities and base classes for detection
==========================================================
"""

import os
import cv2
import numpy as np
import json
from typing import List, Tuple, Dict, Optional


# =========================
# CONFIG PATHS
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODELS_DIR = os.path.join(BASE_DIR, "models")
CONFIG_DIR = os.path.join(BASE_DIR, "config")


# =========================
# BOX UTILITIES
# =========================
def clamp_box(box: List[int], W: int, H: int) -> List[int]:
    """Clamp box [x, y, w, h] to image boundaries"""
    x, y, w, h = box
    x = max(0, x)
    y = max(0, y)
    w = max(0, min(w, W - x))
    h = max(0, min(h, H - y))
    return [x, y, w, h]


def box_xyxy(box: List[int]) -> Tuple[int, int, int, int]:
    """Convert [x, y, w, h] to (x1, y1, x2, y2)"""
    x, y, w, h = box
    return (x, y, x + w, y + h)


def centroid(box: List[int]) -> Tuple[float, float]:
    """Get center point of box"""
    x, y, w, h = box
    return (x + w / 2.0, y + h / 2.0)


def bottom_center(box: List[int]) -> Tuple[float, float]:
    """Get bottom center point of box (useful for checking stop line crossing)"""
    x, y, w, h = box
    return (x + w / 2.0, y + h)


def iou(a: List[int], b: List[int]) -> float:
    """Calculate Intersection over Union between two boxes"""
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


def point_in_box(px: float, py: float, box: List[int]) -> bool:
    """Check if point is inside box"""
    x, y, w, h = box
    return (px >= x) and (px <= x + w) and (py >= y) and (py <= y + h)


def point_in_polygon(point: Tuple[float, float], polygon: List[List[int]]) -> bool:
    """Check if a point is inside a polygon using ray casting algorithm"""
    if not polygon or len(polygon) < 3:
        return True  # No polygon defined, allow all points
    
    x, y = point
    n = len(polygon)
    inside = False
    
    p1x, p1y = polygon[0][0], polygon[0][1]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n][0], polygon[i % n][1]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    
    return inside


def head_region(person_box: List[int], head_ratio: float = 0.35) -> List[int]:
    """Get head region of a person box (upper portion)"""
    x, y, w, h = person_box
    hh = int(h * head_ratio)
    return [x, y, w, max(1, hh)]


# =========================
# DRAWING UTILITIES
# =========================
def draw_box(img: np.ndarray, box: List[int], label: str, 
             color: Tuple[int, int, int] = (0, 255, 0), thickness: int = 2) -> None:
    """Draw bounding box with label on image"""
    x, y, w, h = box
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(img.shape[1] - 1, x + w), min(img.shape[0] - 1, y + h)
    cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)
    cv2.putText(img, label, (x1, max(0, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)


def draw_stop_line(img: np.ndarray, y_pos: int, 
                   color: Tuple[int, int, int] = (0, 255, 255), thickness: int = 2) -> None:
    """Draw horizontal stop line on image"""
    cv2.line(img, (0, y_pos), (img.shape[1], y_pos), color, thickness)
    cv2.putText(img, "STOP LINE", (10, y_pos - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA)


def draw_detection_zone(img: np.ndarray, zone: List[List[int]], 
                        color: Tuple[int, int, int] = (255, 0, 255), thickness: int = 2) -> None:
    """Draw detection zone polygon on image"""
    if zone and len(zone) >= 3:
        pts = np.array(zone, np.int32).reshape((-1, 1, 2))
        cv2.polylines(img, [pts], True, color, thickness)


# =========================
# CONFIG UTILITIES
# =========================
def load_roi_config(config_path: Optional[str] = None) -> Dict:
    """Load ROI configuration from JSON file"""
    # Try provided path first
    if config_path and os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
            return config
    
    # Try default location
    default_path = os.path.join(CONFIG_DIR, "roi_config.json")
    if os.path.exists(default_path):
        with open(default_path, 'r') as f:
            config = json.load(f)
            return config
    
    return {}


def get_camera_config(all_config: Dict, camera_id: str) -> Dict:
    """Get camera-specific config with fallback to default"""
    return all_config.get(camera_id, all_config.get("default", {}))


def scale_config(config: Dict, actual_width: int, actual_height: int) -> Dict:
    """Scale ROI config to match actual frame dimensions"""
    config_width = config.get("frame_width", 1920)
    config_height = config.get("frame_height", 1080)
    
    scale_x = actual_width / config_width
    scale_y = actual_height / config_height
    
    scaled = config.copy()
    
    # Scale stop line
    if "stop_line" in config:
        raw_y = config["stop_line"].get("y", 400)
        scaled["stop_line"] = {
            "y": int(raw_y * scale_y),
            "tolerance": config["stop_line"].get("tolerance", 30),
            "violation_direction": config["stop_line"].get("violation_direction", "below")
        }
    
    # Scale traffic light ROI
    if "traffic_light_roi" in config:
        raw_roi = config["traffic_light_roi"]
        scaled["traffic_light_roi"] = {
            "x1": int(raw_roi.get("x1", 0) * scale_x),
            "y1": int(raw_roi.get("y1", 0) * scale_y),
            "x2": int(raw_roi.get("x2", 100) * scale_x),
            "y2": int(raw_roi.get("y2", 100) * scale_y)
        }
    
    # Scale detection zone
    if "detection_zone" in config and config["detection_zone"]:
        raw_zone = config["detection_zone"]
        scaled["detection_zone"] = [
            [int(pt[0] * scale_x), int(pt[1] * scale_y)] for pt in raw_zone
        ]
    
    return scaled
