import cv2
import numpy as np
import json
import math

def detect_traffic_light_color(image_crop):
    """
    Detects the color of the traffic light using HSV thresholding.
    Returns: 'RED', 'GREEN', 'YELLOW', or 'UNKNOWN'
    """
    if image_crop is None or image_crop.size == 0:
        return 'UNKNOWN'

    hsv = cv2.cvtColor(image_crop, cv2.COLOR_BGR2HSV)

    # Red color range (two ranges in HSV because Red wraps around)
    lower_red1 = np.array([0, 70, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 70, 50])
    upper_red2 = np.array([180, 255, 255])

    # Green color range
    lower_green = np.array([40, 70, 50])
    upper_green = np.array([90, 255, 255])

    # Yellow color range (optional, for safety)
    lower_yellow = np.array([20, 70, 50])
    upper_yellow = np.array([30, 255, 255])

    # Create masks
    mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask_red = cv2.add(mask_red1, mask_red2)
    
    mask_green = cv2.inRange(hsv, lower_green, upper_green)
    mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)

    # Count pixels
    red_pixels = cv2.countNonZero(mask_red)
    green_pixels = cv2.countNonZero(mask_green)
    yellow_pixels = cv2.countNonZero(mask_yellow)

    total_pixels = image_crop.shape[0] * image_crop.shape[1]
    
    # Threshold (e.g., need at least 5% of pixels to be that color to count)
    # This avoids noise
    threshold = total_pixels * 0.05 

    if red_pixels > threshold and red_pixels > green_pixels and red_pixels > yellow_pixels:
        return 'RED'
    elif green_pixels > threshold and green_pixels > red_pixels and green_pixels > yellow_pixels:
        return 'GREEN'
    elif yellow_pixels > threshold:
        return 'YELLOW'
    
    return 'UNKNOWN'

def check_stop_line_violation(vehicle_center, stop_y):
    """
    Checks if a vehicle has crossed the stop line.
    Assumption: Camera view is such that vehicles move from top to bottom (y increases).
    """
    # Assuming standard view: top of image is y=0. Stop line is at y=stop_y.
    # If vehicle moves down detected below the line, it crossed it.
    # Logic needs to be robust. 
    # For now, simplistic check: Is center_y > stop_y?
    _, cy = vehicle_center
    return cy > stop_y

def process_violations(detections, roi_config, image_shape=None, frame=None):
    """
    Core business logic to determine violations.
    Args:
        detections: List of dicts (class_name, bbox, center, confidence)
        roi_config: Dict containing stop_line, traffic_light_roi
        image_shape: (height, width)
        frame: The actual image array (needed for color detection)
    
    Returns:
        List of violation dicts
    """
    violations = []
    
    # Extract config
    stop_line = roi_config.get("stop_line", [])
    if not stop_line or len(stop_line) < 2:
        return []
    
    # Assuming horizontal stop line for simplicity, taking average Y
    stop_y = sum(p[1] for p in stop_line) / len(stop_line)
    
    # Detect Traffic Light State
    traffic_light_state = 'UNKNOWN'
    
    # 1. First, check if we have a specific ROI for traffic light in config (Static ROI)
    # This is more reliable than detecting the object "traffic light" if we know where it is.
    tl_roi_coords = roi_config.get("traffic_light_roi") 
    if tl_roi_coords and frame is not None:
         # ROI format: [x1, y1, x2, y2] or similar. Let's assume [x1, y1, x2, y2]
         if len(tl_roi_coords) == 4:
             x1, y1, x2, y2 = map(int, tl_roi_coords)
             # Ensure coords are within image
             h, w = frame.shape[:2]
             x1, x2 = max(0, x1), min(w, x2)
             y1, y2 = max(0, y1), min(h, y2)
             
             crop = frame[y1:y2, x1:x2]
             traffic_light_state = detect_traffic_light_color(crop)
    
    # 2. Fallback: If no static ROI or state not found, use detected "traffic light" objects
    if traffic_light_state == 'UNKNOWN' and frame is not None:
        traffic_lights = [d for d in detections if d['class_name'] == 'traffic light']
        # Use the largest/most confident one
        for tl in traffic_lights:
            bbox = tl['bbox'] # [x1, y1, x2, y2]
            x1, y1, x2, y2 = map(int, bbox)
            h, w = frame.shape[:2]
            x1, x2 = max(0, x1), min(w, x2)
            y1, y2 = max(0, y1), min(h, y2)
            
            crop = frame[y1:y2, x1:x2]
            state = detect_traffic_light_color(crop)
            if state in ['RED', 'GREEN', 'YELLOW']:
                traffic_light_state = state
                break

    # If Traffic Light is NOT RED, there is no violation (assuming no other rules for now)
    # Note: 'UNKNOWN' might mean we missed the light. Safer to NOT flag violation to avoid false positives?
    # Or flag warning? User wants to "fix false positives" (model du doan sai), so likely we strictly check for RED.
    if traffic_light_state != 'RED':
        return []

    # Check Vehicles
    vehicles = [d for d in detections if d['class_name'] in ['car', 'motorcycle', 'bus', 'truck']]
    
    for vehicle in vehicles:
        if check_stop_line_violation(vehicle['center'], stop_y):
            violations.append({
                "type": "stop_line_crossing",
                "vehicle": vehicle['class_name'],
                "confidence": vehicle['confidence'],
                "position": vehicle['center'],
                "traffic_light_state": traffic_light_state
            })
            
    return violations
