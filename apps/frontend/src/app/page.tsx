"use client";

import { useEffect, useState, useRef } from "react";
import styles from "./page.module.css";
import {
  CameraViewer,
  StatsCard,
  ViolationCard,
  VideoSourceList,
} from "@/components";
import { Violation, Stats } from "@/types";

export default function Home() {
  const [violations, setViolations] = useState<Violation[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Fetch functions
  const fetchViolations = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/violations?limit=20`);
      const data = await response.json();
      setViolations(data.violations || []);
    } catch (error) {
      console.error("Error fetching violations:", error);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/stats`);
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error("Error fetching stats:", error);
    }
  };

  // Initial fetch and polling
  useEffect(() => {
    fetchViolations();
    fetchStats();

    const violationsInterval = setInterval(fetchViolations, 3000);
    const statsInterval = setInterval(fetchStats, 10000);

    return () => {
      clearInterval(violationsInterval);
      clearInterval(statsInterval);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // WebSocket for real-time violation updates
  useEffect(() => {
    const wsUrl = apiUrl.replace("http", "ws") + "/ws";
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("WebSocket connected");
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "init") {
          if (data.violations) {
            setViolations((prev) => [...data.violations, ...prev].slice(0, 50));
          }
        } else {
          setViolations((prev) => [data, ...prev].slice(0, 50));
          fetchStats();
        }
      } catch (error) {
        console.error("Error parsing WebSocket message:", error);
      }
    };

    ws.onerror = () => setIsConnected(false);
    ws.onclose = () => {
      setIsConnected(false);
      setTimeout(() => console.log("Attempting to reconnect..."), 3000);
    };

    return () => ws.close();
  }, [apiUrl]);

  return (
    <div className={styles.container}>
      {/* Header */}
      <header className={styles.header}>
        <h1>🛵 Hệ Thống Giám Sát Vi Phạm Mũ Bảo Hiểm</h1>
        <div className={styles.connectionStatus}>
          <span
            className={isConnected ? styles.connected : styles.disconnected}
          >
            {isConnected ? "● Kết nối" : "○ Mất kết nối"}
          </span>
        </div>
      </header>

      {/* Statistics */}
      {stats && (
        <div className={styles.statsContainer}>
          <StatsCard value={stats.total_violations} label="Tổng vi phạm" />
          <StatsCard value={stats.violations_today} label="Vi phạm hôm nay" />
          <StatsCard
            value={stats.violations_last_hour}
            label="Vi phạm 1 giờ qua"
          />
        </div>
      )}

      {/* Video Sources */}
      <VideoSourceList apiUrl={apiUrl} />

      {/* Live Camera View */}
      <CameraViewer apiUrl={apiUrl} />

      {/* Violations List */}
      <div className={styles.violationsContainer}>
        <h2>Vi phạm gần đây</h2>
        {violations.length === 0 ? (
          <div className={styles.noViolations}>
            <p>Chưa có vi phạm nào được phát hiện</p>
          </div>
        ) : (
          <div className={styles.violationsList}>
            {violations.map((violation) => (
              <ViolationCard
                key={violation.violation_id}
                violation={violation}
                apiUrl={apiUrl}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
