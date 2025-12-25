import styles from "./ViolationCard.module.css";
import { Violation } from "@/types";

interface ViolationCardProps {
  violation: Violation;
  apiUrl: string;
}

export function ViolationCard({ violation, apiUrl }: ViolationCardProps) {
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString("vi-VN");
  };

  const getImageSrc = () => {
    if (violation.image_base64) {
      return `data:image/jpeg;base64,${violation.image_base64}`;
    }
    if (violation.image_path) {
      return `${apiUrl}/violations/${violation.image_path.split("/").pop()}`;
    }
    return null;
  };

  const imageSrc = getImageSrc();

  return (
    <div className={styles.card}>
      <div className={styles.image}>
        {imageSrc ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={imageSrc} alt={`Violation ${violation.violation_id}`} />
        ) : (
          <span className={styles.noImage}>Không có hình ảnh</span>
        )}
      </div>

      <div className={styles.details}>
        <div className={styles.header}>
          <span className={styles.badge}>🚫 Không đội MBH</span>
          <span className={styles.camera}>{violation.camera_id}</span>
        </div>

        <div className={styles.time}>🕒 {formatTime(violation.timestamp)}</div>

        <div className={styles.info}>
          <span>Track ID: {violation.track_id}</span>
          <span>Độ tin cậy: {(violation.confidence * 100).toFixed(1)}%</span>
        </div>

        <div className={styles.metadata}>
          <span
            className={
              violation.metadata?.person_detected
                ? styles.detected
                : styles.notDetected
            }
          >
            👤 Người
          </span>
          <span
            className={
              violation.metadata?.motorbike_detected
                ? styles.detected
                : styles.notDetected
            }
          >
            🏍️ Xe máy
          </span>
          <span
            className={
              violation.metadata?.helmet_detected
                ? styles.detected
                : styles.notDetected
            }
          >
            ⛑️ Mũ BH
          </span>
        </div>
      </div>
    </div>
  );
}
