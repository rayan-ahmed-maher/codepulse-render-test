"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Terminal as TerminalIcon, Copy, Trash2, Check } from "lucide-react";

export default function Terminal({ logs = [], title = "Build Output" }) {
  const scrollRef = useRef(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  const getLineColor = (line) => {
    if (!line || typeof line !== "string") return "var(--text-secondary)";
    if (line.includes("ERROR") || line.includes("✗") || line.includes("FAIL"))
      return "var(--color-rose-danger)";
    if (line.includes("WARN") || line.includes("⚠"))
      return "var(--color-amber-warning)";
    if (line.includes("SUCCESS") || line.includes("✓") || line.includes("DONE") || line.includes("READY"))
      return "var(--color-emerald-neon)";
    if (line.includes("INFO") || line.includes("→"))
      return "var(--color-cyan-info)";
    if (line.startsWith("$") || line.startsWith(">"))
      return "var(--color-electric-indigo)";
    return "var(--text-secondary)";
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(logs.join("\n"));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className="glass-panel-static terminal-window"
      style={{
        position: "relative",
        overflow: "hidden",
        boxShadow:
          "inset 0 2px 8px rgba(0,0,0,0.4), 0 0 30px rgba(139, 92, 246, 0.15)",
        border: "1px solid rgba(139, 92, 246, 0.2)",
        backdropFilter: "blur(20px)",
        background: "rgba(13, 11, 30, 0.7)",
      }}
    >
      <div style={{
        position: "absolute", inset: 0, zIndex: 0, pointerEvents: "none",
        background: "linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06))",
        backgroundSize: "100% 4px, 3px 100%",
        opacity: 0.3
      }} />
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "10px 16px",
          borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
          background: "rgba(0, 0, 0, 0.3)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ display: "flex", gap: 6 }}>
            <div
              style={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: "#ef4444",
              }}
            />
            <div
              style={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: "#f59e0b",
              }}
            />
            <div
              style={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: "#10b981",
              }}
            />
          </div>
          <span
            style={{
              fontSize: "0.75rem",
              color: "var(--text-tertiary)",
              fontWeight: 600,
              marginLeft: 8,
            }}
          >
            <TerminalIcon
              size={12}
              style={{ marginRight: 4, verticalAlign: "middle" }}
            />
            {title}
          </span>
        </div>

        <div style={{ display: "flex", gap: 4 }}>
          <button
            onClick={handleCopy}
            className="btn btn-ghost btn-sm"
            style={{ padding: "4px 8px" }}
            title="Copy logs"
          >
            {copied ? <Check size={12} /> : <Copy size={12} />}
          </button>
        </div>
      </div>

      {/* Log Content */}
      <div 
        className="terminal-body"
        ref={scrollRef}
        style={{ 
          background: "var(--glass-bg)", 
          backdropFilter: "var(--glass-blur)",
          border: "1px solid var(--glass-border)",
          boxShadow: "var(--glass-inner-glow), 0 10px 30px rgba(0, 0, 0, 0.5)",
          color: "var(--text-primary)", 
          fontFamily: "var(--font-mono)", 
          padding: "16px", 
          height: "300px", 
          overflowY: "auto",
          transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
          borderBottomLeftRadius: 12,
          borderBottomRightRadius: 12
        }}
      >
        <AnimatePresence>
          {logs.length === 0 ? (
            <div
              style={{
                color: "var(--text-tertiary)",
                fontStyle: "italic",
                padding: "20px 0",
                textAlign: "center",
              }}
            >
              Awaiting build output...
            </div>
          ) : (
            logs.filter(l => typeof l === "string").map((line, i) => {
              const color = getLineColor(line);
              // Simple regex for URLs and absolute Linux-style paths
              const parts = line.split(/(https?:\/\/[^\s]+|\/(?:[\w.-]+\/)*[\w.-]+)/g);
              return (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.15, delay: i * 0.02 }}
                  style={{
                    color: color,
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-all",
                    position: "relative",
                    zIndex: 1,
                  }}
                >
                  <span style={{ color: "var(--text-tertiary)", marginRight: 8, userSelect: "none" }}>
                    {String(i + 1).padStart(3, " ")}
                  </span>
                  {parts.map((part, j) => {
                    if (part.match(/^(https?:\/\/|\/)/)) {
                      return <span key={j} style={{ color: "var(--color-cyan-info)", textDecoration: "underline", textUnderlineOffset: 2 }}>{part}</span>;
                    }
                    return part;
                  })}
                </motion.div>
              );
            })
          )}
        </AnimatePresence>

        {/* Blinking Cursor */}
        {logs.length > 0 && (
          <motion.span
            animate={{ opacity: [1, 0, 1] }}
            transition={{ duration: 1, repeat: Infinity }}
            style={{
              display: "inline-block",
              width: 8,
              height: 16,
              background: "var(--color-electric-indigo)",
              marginLeft: 4,
              verticalAlign: "middle",
            }}
          />
        )}
      </div>
    </div>
  );
}
