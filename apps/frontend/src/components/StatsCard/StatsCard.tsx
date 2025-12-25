import styles from "./StatsCard.module.css";

interface StatsCardProps {
  value: number;
  label: string;
}

export function StatsCard({ value, label }: StatsCardProps) {
  return (
    <div className={styles.card}>
      <div className={styles.value}>{value}</div>
      <div className={styles.label}>{label}</div>
    </div>
  );
}
