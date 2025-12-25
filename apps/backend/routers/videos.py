"""
Video routes for the API
"""
from fastapi import APIRouter
from services.video import get_available_videos

router = APIRouter(prefix="/api", tags=["videos"])


@router.get("/videos")
def list_videos():
    """Get list of available video files that can be used for streaming"""
    return get_available_videos()
