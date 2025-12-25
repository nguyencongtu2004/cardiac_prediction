"""
Video service for handling video file operations
"""
import os
import glob
from config import VIDEO_DIR


def get_available_videos():
    """Get list of available video files that can be used for streaming"""
    videos = []
    
    if not os.path.isdir(VIDEO_DIR):
        return {
            "videos": [],
            "video_dir": VIDEO_DIR,
            "error": f"Directory not found: {VIDEO_DIR}"
        }
    
    # Scan for video files
    video_extensions = ['*.mp4', '*.avi', '*.mkv', '*.mov']
    for pattern in video_extensions:
        for video_path in glob.glob(os.path.join(VIDEO_DIR, pattern)):
            filename = os.path.basename(video_path)
            name_without_ext = os.path.splitext(filename)[0]
            
            # Get file stats
            try:
                stat = os.stat(video_path)
                size_mb = stat.st_size / (1024 * 1024)
            except Exception:
                size_mb = 0
            
            videos.append({
                "id": name_without_ext,
                "filename": filename,
                "path": video_path,
                "size_mb": round(size_mb, 2),
                "camera_id": name_without_ext
            })
    
    # Sort by filename
    videos.sort(key=lambda x: x['filename'])
    
    return {
        "videos": videos,
        "count": len(videos),
        "video_dir": VIDEO_DIR
    }
