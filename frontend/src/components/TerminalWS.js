"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Terminal as TerminalIcon, Copy, Trash2, Check, Wifi, WifiOff, RefreshCw } from "lucide-react";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
const MAX_RECONNECT_ATTEMPTS = 5;

// ── Log level config ─────────────────────────────────
const LEVEL_CONFIG = {
  INFO:    { color: "#00F5FF", prefix: "→" },
  SUCCESS: { color: "#00FF88", prefix: "✓" },
  WARNING: { color: "#FFD700", prefix: "⚠" },
  ERROR:   { color: "#FF3B3B", prefix: "❌" },
};

export default function TerminalWS({ sessionId = "default", title = "Build Terminal" }) {
  const [logs, setLogs] = useState([]);
  const [status, setStatus] = useState("disconnected"); // connected | reconnecting | disconnected
  const [copied, setCopied] = useState(false);
  const scrollRef = useRef(null);
  const wsRef = useRef(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef(null);

  // ── Auto scroll ────────────────────────────────────
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  // ── WebSocket Connection ───────────────────────────
  const connect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;

    const url = `${WS_BASE}/ws/terminal/${sessionId}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("connected");
      reconnectAttemptRef.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        // Handle different message types
        if (data.type === "history") {
          // Replay stored logs on reconnect
          setLogs((prev) => {
            const existing = new Set(prev.map((l) => l.timestamp + l.message));
            const newLogs = (data.logs || []).filter(
              (l) => !existing.has(l.timestamp + l.message)
            );
            return [...prev, ...newLogs];
          });
        } else if (data.type === "status") {
          // Connection confirmation — no action needed
        } else if (data.type === "pong") {
          // Keepalive response — no action needed
        } else if (data.type === "cleared") {
          setLogs([]);
        } else if (data.level && data.message) {
          // Real log event — append immediately (NEVER buffer)
          setLogs((prev) => [...prev, data]);
        }
      } catch {
        // Raw text — treat as INFO
        setLogs((prev) => [...prev, {
          timestamp: new Date().toISOString(),
          level: "INFO",
          message: event.data,
        }]);
      }
    };

    ws.onclose = () => {
      setStatus("disconnected");
      attemptReconnect();
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [sessionId]);

  // ── Auto-Reconnect with Exponential Backoff ────────
  const attemptReconnect = useCallback(() => {
    if (reconnectAttemptRef.current >= MAX_RECONNECT_ATTEMPTS) {
      setStatus("disconnected");
      // Sentry error event if available
      if (typeof window !== "undefined" && window.Sentry) {
        window.Sentry.captureMessage(
          `WebSocket terminal failed after ${MAX_RECONNECT_ATTEMPTS} reconnect attempts`,
          "error"
        );
      }
      return;
    }

    setStatus("reconnecting");
    reconnectAttemptRef.current += 1;
    const delay = Math.min(1000 * Math.pow(2, reconnectAttemptRef.current), 30000);

    reconnectTimerRef.current = setTimeout(() => {
      connect();
    }, delay);
  }, [connect]);

  // ── Connect on mount ───────────────────────────────
  useEffect(() => {
    connect();

    // Keepalive ping every 25 seconds
    const pingInterval = setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "ping" }));
      }
    }, 25000);

    return () => {
      clearInterval(pingInterval);
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connect]);

  // ── Actions ────────────────────────────────────────
  const handleCopy = () => {
    const text = logs.map((l) => {
      const cfg = LEVEL_CONFIG[l.level] || LEVEL_CONFIG.INFO;
      const ts = l.timestamp ? new Date(l.timestamp).toLocaleTimeString() : "";
      return `[${ts}] ${cfg.prefix} ${l.message}${l.evidence ? ` (${l.evidence})` : ""}`;
    }).join("\n");
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleClear = () => {
    setLogs([]);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "clear" }));
    }
  };

  const handleReconnect = () => {
    reconnectAttemptRef.current = 0;
    connect();
  };

  // ── Status indicator colors ────────────────────────
  const statusConfig = {
    connected:    { color: "#00FF88", label: "Connected", icon: Wifi },
    reconnecting: { color: "#FFD700", label: "Reconnecting...", icon: RefreshCw },
    disconnected: { color: "#FF3B3B", label: "Disconnected", icon: WifiOff },
  };
  const st = statusConfig[status] || statusConfig.disconnected;

  return (
    <div
      style={{
        position: "relative", overflow: "hidden", borderRadius: 12,
        boxShadow: "inset 0 2px 8px rgba(0,0,0,0.6), 0 0 30px rgba(139, 92, 246, 0.1)",
        border: "1px solid rgba(139, 92, 246, 0.15)",
      }}
    >
      {/* CRT scanline overlay */}
      <div style={{
        position: "absolute", inset: 0, zIndex: 0, pointerEvents: "none",
        background: "linear-gradient(rgba(18,16,16,0) 50%, rgba(0,0,0,0.25) 50%), linear-gradient(90deg, rgba(255,0,0,0.06), rgba(0,255,0,0.02), rgba(0,0,255,0.06))",
        backgroundSize: "100% 4px, 3px 100%", opacity: 0.3,
      }} />

      {/* Header */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "10px 16px",
        borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
        background: "#000000",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {/* macOS dots */}
          <div style={{ display: "flex", gap: 6 }}>
            <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#ef4444" }} />
            <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#f59e0b" }} />
            <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#10b981" }} />
          </div>
          <span style={{ fontSize: "0.75rem", color: "#6b7280", fontWeight: 600, marginLeft: 8 }}>
            <TerminalIcon size={12} style={{ marginRight: 4, verticalAlign: "middle" }} />
            {title}
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {/* Connection status */}
          <button
            onClick={status === "disconnected" ? handleReconnect : undefined}
            style={{
              display: "flex", alignItems: "center", gap: 4,
              fontSize: "0.62rem", color: st.color,
              background: "none", border: "none", cursor: status === "disconnected" ? "pointer" : "default",
              padding: "2px 8px", borderRadius: 12,
              border: `1px solid ${st.color}33`,
            }}
          >
            <st.icon size={10} style={status === "reconnecting" ? { animation: "spin 1s linear infinite" } : {}} />
            {st.label}
          </button>

          {/* Action buttons */}
          <button
            onClick={handleCopy}
            title="Copy All Logs"
            style={{
              padding: "4px 8px", borderRadius: 6,
              background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
              cursor: "pointer", color: "#9ca3af", display: "flex", alignItems: "center", gap: 4,
              fontSize: "0.65rem",
            }}
          >
            {copied ? <Check size={11} color="#10b981" /> : <Copy size={11} />}
            {copied ? "Copied" : "Copy"}
          </button>
          <button
            onClick={handleClear}
            title="Clear Terminal"
            style={{
              padding: "4px 8px", borderRadius: 6,
              background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
              cursor: "pointer", color: "#9ca3af", display: "flex", alignItems: "center", gap: 4,
              fontSize: "0.65rem",
            }}
          >
            <Trash2 size={11} />
            Clear
          </button>
        </div>
      </div>

      {/* Terminal Body */}
      <div
        ref={scrollRef}
        style={{
          background: "#000000",
          fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
          fontSize: "0.78rem",
          lineHeight: 1.8,
          padding: "16px",
          height: 320,
          overflowY: "auto",
          position: "relative",
          zIndex: 1,
        }}
      >
        <AnimatePresence>
          {logs.length === 0 ? (
            <div style={{ color: "#4b5563", fontStyle: "italic", textAlign: "center", padding: "40px 0" }}>
              Awaiting real-time logs...
            </div>
          ) : (
            logs.map((log, i) => {
              const cfg = LEVEL_CONFIG[log.level] || LEVEL_CONFIG.INFO;
              const timestamp = log.timestamp
                ? new Date(log.timestamp).toLocaleTimeString("en-US", {
                    hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
                  })
                : "";

              return (
                <motion.div
                  key={`${log.timestamp}-${i}`}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.1 }}
                  style={{ display: "flex", gap: 8, position: "relative", zIndex: 1 }}
                >
                  {/* Timestamp */}
                  <span style={{ color: "#4b5563", whiteSpace: "nowrap", userSelect: "none", minWidth: 70 }}>
                    {timestamp}
                  </span>
                  {/* Level prefix */}
                  <span style={{ color: cfg.color, minWidth: 16, textAlign: "center" }}>
                    {cfg.prefix}
                  </span>
                  {/* Message */}
                  <span style={{ color: cfg.color, wordBreak: "break-word" }}>
                    {log.message}
                    {log.evidence && (
                      <span style={{ color: "#6b7280", marginLeft: 8 }}>
                        ({log.evidence})
                      </span>
                    )}
                  </span>
                </motion.div>
              );
            })
          )}
        </AnimatePresence>

        {/* Blinking cursor */}
        <motion.span
          animate={{ opacity: [1, 0, 1] }}
          transition={{ duration: 1, repeat: Infinity }}
          style={{
            display: "inline-block", width: 8, height: 16,
            background: "#00F5FF", marginLeft: 4, verticalAlign: "middle",
            position: "relative", zIndex: 1,
          }}
        />
      </div>
    </div>
  );
}
