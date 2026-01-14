"""
ROI Configuration Tool
======================
Công cụ trực quan để cấu hình vùng ROI cho phát hiện đèn giao thông.

Cách sử dụng:
1. Chạy: python scripts/configure_roi.py --video data/video/cam1.mp4 --camera cam1
2. Click và kéo để vẽ vùng đèn giao thông (traffic light ROI)
3. Click để đặt vị trí vạch dừng (stop line)
4. Click 4 điểm để vẽ vùng nhận diện xe (detection zone)
5. Nhấn 'S' để lưu config
6. Nhấn 'R' để reset
7. Nhấn 'Q' để thoát

Hotkeys:
  T - Chế độ vẽ Traffic Light ROI
  L - Chế độ đặt Stop Line
  D - Chế độ vẽ Detection Zone (4 điểm)
  S - Lưu config vào roi_config.json
  R - Reset tất cả
  Q - Thoát
"""

import os
import cv2
import json
import argparse
import numpy as np

# =========================
# CONFIG
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
DATA_DIR = os.path.join(BASE_DIR, "data")

DEFAULT_VIDEO = os.path.join(DATA_DIR, "video/dendo.mp4")
CONFIG_FILE = os.path.join(CONFIG_DIR, "roi_config.json")

# Colors (BGR)
COLOR_TRAFFIC_LIGHT = (0, 255, 0)  # Green
COLOR_STOP_LINE = (0, 255, 255)    # Yellow
COLOR_DETECTION_ZONE = (255, 0, 255)  # Magenta
COLOR_TEXT = (255, 255, 255)       # White
COLOR_HELP = (200, 200, 200)       # Light gray

# =========================
# GLOBALS for mouse callback
# =========================
drawing = False
start_point = None
current_mode = "traffic_light"  # "traffic_light", "stop_line", "detection_zone"

# ROI values
traffic_light_roi = {"x1": 0, "y1": 0, "x2": 0, "y2": 0}
stop_line_y = 400
frame_width = 1920
frame_height = 1080

# Detection zone - 4 points (quadrilateral)
detection_zone_points = []  # List of (x, y) tuples


def mouse_callback(event, x, y, flags, param):
    global drawing, start_point, traffic_light_roi, stop_line_y, current_mode, detection_zone_points
    
    if current_mode == "traffic_light":
        if event == cv2.EVENT_LBUTTONDOWN:
            drawing = True
            start_point = (x, y)
            traffic_light_roi["x1"] = x
            traffic_light_roi["y1"] = y
        
        elif event == cv2.EVENT_MOUSEMOVE:
            if drawing:
                traffic_light_roi["x2"] = x
                traffic_light_roi["y2"] = y
        
        elif event == cv2.EVENT_LBUTTONUP:
            drawing = False
            traffic_light_roi["x2"] = x
            traffic_light_roi["y2"] = y
            # Ensure x1 < x2 and y1 < y2
            if traffic_light_roi["x1"] > traffic_light_roi["x2"]:
                traffic_light_roi["x1"], traffic_light_roi["x2"] = traffic_light_roi["x2"], traffic_light_roi["x1"]
            if traffic_light_roi["y1"] > traffic_light_roi["y2"]:
                traffic_light_roi["y1"], traffic_light_roi["y2"] = traffic_light_roi["y2"], traffic_light_roi["y1"]
    
    elif current_mode == "stop_line":
        if event == cv2.EVENT_LBUTTONDOWN:
            stop_line_y = y
            print(f"[INFO] Stop line set to Y={y}")
    
    elif current_mode == "detection_zone":
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(detection_zone_points) < 4:
                detection_zone_points.append((x, y))
                print(f"[INFO] Detection zone point {len(detection_zone_points)}: ({x}, {y})")
                if len(detection_zone_points) == 4:
                    print("[INFO] Detection zone complete! 4 points set.")


