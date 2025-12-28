"use client";

import { useEffect, useState } from "react";
import styles from "./VideoSourceList.module.css";

interface VideoSource {
  id: string;
  filename: string;
  path: string;
  size_mb: number;
  camera_id: string;
}

interface VideoSourceListProps {
  apiUrl: string;
}

export function VideoSourceList({ apiUrl }: VideoSourceListProps) {
  const [videos, setVideos] = useState<VideoSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchVideos = async () => {
      try {
        const response = await fetch(`${apiUrl}/api/videos`);
        const data = await response.json();
        setVideos(data.videos || []);
        setError(data.error || null);
      } catch (err) {
        setError("Không thể tải danh sách video");
        console.error("Error fetching videos:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchVideos();
  }, [apiUrl]);

  if (loading) {
    return (
      <div className={styles.container}>
        <h3>📁 Nguồn Video Có Sẵn</h3>
        <div className={styles.loading}>Đang tải...</div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <h3>📁 Nguồn Video Có Sẵn ({videos.length})</h3>

      {error && <div className={styles.error}>{error}</div>}

      {videos.length === 0 ? (
        <div className={styles.empty}>
          <p>Chưa có video nào trong thư mục</p>
          <p className={styles.hint}>Thêm video vào thư mục data/video/</p>
        </div>
      ) : (
        <div className={styles.videoList}>
          {videos.map((video) => (
            <div key={video.id} className={styles.videoItem}>
              <div className={styles.videoIcon}>🎬</div>
              <div className={styles.videoInfo}>
                <span className={styles.videoName}>{video.filename}</span>
                <span className={styles.videoMeta}>
                  Camera: {video.camera_id} • {video.size_mb} MB
                </span>
              </div>
              <div className={styles.status}>Sẵn sàng</div>
            </div>
          ))}
        </div>
      )}

      <div className={styles.footer}>
        <p>
          💡 Trigger DAG &quot;violation_demo_streaming&quot; để stream tất cả
          video
        </p>
      </div>
    </div>
  );
}
