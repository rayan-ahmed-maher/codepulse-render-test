"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Terminal as TerminalIcon, X, Minimize2, Maximize2, Copy, Check } from "lucide-react";

export default function TerminalOverlay({ logs = [], isOpen, onToggle }) {
  const scrollRef = useRef(null);
  const [copied, setCopied] = useState(false);
  const [isMaximized, setIsMaximized] = useState(false);

  // Ctrl + ~ toggle
  useEffect(() => {
    const handler = (e) => {
      if (e.ctrlKey && e.key === "`") {
        e.preventDefault();
        onToggle?.();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onToggle]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [logs]);

  const getLineColor = (line) => {
    if (!line || typeof line !== "string") return "var(--text-secondary)";
    if (line.includes("ERROR") || line.includes("✗") || line.includes("FAIL")) return "#ef4444";
    if (line.includes("WARN") || line.includes("⚠")) return "#f59e0b";
    if (line.includes("SUCCESS") || line.includes("✓") || line.includes("DONE") || line.includes("READY")) return "#10b981";
    if (line.includes("INFO") || line.includes("→")) return "#06b6d4";
    if (line.startsWith("$") || line.startsWith(">")) return "#818cf8";
    return "rgba(255,255,255,0.5)";
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(logs.filter(l => typeof l === "string").join("\n"));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 40 }}
          transition={{ type: "spring", stiffness: 200, damping: 22 }}
          style={{
            position: "fixed",
            bottom: 0, left: 0, right: 0,
            height: isMaximized ? "100vh" : "45vh",
            zIndex: 9999,
            display: "flex",
            flexDirection: "column",
            background: "rgba(5, 5, 12, 0.92)",
            backdropFilter: "blur(20px)",
            borderTop: "1px solid rgba(99, 102, 241, 0.15)",
            boxShadow: "0 -10px 60px rgba(0, 0, 0, 0.6)",
            transition: "height 0.3s ease",
          }}
        >
          {/* Header */}
          <div style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "10px 20px", borderBottom: "1px solid rgba(255,255,255,0.05)",
            background: "rgba(0,0,0,0.3)", flexShrink: 0,
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{ display: "flex", gap: 6 }}>
                <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#ef4444" }} />
                <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#f59e0b" }} />
                <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#10b981" }} />
              </div>
              <span style={{ fontSize: "0.75rem", color: "var(--text-tertiary)", fontWeight: 600 }}>
                <TerminalIcon size={12} style={{ marginRight: 4, verticalAlign: "middle" }} />
                autodeploy — cinematic terminal
              </span>
              <span style={{ fontSize: "0.6rem", color: "rgba(99, 102, 241, 0.5)", fontFamily: "monospace" }}>
                Ctrl + ` to toggle
              </span>
            </div>

            <div style={{ display: "flex", gap: 4 }}>
              <button onClick={handleCopy} className="btn btn-ghost btn-sm" style={{ padding: "4px 8px" }} title="Copy logs">
                {copied ? <Check size={12} /> : <Copy size={12} />}
              </button>
              <button onClick={() => setIsMaximized(!isMaximized)} className="btn btn-ghost btn-sm" style={{ padding: "4px 8px" }} title="Maximize">
                {isMaximized ? <Minimize2 size={12} /> : <Maximize2 size={12} />}
              </button>
              <button onClick={onToggle} className="btn btn-ghost btn-sm" style={{ padding: "4px 8px" }} title="Close">
                <X size={12} />
              </button>
            </div>
          </div>

          {/* Log Content */}
          <div
            ref={scrollRef}
            style={{
              flex: 1, padding: "12px 20px", overflowY: "auto",
              fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
              fontSize: "0.78rem", lineHeight: 1.8,
            }}
          >
            {logs.length === 0 ? (
              <div style={{ color: "var(--text-tertiary)", fontStyle: "italic", padding: "20px 0", textAlign: "center" }}>
                Awaiting build output... Deploy a project to see real-time logs here.
              </div>
            ) : (
              logs.filter(l => typeof l === "string").map((line, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -6 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.1, delay: Math.min(i * 0.01, 0.5) }}
                  style={{ color: getLineColor(line), whiteSpace: "pre-wrap", wordBreak: "break-all" }}
                >
                  <span style={{ color: "rgba(255,255,255,0.15)", marginRight: 12, userSelect: "none", fontVariantNumeric: "tabular-nums" }}>
                    {String(i + 1).padStart(3, " ")}
                  </span>
                  {line}
                </motion.div>
              ))
            )}

            {logs.length > 0 && (
              <motion.span
                animate={{ opacity: [1, 0, 1] }}
                transition={{ duration: 1, repeat: Infinity }}
                style={{
                  display: "inline-block", width: 8, height: 16,
                  background: "var(--color-electric-indigo)",
                  marginLeft: 4, verticalAlign: "middle",
                }}
              />
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