def draw_overlay(frame):
    """Draw ROI overlay on frame"""
    overlay = frame.copy()
    
    # Draw traffic light ROI
    if traffic_light_roi["x2"] > 0 and traffic_light_roi["y2"] > 0:
        cv2.rectangle(
            overlay,
            (traffic_light_roi["x1"], traffic_light_roi["y1"]),
            (traffic_light_roi["x2"], traffic_light_roi["y2"]),
            COLOR_TRAFFIC_LIGHT,
            2
        )
        cv2.putText(
            overlay,
            "Traffic Light ROI",
            (traffic_light_roi["x1"], traffic_light_roi["y1"] - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_TRAFFIC_LIGHT, 2
        )
    
    # Draw stop line
    cv2.line(overlay, (0, stop_line_y), (frame.shape[1], stop_line_y), COLOR_STOP_LINE, 2)
    cv2.putText(
        overlay,
        f"Stop Line (Y={stop_line_y})",
        (10, stop_line_y - 10),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_STOP_LINE, 2
    )
    
    # Draw detection zone (quadrilateral)
    if len(detection_zone_points) > 0:
        # Draw points
        for i, pt in enumerate(detection_zone_points):
            cv2.circle(overlay, pt, 8, COLOR_DETECTION_ZONE, -1)
            cv2.putText(overlay, str(i+1), (pt[0]+10, pt[1]-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_DETECTION_ZONE, 2)
        
        # Draw lines connecting points
        if len(detection_zone_points) >= 2:
            for i in range(len(detection_zone_points) - 1):
                cv2.line(overlay, detection_zone_points[i], detection_zone_points[i+1], COLOR_DETECTION_ZONE, 2)
        
        # Close the polygon if 4 points
        if len(detection_zone_points) == 4:
            cv2.line(overlay, detection_zone_points[3], detection_zone_points[0], COLOR_DETECTION_ZONE, 2)
            # Fill with semi-transparent color
            pts = np.array(detection_zone_points, np.int32)
            pts = pts.reshape((-1, 1, 2))
            overlay_fill = overlay.copy()
            cv2.fillPoly(overlay_fill, [pts], COLOR_DETECTION_ZONE)
            overlay = cv2.addWeighted(overlay, 0.7, overlay_fill, 0.3, 0)
            cv2.putText(overlay, "Detection Zone", (detection_zone_points[0][0], detection_zone_points[0][1] - 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_DETECTION_ZONE, 2)
    
    return overlay


def draw_help(frame):
    """Draw help text overlay"""
    h, w = frame.shape[:2]
    
    # Semi-transparent background for help
    help_bg = frame.copy()
    cv2.rectangle(help_bg, (10, 10), (380, 220), (0, 0, 0), -1)
    frame = cv2.addWeighted(frame, 0.7, help_bg, 0.3, 0)
    
    # Help text
    lines = [
        f"Mode: {current_mode.upper()}",
        "",
        "Hotkeys:",
        "  T - Mode: Traffic Light ROI",
        "  L - Mode: Stop Line",
        "  D - Mode: Detection Zone (4 points)",
        "  S - Save config",
        "  R - Reset all",
        "  Q - Quit",
        "",
        "Mouse: Click & drag / Click points"
    ]
    
    y_offset = 30
    for line in lines:
        if "Traffic" in line:
            color = COLOR_TRAFFIC_LIGHT
        elif "Stop" in line:
            color = COLOR_STOP_LINE
        elif "Detection" in line:
            color = COLOR_DETECTION_ZONE
        else:
            color = COLOR_HELP
        if line.startswith("Mode:"):
            if current_mode == "traffic_light":
                color = COLOR_TRAFFIC_LIGHT
            elif current_mode == "stop_line":
                color = COLOR_STOP_LINE
            else:
                color = COLOR_DETECTION_ZONE
        cv2.putText(frame, line, (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        y_offset += 18
    
    return frame


def save_config(camera_id="default"):
    """Save ROI config to JSON file"""
    global traffic_light_roi, stop_line_y, frame_width, frame_height, detection_zone_points
    
    # Load existing config or create new
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
    
    # Convert detection zone points to list format
    zone_points = [[pt[0], pt[1]] for pt in detection_zone_points] if detection_zone_points else []
    
    # Update config for this camera (include frame dimensions for scaling)
    config[camera_id] = {
        "frame_width": frame_width,
        "frame_height": frame_height,
        "stop_line": {
            "y": stop_line_y,
            "tolerance": 30,
            "violation_direction": "above"  # "below" = xe vượt xuống dưới vạch, "above" = xe vượt lên trên vạch
        },
        "traffic_light_roi": traffic_light_roi.copy(),
        "detection_zone": zone_points,  # 4 điểm tứ giác [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        "color_detection": {
            "red_lower1": [0, 100, 100],
            "red_upper1": [10, 255, 255],
            "red_lower2": [160, 100, 100],
            "red_upper2": [180, 255, 255],
            "green_lower": [40, 100, 100],
            "green_upper": [80, 255, 255],
            "yellow_lower": [20, 100, 100],
            "yellow_upper": [35, 255, 255]
        }
    }
    
    # Save
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n{'='*50}")
    print(f"✅ Config saved to: {CONFIG_FILE}")
    print(f"   Camera ID: {camera_id}")
    print(f"   Frame Size: {frame_width}x{frame_height}")
    print(f"   Stop Line Y: {stop_line_y}")
    print(f"   Traffic Light ROI: {traffic_light_roi}")
    print(f"   Detection Zone: {len(zone_points)} points")
    print(f"{'='*50}\n")


def load_existing_config(camera_id="default"):
    """Load existing config if available"""
    global traffic_light_roi, stop_line_y, detection_zone_points
    
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:   
            config = json.load(f)
        
        if camera_id in config:
            cam_config = config[camera_id]
            if "stop_line" in cam_config:
                stop_line_y = cam_config["stop_line"].get("y", 400)
            if "traffic_light_roi" in cam_config:
                traffic_light_roi.update(cam_config["traffic_light_roi"])
            if "detection_zone" in cam_config:
                zone = cam_config["detection_zone"]
                detection_zone_points = [(pt[0], pt[1]) for pt in zone] if zone else []
            print(f"[INFO] Loaded existing config for camera: {camera_id}")


def main():
    global current_mode, traffic_light_roi, stop_line_y, detection_zone_points
    
    parser = argparse.ArgumentParser(description='ROI Configuration Tool')
    parser.add_argument('--video', type=str, default=DEFAULT_VIDEO, help='Path to video file')
    parser.add_argument('--camera', type=str, default='default', help='Camera ID for config')
    parser.add_argument('--frame', type=int, default=100, help='Frame number to use')
    args = parser.parse_args()
    
    # Open video
    print(f"\n[INFO] Opening video: {args.video}")
    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        print(f"Error: Cannot open video: {args.video}")
        return
    
    # Seek to specified frame
    cap.set(cv2.CAP_PROP_POS_FRAMES, args.frame)
    ret, frame = cap.read()
    if not ret:
        print("Error: Cannot read frame")
        cap.release()
        return
    
    # Get frame dimensions - update global variables
    global frame_width, frame_height
    h, w = frame.shape[:2]
    frame_width = w
    frame_height = h
    print(f"[INFO] Frame size: {w}x{h}")
    
    # Load existing config
    load_existing_config(args.camera)
    
    # Create window
    window_name = "ROI Configuration Tool"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, min(w, 1280), min(h, 720))
    cv2.setMouseCallback(window_name, mouse_callback)
    
    print("\n" + "="*50)
    print("ROI Configuration Tool")
    print("="*50)
    print("Instructions:")
    print("  1. Press 'T' to draw Traffic Light ROI")
    print("  2. Press 'L' to set Stop Line position")
    print("  3. Press 'D' to draw Detection Zone (4 points)")
    print("  4. Press 'S' to save config")
    print("  5. Press 'Q' to quit")
    print("="*50 + "\n")
    
    while True:
        # Draw overlay
        display = draw_overlay(frame.copy())
        display = draw_help(display)
        
        # Show
        cv2.imshow(window_name, display)
        
        # Handle keys
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q') or key == 27:  # Q or ESC
            break
        
        elif key == ord('t'):
            current_mode = "traffic_light"
            print("[MODE] Traffic Light ROI - Click and drag to draw rectangle")
        
        elif key == ord('l'):
            current_mode = "stop_line"
            print("[MODE] Stop Line - Click to set Y position")
        
        elif key == ord('d'):
            current_mode = "detection_zone"
            detection_zone_points = []  # Reset points
            print("[MODE] Detection Zone - Click 4 points to draw quadrilateral")
        
        elif key == ord('s'):
            save_config(args.camera)
        
        elif key == ord('r'):
            traffic_light_roi = {"x1": 0, "y1": 0, "x2": 0, "y2": 0}
            stop_line_y = 400
            detection_zone_points = []
            print("[RESET] All ROI values reset")
        
        elif key == ord('n'):
            # Next frame
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()
        
        elif key == ord('p'):
            # Previous frame
            pos = cap.get(cv2.CAP_PROP_POS_FRAMES)
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, pos - 2))
            ret, frame = cap.read()
    
    cap.release()
    cv2.destroyAllWindows()
    print("\n[INFO] ROI Configuration Tool closed")


if __name__ == "__main__":
    main()
