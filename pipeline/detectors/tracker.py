"""
tracker.py - Centroid-based object tracker
===========================================
Simple centroid tracking for vehicles and persons.
"""

import numpy as np
from typing import Dict, List, Tuple, Any
from .base import centroid


class CentroidTracker:
    """
    Simple centroid-based object tracker.
    Tracks objects by matching centroids between frames.
    """
    
    def __init__(self, max_dist: float = 100, ttl_sec: float = 2.0):
        """
        Args:
            max_dist: Maximum distance (pixels) to match existing track
            ttl_sec: Time-to-live in seconds before removing stale tracks
        """
        self.max_dist = max_dist
        self.ttl_sec = ttl_sec
        self.next_id = 1
        self.tracks: Dict[int, Dict] = {}
    
    def update(self, detections: List[Tuple], now_ts: float) -> Dict[int, Dict]:
        """
        Update tracks with new detections.
        
        Args:
            detections: List of (box, extra_info) tuples
                       box: [x, y, w, h]
                       extra_info: any additional data (e.g., vehicle_type)
            now_ts: Current timestamp
            
        Returns:
            Dict of track_id -> track_info
        """
        # Remove old tracks
        to_del = [tid for tid, tr in self.tracks.items() 
                  if (now_ts - tr["t"]) > self.ttl_sec]
        for tid in to_del:
            del self.tracks[tid]
        
        assigned = {}
        used_tracks = set()
        
        # Greedy assignment by nearest centroid
        for detection in detections:
            if isinstance(detection, tuple) and len(detection) >= 2:
                box, extra_info = detection[0], detection[1]
            else:
                box = detection
                extra_info = None
            
            cx, cy = centroid(box)
            best_id = None
            best_d = float('inf')
            
            for tid, tr in self.tracks.items():
                if tid in used_tracks:
                    continue
                tx, ty = tr["c"]
                d = np.sqrt((cx - tx) ** 2 + (cy - ty) ** 2)
                if d < best_d:
                    best_d = d
                    best_id = tid
            
            if best_id is not None and best_d <= self.max_dist:
                # Update existing track
                self.tracks[best_id]["c"] = (cx, cy)
                self.tracks[best_id]["t"] = now_ts
                self.tracks[best_id]["box"] = box
                assigned[best_id] = self.tracks[best_id]
                used_tracks.add(best_id)
            else:
                # Create new track
                tid = self.next_id
                self.next_id += 1
                track_info = {
                    "c": (cx, cy),
                    "t": now_ts,
                    "box": box,
                    "crossed": False,
                    "extra": extra_info
                }
                # For backward compatibility with vehicle tracking
                if isinstance(extra_info, str):
                    track_info["vehicle_type"] = extra_info
                
                self.tracks[tid] = track_info
                assigned[tid] = track_info
                used_tracks.add(tid)
        
        return assigned
    
    def reset(self):
        """Reset all tracks"""
        self.tracks = {}
        self.next_id = 1
