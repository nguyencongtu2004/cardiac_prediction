"use client";

import { useEffect, useRef, useState } from "react";
import styles from "./CameraViewer.module.css";
import { CameraFrame } from "@/types";

interface CameraViewerProps {
  apiUrl: string;
}

export function CameraViewer({ apiUrl }: CameraViewerProps) {
  const [cameras, setCameras] = useState<Record<string, CameraFrame>>({});
  const [selectedCamera, setSelectedCamera] = useState<string>("");
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const wsUrl = apiUrl.replace("http", "ws") + "/ws/camera";
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("Camera WebSocket connected");
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "frame" && data.image_base64) {
          const cameraId = data.camera_id || "unknown";
          setCameras((prev) => ({
            ...prev,
            [cameraId]: {
              camera_id: cameraId,
              timestamp: data.timestamp,
              frame_number: data.frame_number,
              image_base64: data.image_base64,
            },
          }));

          // Auto-select first camera if none selected
          setSelectedCamera((prev) => (prev === "" ? cameraId : prev));
        }
      } catch (error) {
        console.error("Error parsing camera frame:", error);
      }
    };

    ws.onerror = () => setIsConnected(false);
    ws.onclose = () => setIsConnected(false);

    return () => {
      ws.close();
    };
  }, [apiUrl]);

  const cameraList = Object.keys(cameras);
  const currentFrame = selectedCamera ? cameras[selectedCamera] : null;

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2>
          📹 Camera Trực Tiếp{" "}
          {isConnected ? (
            <span className={styles.live}>● LIVE</span>
          ) : (
            <span className={styles.offline}>○ Offline</span>
          )}
        </h2>

        {cameraList.length > 0 && (
          <div className={styles.cameraSelector}>
            <label>Chọn camera:</label>
            <select
              value={selectedCamera}
              onChange={(e) => setSelectedCamera(e.target.value)}
              className={styles.select}
            >
              {cameraList.map((camId) => (
                <option key={camId} value={camId}>
                  {camId}
                </option>
              ))}
            </select>
            <span className={styles.cameraCount}>
              ({cameraList.length} camera)
            </span>
          </div>
        )}
      </div>

      <div className={styles.viewer}>
        {currentFrame ? (
          <div className={styles.frameContainer}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={`data:image/jpeg;base64,${currentFrame.image_base64}`}
              alt={`Camera: ${selectedCamera}`}
              className={styles.frame}
            />
            <div className={styles.overlay}>
              <span className={styles.cameraId}>{selectedCamera}</span>
              <span className={styles.frameInfo}>
                Frame: {currentFrame.frame_number}
              </span>
            </div>
          </div>
        ) : (
          <div className={styles.placeholder}>
            <p>🎬 Đang chờ video stream...</p>
            <p className={styles.hint}>
              Trigger DAG &quot;violation_demo_streaming&quot; trong Airflow
            </p>
          </div>
        )}
      </div>

      {/* Camera thumbnails */}
      {cameraList.length > 1 && (
        <div className={styles.thumbnails}>
          {cameraList.map((camId) => (
            <button
              key={camId}
              className={`${styles.thumbnail} ${
                camId === selectedCamera ? styles.active : ""
              }`}
              onClick={() => setSelectedCamera(camId)}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`data:image/jpeg;base64,${cameras[camId].image_base64}`}
                alt={camId}
              />
              <span>{camId}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
