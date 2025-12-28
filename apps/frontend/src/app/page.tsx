"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import styles from "./page.module.css";
import {
  CameraViewer,
  StatsCard,
  ViolationCard,
  VideoSourceList,
} from "@/components";
import { Violation, Stats } from "@/types";

// Extended stats type to include redlight
interface CombinedStats extends Stats {
  redlight_total?: number;
  redlight_today?: number;
  redlight_last_hour?: number;
}

// Helper to normalize violation_type from backend (red_light, no_helmet) to UI format (RED_LIGHT, HELMET)
const normalizeViolationType = (
  rawType: string | undefined,
  isRedlightEndpoint: boolean = false
): string => {
  const upperType = rawType?.toUpperCase() || "";
  if (
    upperType === "RED_LIGHT" ||
    upperType.includes("RED") ||
    isRedlightEndpoint
  ) {
    return "RED_LIGHT";
  }
  return "HELMET";
};

export default function Home() {
  const [violations, setViolations] = useState<Violation[]>([]);
  const [stats, setStats] = useState<CombinedStats | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  // Track violations received from WebSocket that might not be in API yet
  const wsViolationsRef = useRef<Map<string, Violation>>(new Map());
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Merge WS violations with API violations
  const mergeViolations = useCallback(
    (apiViolations: Violation[]): Violation[] => {
      const apiViolationIds = new Set(apiViolations.map((v) => v.violation_id));

      // Get WS violations that are NOT in the API response yet
      const wsOnlyViolations: Violation[] = [];
      wsViolationsRef.current.forEach((violation, id) => {
        if (!apiViolationIds.has(id)) {
          wsOnlyViolations.push(violation);
        } else {
          // If it's now in API, remove from WS tracking
          wsViolationsRef.current.delete(id);
        }
      });

      // Combine: WS-only violations first (newest), then API violations
      const combined = [...wsOnlyViolations, ...apiViolations]
        .sort(
          (a, b) =>
            new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
        )
        .slice(0, 50);

      return combined;
    },
    []
  );

  // Fetch both helmet and redlight violations
  const fetchViolations = useCallback(async () => {
    try {
      // Fetch helmet violations
      const helmetRes = await fetch(`${apiUrl}/api/violations?limit=20`);
      const helmetData = await helmetRes.json();
      const helmetViolations = (helmetData.violations || []).map(
        (v: Violation) => ({
          ...v,
          violation_type: normalizeViolationType(v.violation_type, false),
        })
      );

      // Fetch redlight violations
      const redlightRes = await fetch(
        `${apiUrl}/api/redlight-violations?limit=20`
      );
      const redlightData = await redlightRes.json();
      const redlightViolations = (redlightData.violations || []).map(
        (v: Violation) => ({
          ...v,
          violation_type: normalizeViolationType(v.violation_type, true),
        })
      );

      // Combine API results
      const apiCombined = [...helmetViolations, ...redlightViolations].sort(
        (a, b) =>
          new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      );

      // Merge with WS violations that might not be in API yet
      const merged = mergeViolations(apiCombined);
      setViolations(merged);
    } catch (error) {
      console.error("Error fetching violations:", error);
    }
  }, [apiUrl, mergeViolations]);

  // Fetch combined stats
  const fetchStats = useCallback(async () => {
    try {
      // Fetch helmet stats
      const helmetRes = await fetch(`${apiUrl}/api/stats`);
      const helmetStats = await helmetRes.json();

      // Fetch redlight stats
      let redlightStats = {
        total_violations: 0,
        violations_today: 0,
        violations_last_hour: 0,
      };
      try {
        const redlightRes = await fetch(`${apiUrl}/api/redlight-stats`);
        redlightStats = await redlightRes.json();
      } catch {
        console.log("Redlight stats not available yet");
      }

      // Combine stats
      setStats({
        total_violations:
          (helmetStats.total_violations || 0) +
          (redlightStats.total_violations || 0),
        violations_today:
          (helmetStats.violations_today || 0) +
          (redlightStats.violations_today || 0),
        violations_last_hour:
          (helmetStats.violations_last_hour || 0) +
          (redlightStats.violations_last_hour || 0),
        by_camera: helmetStats.by_camera || [],
        redlight_total: redlightStats.total_violations || 0,
        redlight_today: redlightStats.violations_today || 0,
        redlight_last_hour: redlightStats.violations_last_hour || 0,
      });
    } catch (error) {
      console.error("Error fetching stats:", error);
    }
  }, [apiUrl]);

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
  }, [fetchViolations, fetchStats]);

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
            // Track init violations in WS ref
            data.violations.forEach((v: Violation) => {
              if (v.violation_id) {
                wsViolationsRef.current.set(v.violation_id, v);
              }
            });
            setViolations((prev) => [...data.violations, ...prev].slice(0, 50));
          }
        } else {
          // Handle both helmet and redlight violations from WebSocket
          const isRedlight = data.type === "redlight";
          const violation: Violation = {
            ...data,
            violation_type: normalizeViolationType(
              data.violation_type,
              isRedlight
            ),
          };

          // Track this WS violation so it won't be lost during API fetch
          if (violation.violation_id) {
            wsViolationsRef.current.set(violation.violation_id, violation);
            console.log(
              `[WS] Tracked new violation: ${violation.violation_id}`
            );
          }

          setViolations((prev) => [violation, ...prev].slice(0, 50));
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
  }, [apiUrl, fetchStats]);

  return (
    <div className={styles.container}>
      {/* Header */}
      <header className={styles.header}>
        <h1>🚦 Hệ Thống Giám Sát Vi Phạm Giao Thông</h1>
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
          <StatsCard value={stats.redlight_total || 0} label="🚦 Vượt đèn đỏ" />
        </div>
      )}

      {/* Main Content - Two Column Layout */}
      <div className={styles.mainContent}>
        {/* Left Column - Camera */}
        <div className={styles.leftColumn}>
          {/* Video Sources */}
          <VideoSourceList apiUrl={apiUrl} />

          {/* Live Camera View */}
          <CameraViewer apiUrl={apiUrl} />
        </div>

        {/* Right Column - Violations (Scrollable) */}
        <div className={styles.rightColumn}>
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
                    key={
                      violation.violation_id +
                      violation.violation_type +
                      violation.timestamp
                    }
                    violation={violation}
                    apiUrl={apiUrl}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
