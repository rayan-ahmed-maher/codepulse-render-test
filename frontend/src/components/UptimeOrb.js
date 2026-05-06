"use client";

import { motion } from "framer-motion";

export default function UptimeOrb({ isLive = true, size = 120 }) {
  const color = isLive
    ? { main: "#10b981", glow: "rgba(16, 185, 129, 0.4)", bg: "rgba(16, 185, 129, 0.08)" }
    : { main: "#ef4444", glow: "rgba(239, 68, 68, 0.4)", bg: "rgba(239, 68, 68, 0.08)" };

  return (
    <div
      style={{
        position: "relative",
        width: size,
        height: size,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {/* Outer Ring Pulses */}
      {[1, 2, 3].map((i) => (
        <motion.div
          key={i}
          animate={{
            scale: [1, 2.2],
            opacity: [0.3, 0],
          }}
          transition={{
            duration: 2.5,
            repeat: Infinity,
            delay: i * 0.6,
            ease: "easeOut",
          }}
          style={{
            position: "absolute",
            width: size * 0.5,
            height: size * 0.5,
            borderRadius: "50%",
            border: `2px solid ${color.main}`,
          }}
        />
      ))}

      {/* Glow Background */}
      <motion.div
        animate={{
          boxShadow: [
            `0 0 40px ${color.glow}, 0 0 80px ${color.bg}`,
            `0 0 60px ${color.glow}, 0 0 120px ${color.bg}`,
            `0 0 40px ${color.glow}, 0 0 80px ${color.bg}`,
          ],
        }}
        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        style={{
          position: "absolute",
          width: size * 0.5,
          height: size * 0.5,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${color.main} 0%, ${color.bg} 60%, transparent 100%)`,
          filter: "blur(8px)",
        }}
      />

      {/* Core Orb */}
      <motion.div
        animate={{
          scale: [1, 1.05, 1],
        }}
        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        style={{
          width: size * 0.35,
          height: size * 0.35,
          borderRadius: "50%",
          background: `radial-gradient(circle at 30% 30%, ${color.main}, rgba(0,0,0,0.2))`,
          boxShadow: `0 0 30px ${color.glow}, inset 0 0 20px rgba(255,255,255,0.1)`,
          position: "relative",
          zIndex: 1,
        }}
      >
        {/* Specular Highlight */}
        <div
          style={{
            position: "absolute",
            top: "15%",
            left: "20%",
            width: "30%",
            height: "20%",
            borderRadius: "50%",
            background: "rgba(255, 255, 255, 0.3)",
            filter: "blur(3px)",
          }}
        />
      </motion.div>

      {/* Status Label */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          fontSize: "0.65rem",
          fontWeight: 700,
          textTransform: "uppercase",
          letterSpacing: "0.15em",
          color: color.main,
          textShadow: `0 0 10px ${color.glow}`,
        }}
      >
        {isLive ? "LIVE" : "OFFLINE"}
      </div>
    </div>
  );
}
