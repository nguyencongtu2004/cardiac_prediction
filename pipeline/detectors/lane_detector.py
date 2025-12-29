"""
lane_detector.py - Lane Violation Detection Logic
==================================================
Shared detection logic for lane violations.
Used by both standalone scripts and Kafka consumers.

Phát hiện vi phạm lấn làn dựa trên:
- Xe di chuyển qua vạch kẻ liền (solid line)
- Xe chuyển làn không đúng quy định
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional, Any

from .base import (
    centroid, bottom_center, clamp_box, point_in_polygon,
    draw_box
)
from .tracker import CentroidTracker


# COCO Class IDs for YOLOv8
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


def point_to_line_distance(px: float, py: float, 
                           x1: float, y1: float, 
                           x2: float, y2: float) -> float:
    """Calculate perpendicular distance from point to line segment"""
    line_len_sq = (x2 - x1) ** 2 + (y2 - y1) ** 2
    if line_len_sq == 0:
        return np.sqrt((px - x1) ** 2 + (py - y1) ** 2)
    
    t = max(0, min(1, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / line_len_sq))
    proj_x = x1 + t * (x2 - x1)
    proj_y = y1 + t * (y2 - y1)
    
    return np.sqrt((px - proj_x) ** 2 + (py - proj_y) ** 2)


def get_line_side(px: float, py: float, 
                  x1: float, y1: float, 
                  x2: float, y2: float) -> int:
    """
    Determine which side of a line a point is on.
    Returns: -1 (left), 0 (on line), 1 (right)
    """
    d = (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)
    if abs(d) < 1e-6:
        return 0
    return 1 if d > 0 else -1


class LaneLine:
    """Represents a lane boundary line"""
    
    def __init__(self, line_config: Dict, line_id: int):
        self.id = line_id
        self.x1 = line_config.get("x1", 0)
        self.y1 = line_config.get("y1", 0)
        self.x2 = line_config.get("x2", 0)
        self.y2 = line_config.get("y2", 0)
        self.line_type = line_config.get("type", "solid")  # "solid" or "dashed"
    
    def get_distance(self, px: float, py: float) -> float:
        """Get distance from point to this line"""
        return point_to_line_distance(px, py, self.x1, self.y1, self.x2, self.y2)
    
    def get_side(self, px: float, py: float) -> int:
        """Get which side of line the point is on"""
        return get_line_side(px, py, self.x1, self.y1, self.x2, self.y2)
    
    def is_solid(self) -> bool:
        return self.line_type == "solid"
    
    def draw(self, frame: np.ndarray, color: Optional[Tuple[int, int, int]] = None) -> None:
        """Draw this line on frame"""
        if color is None:
            color = (255, 255, 0) if self.is_solid() else (255, 255, 100)
        
        thickness = 3 if self.is_solid() else 2
        
        if self.is_solid():
            cv2.line(frame, (self.x1, self.y1), (self.x2, self.y2), color, thickness)
        else:
            # Draw dashed line
            self._draw_dashed_line(frame, color, thickness)
    
    def _draw_dashed_line(self, frame: np.ndarray, color: Tuple[int, int, int], thickness: int) -> None:
        """Draw a dashed line"""
        dash_length = 20
        gap_length = 15
        
        dx = self.x2 - self.x1
        dy = self.y2 - self.y1
        line_length = np.sqrt(dx ** 2 + dy ** 2)
        
        if line_length == 0:
            return
        
        dx /= line_length
        dy /= line_length
        
        current_length = 0
        drawing = True
        
        while current_length < line_length:
            if drawing:
                end_length = min(current_length + dash_length, line_length)
                start_x = int(self.x1 + dx * current_length)
                start_y = int(self.y1 + dy * current_length)
                end_x = int(self.x1 + dx * end_length)
                end_y = int(self.y1 + dy * end_length)
                cv2.line(frame, (start_x, start_y), (end_x, end_y), color, thickness)
                current_length = end_length
            else:
                current_length += gap_length
            drawing = not drawing


class LaneViolationChecker:
    """Checks for lane violations"""
    
    def __init__(self, config: Dict):
        """
        Args:
            config: Camera config with lane_lines settings
        """
        self.config = config
        self.lane_lines: List[LaneLine] = []
        self.crossing_threshold = config.get("lane_crossing_threshold", 30)  # pixels
        
        # Load lane lines
        lane_lines_config = config.get("lane_lines", [])
        for i, line_config in enumerate(lane_lines_config):
            self.lane_lines.append(LaneLine(line_config, i))
        
        # Track which side of each line each vehicle was on
        self.vehicle_line_sides: Dict[int, Dict[int, int]] = {}  # track_id -> {line_id -> side}
    
    def check_violation(self, track_id: int, track_info: Dict) -> Optional[Dict]:
        """
        Check if vehicle violated lane rules by crossing a solid line.
        
        Args:
            track_id: Vehicle track ID
            track_info: Track info dict with 'box' key
            
        Returns:
            Violation info dict if violation detected, None otherwise
        """
        if not self.lane_lines:
            return None
        
        box = track_info["box"]
        vehicle_center = bottom_center(box)
        px, py = vehicle_center
        
        # Initialize tracking for this vehicle if needed
        if track_id not in self.vehicle_line_sides:
            self.vehicle_line_sides[track_id] = {}
            # Record initial sides
            for line in self.lane_lines:
                self.vehicle_line_sides[track_id][line.id] = line.get_side(px, py)
            return None
        
        # Check each solid line
        for line in self.lane_lines:
            if not line.is_solid():
                continue
            
            current_side = line.get_side(px, py)
            previous_side = self.vehicle_line_sides[track_id].get(line.id, 0)
            
            # Check if crossed (side changed and neither is 0)
            if previous_side != 0 and current_side != 0 and previous_side != current_side:
                # Also check distance to ensure it's a real crossing
                dist = line.get_distance(px, py)
                if dist < self.crossing_threshold * 2:  # Within reasonable range
                    # Update side tracking
                    self.vehicle_line_sides[track_id][line.id] = current_side
                    
                    return {
                        "type": "solid_line_crossing",
                        "line_id": line.id,
                        "line_type": line.line_type,
                        "from_side": "left" if previous_side == -1 else "right",
                        "to_side": "left" if current_side == -1 else "right",
                        "distance": dist,
                        "position": (px, py)
                    }
            
            # Update tracking
            if current_side != 0:
                self.vehicle_line_sides[track_id][line.id] = current_side
        
        return None
    
    def get_vehicle_lane(self, box: List[int]) -> int:
        """
        Get which lane a vehicle is in based on its position.
        Returns lane index (0-based) or -1 if outside lanes.
        """
        if len(self.lane_lines) < 2:
            return -1
        
        px, py = bottom_center(box)
        
        # Simple approach: count how many lines the vehicle is to the right of
        lane = 0
        for line in self.lane_lines:
            if line.get_side(px, py) > 0:  # right of line
                lane += 1
        
        return lane
    
    def cleanup_old_tracks(self, active_track_ids: set) -> None:
        """Remove tracking data for vehicles that are no longer being tracked"""
        old_ids = set(self.vehicle_line_sides.keys()) - active_track_ids
        for tid in old_ids:
            del self.vehicle_line_sides[tid]


def detect_vehicles_for_lane(yolo_model, frame: np.ndarray,
                              detection_zone: Optional[List] = None,
                              conf_thres: float = 0.4) -> List[Tuple]:
    """
    Detect vehicles in frame for lane violation detection.
    
    Args:
        yolo_model: YOLOv8 model instance
        frame: Input frame
        detection_zone: Optional polygon to filter detections
        conf_thres: Confidence threshold
        
    Returns:
        List of (box, vehicle_type, confidence) tuples
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
            conf = float(box_data.conf[0].item())
            box = clamp_box([x1, y1, x2 - x1, y2 - y1], W, H)
            vehicle_type = VEHICLE_NAMES.get(cls_id, "vehicle")
            
            # Filter by detection zone if provided
            if detection_zone:
                vehicle_center = centroid(box)
                if not point_in_polygon(vehicle_center, detection_zone):
                    continue
            
            detections.append((box, vehicle_type, conf))
    
    return detections


