"use client";

import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, X, ShieldAlert, Zap } from "lucide-react";

/**
 * NVIDIA AI Error Toast — cinematic glitch effect
 */
export default function ValidationToast({ show, type = "error", title, message, onDismiss }) {
  const isError = type === "error";

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0, y: -20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -20, scale: 0.95 }}
          transition={{ type: "spring", stiffness: 200, damping: 20 }}
          style={{
            position: "relative",
            padding: "16px 20px",
            borderRadius: "var(--radius-lg)",
            background: isError
              ? "linear-gradient(135deg, rgba(239, 68, 68, 0.08), rgba(239, 68, 68, 0.03))"
              : "linear-gradient(135deg, rgba(245, 158, 11, 0.08), rgba(245, 158, 11, 0.03))",
            border: `1px solid ${isError ? "rgba(239, 68, 68, 0.2)" : "rgba(245, 158, 11, 0.2)"}`,
            display: "flex",
            alignItems: "flex-start",
            gap: 14,
            overflow: "hidden",
          }}
        >
          {/* Glitch scanline */}
          <motion.div
            animate={{ top: ["-10%", "110%"] }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            style={{
              position: "absolute",
              left: 0, right: 0,
              height: 2,
              background: isError
                ? "linear-gradient(90deg, transparent, rgba(239,68,68,0.3), transparent)"
                : "linear-gradient(90deg, transparent, rgba(245,158,11,0.3), transparent)",
              pointerEvents: "none",
            }}
          />

          {/* Icon */}
          <motion.div
            animate={{ rotate: [0, -3, 3, -1, 0] }}
            transition={{ duration: 0.5, delay: 0.2 }}
            style={{
              width: 36, height: 36, borderRadius: 10,
              background: isError ? "rgba(239,68,68,0.12)" : "rgba(245,158,11,0.12)",
              display: "flex", alignItems: "center", justifyContent: "center",
              flexShrink: 0,
            }}
          >
            {isError ? (
              <ShieldAlert size={18} color="#ef4444" />
            ) : (
              <AlertTriangle size={18} color="#f59e0b" />
            )}
          </motion.div>

          {/* Content */}
          <div style={{ flex: 1 }}>
            <div style={{
              fontSize: "0.85rem", fontWeight: 800,
              color: isError ? "#ef4444" : "#f59e0b",
              marginBottom: 2, display: "flex", alignItems: "center", gap: 6,
            }}>
              <Zap size={12} />
              {title || "Validation Failed"}
            </div>
            <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
              {message}
            </p>
          </div>

          {/* Dismiss */}
          {onDismiss && (
            <button
              onClick={onDismiss}
              style={{
                background: "none", border: "none",
                color: "var(--text-tertiary)", cursor: "pointer", padding: 4,
              }}
            >
              <X size={14} />
            </button>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
