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
      // Handle both helmet and redlight violation paths
      const filename = violation.image_path.split("/").pop();
      const subdir =
        violation.violation_type === "RED_LIGHT" ? "redlight/" : "";
      return `${apiUrl}/violations/${subdir}${filename}`;
    }
    return null;
  };

  const imageSrc = getImageSrc();

  // Determine violation type display
  const isRedLight = violation.violation_type === "RED_LIGHT";
  const badgeText = isRedLight ? "🚦 Vượt đèn đỏ" : "🚫 Không đội MBH";
  const badgeClass = isRedLight ? styles.badgeRedlight : styles.badge;

  return (
    <div className={`${styles.card} ${isRedLight ? styles.cardRedlight : ""}`}>
      <div className={styles.image}>
        {imageSrc ? (
          <a
            href={imageSrc}
            target="_blank"
            rel="noopener noreferrer"
            className={styles.imageLink}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={imageSrc} alt={`Violation ${violation.violation_id}`} />
          </a>
        ) : (
          <span className={styles.noImage}>Không có hình ảnh</span>
        )}
      </div>

      <div className={styles.details}>
        <div className={styles.header}>
          <span className={badgeClass}>{badgeText}</span>
          <span className={styles.camera}>{violation.camera_id}</span>
        </div>

        <div className={styles.time}>🕒 {formatTime(violation.timestamp)}</div>

        <div className={styles.info}>
          <span>Track ID: {violation.track_id}</span>
          <span>
            Độ tin cậy: {((violation.confidence || 0) * 100).toFixed(1)}%
          </span>
          {isRedLight && violation.vehicle_type && (
            <span>Loại xe: {violation.vehicle_type}</span>
          )}
          {isRedLight && violation.traffic_light_state && (
            <span>Đèn: {violation.traffic_light_state}</span>
          )}
        </div>

        <div className={styles.metadata}>
          {isRedLight ? (
            // Red light violation metadata
            <>
              <span className={styles.detected}>
                🚗 {violation.vehicle_type || "Xe"}
              </span>
              <span
                className={
                  violation.traffic_light_state === "RED"
                    ? styles.notDetected
                    : styles.detected
                }
              >
                🚦 {violation.traffic_light_state || "UNKNOWN"}
              </span>
            </>
          ) : (
            // Helmet violation metadata
            <>
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
            </>
          )}
        </div>
      </div>
    </div>
  );
}