def draw_lane_lines(frame: np.ndarray, lane_lines: List[LaneLine]) -> None:
    """Draw all lane lines on frame"""
    for line in lane_lines:
        line.draw(frame)


def annotate_lane_frame(frame: np.ndarray, config: Dict,
                        lane_checker: LaneViolationChecker,
                        tracked: Dict,
                        violations: List[Tuple]) -> np.ndarray:
    """
    Create annotated frame with lane detection visualizations.
    
    Args:
        frame: Input frame
        config: Camera config
        lane_checker: LaneViolationChecker instance
        tracked: Dict of tracked vehicles
        violations: List of (track_id, track_info, violation_info) tuples
        
    Returns:
        Annotated frame
    """
    out = frame.copy()
    H, W = out.shape[:2]
    
    # Draw lane lines
    draw_lane_lines(out, lane_checker.lane_lines)
    
    # Draw detection zone if present
    detection_zone = config.get("detection_zone", [])
    if detection_zone and len(detection_zone) >= 3:
        pts = np.array(detection_zone, np.int32).reshape((-1, 1, 2))
        cv2.polylines(out, [pts], True, (255, 0, 255), 2)
    
    # Draw all tracked vehicles
    for tid, track_info in tracked.items():
        box = track_info["box"]
        vehicle_type = track_info.get("vehicle_type", track_info.get("extra", "vehicle"))
        lane = lane_checker.get_vehicle_lane(box)
        label = f"{vehicle_type} #{tid} L{lane}" if lane >= 0 else f"{vehicle_type} #{tid}"
        draw_box(out, box, label, color=(0, 255, 0))
    
    # Draw violations in red
    for tid, track_info, violation_info in violations:
        box = track_info["box"]
        label = f"LANE VIOLATION #{tid}"
        draw_box(out, box, label, color=(0, 0, 255), thickness=3)
        
        # Draw violation position marker
        px, py = violation_info.get("position", bottom_center(box))
        cv2.circle(out, (int(px), int(py)), 8, (0, 0, 255), -1)
        
        # Draw text describing violation
        line_id = violation_info.get("line_id", -1)
        cv2.putText(out, f"Crossed solid line {line_id}", 
                    (int(px) - 50, int(py) - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    
    return out
