"use client";

import { useEffect, useState } from "react";
import Image from "next/image";

interface Violation {
  camera_id: string;
  timestamp: string;
  image_path: string;
  violations: {
    type: string;
    vehicle: string;
    confidence: number;
    traffic_light_state: string;
  }[];
}

export default function Dashboard() {
  const [violations, setViolations] = useState<Violation[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    // Initial fetch
    fetch("http://localhost:8000/violations")
      .then((res) => res.json())
      .then((data) => setViolations(data))
      .catch((err) => console.error("Failed to fetch initial data", err));

    // WebSocket
    const ws = new WebSocket("ws://localhost:8000/ws");

    ws.onopen = () => {
      console.log("Connected to WebSocket");
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const newViolation = JSON.parse(event.data);
        console.log("New Violation:", newViolation);
        setViolations((prev) => [newViolation, ...prev].slice(0, 50));
      } catch (e) {
        console.error("Error parsing WS message", e);
      }
    };

    ws.onclose = () => {
      console.log("Disconnected from WebSocket");
      setIsConnected(false);
    };

    return () => {
      ws.close();
    };
  }, []);

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <header className="flex justify-between items-center mb-8 border-b border-gray-700 pb-4">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
            Traffic Monitoring Dashboard
          </h1>
          <p className="text-gray-400 text-sm mt-1">
            Real-time Violation Detection System
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`w-3 h-3 rounded-full ${
              isConnected ? "bg-green-500 animate-pulse" : "bg-red-500"
            }`}
          ></span>
          <span className="text-sm font-medium">
            {isConnected ? "System Online" : "Disconnected"}
          </span>
        </div>
      </header>

      <main className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Stats & Live View Placeholder */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 shadow-xl">
            <h2 className="text-xl font-semibold mb-4 text-blue-300">
              Statistics (Session)
            </h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gray-700/50 p-4 rounded-lg text-center">
                <p className="text-3xl font-bold text-red-500">
                  {violations.length}
                </p>
                <p className="text-gray-400 text-xs uppercase tracking-wider mt-1">
                  Total Violations
                </p>
              </div>
              <div className="bg-gray-700/50 p-4 rounded-lg text-center">
                <p className="text-3xl font-bold text-yellow-500">
                  {new Set(violations.map((v) => v.camera_id)).size}
                </p>
                <p className="text-gray-400 text-xs uppercase tracking-wider mt-1">
                  Active Cameras
                </p>
              </div>
            </div>
          </div>

          <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 h-64 flex items-center justify-center relative overflow-hidden group">
            <div className="absolute inset-0 bg-blue-500/10 group-hover:bg-blue-500/20 transition-colors"></div>
            <div className="text-center z-10">
              <svg
                className="w-12 h-12 text-gray-500 mx-auto mb-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                ></path>
              </svg>
              <p className="text-gray-400">Select a camera to view live feed</p>
              <p className="text-xs text-gray-600 mt-1">
                (Mock Feed Placeholder)
              </p>
            </div>
          </div>
        </div>

        {/* Right Column: Violation Feed */}
        <div className="lg:col-span-2">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <span className="text-red-400">Live Alerts</span>
            <span className="text-xs bg-red-500/20 text-red-400 px-2 py-0.5 rounded-full animate-pulse">
              LIVE
            </span>
          </h2>

          <div className="space-y-4 max-h-[80vh] overflow-y-auto pr-2 custom-scrollbar">
            {violations.length === 0 ? (
              <div className="text-center py-20 bg-gray-800/50 rounded-xl border border-dashed border-gray-700">
                <p className="text-gray-500">Waiting for violations...</p>
              </div>
            ) : (
              violations.map((v, idx) => (
                <div
                  key={idx}
                  className="bg-gray-800 rounded-xl p-4 border border-gray-700 shadow-lg flex gap-4 transition-all hover:border-gray-600 hover:shadow-xl animate-in slide-in-from-right fade-in duration-300"
                >
                  <div className="relative w-48 h-32 flex-shrink-0 bg-gray-900 rounded-lg overflow-hidden border border-gray-700">
                    {/* Image Placeholder - In production, serve actual image via backend static file server */}
                    <div className="absolute inset-0 flex items-center justify-center text-gray-600 text-xs">
                      {v.image_path.split("/").pop()}
                    </div>
                  </div>

                  <div className="flex-1">
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="text-xs text-blue-400 font-semibold uppercase tracking-wider mb-1">
                          {v.camera_id}
                        </p>
                        <h3 className="font-bold text-lg text-white">
                          {v.violations
                            .map((d) => d.type.replace(/_/g, " "))
                            .join(", ")}
                        </h3>
                      </div>
                      <span className="text-xs text-gray-400 font-mono">
                        {new Date(v.timestamp).toLocaleTimeString()}
                      </span>
                    </div>

                    <div className="mt-3 flex flex-wrap gap-2">
                      {v.violations.map((detail, i) => (
                        <span
                          key={i}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-red-500/10 text-red-400 text-xs font-medium border border-red-500/20"
                        >
                          {detail.vehicle} (
                          {(detail.confidence * 100).toFixed(0)}%)
                        </span>
                      ))}
                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium border ${
                          v.violations[0]?.traffic_light_state === "RED"
                            ? "bg-red-900/30 text-red-200 border-red-800"
                            : "bg-gray-700 text-gray-300 border-gray-600"
                        }`}
                      >
                        🚦 Signal:{" "}
                        {v.violations[0]?.traffic_light_state || "UNKNOWN"}
                      </span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
