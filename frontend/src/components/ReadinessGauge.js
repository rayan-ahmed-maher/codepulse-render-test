"use client";

import { motion, useSpring, useTransform } from "framer-motion";
import { useEffect, useState } from "react";

export default function ReadinessGauge({ score = 0, size = 140, strokeWidth = 10 }) {
  const [displayScore, setDisplayScore] = useState(0);
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  const springScore = useSpring(0, { stiffness: 60, damping: 20 });
  const strokeDashoffset = useTransform(
    springScore,
    [0, 100],
    [circumference, 0]
  );

  useEffect(() => {
    springScore.set(score);
    const unsub = springScore.on("change", (v) =>
      setDisplayScore(Math.round(v))
    );
    return unsub;
  }, [score, springScore]);

  const getColor = (s) => {
    if (s >= 80) return { main: "#10b981", glow: "rgba(16, 185, 129, 0.4)", label: "Ready" };
    if (s >= 50) return { main: "#f59e0b", glow: "rgba(245, 158, 11, 0.4)", label: "Needs Work" };
    return { main: "#ef4444", glow: "rgba(239, 68, 68, 0.4)", label: "Critical" };
  };

  const color = getColor(score);

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
      {/* Glow Filter */}
      <svg width={0} height={0} style={{ position: "absolute" }}>
        <defs>
          <filter id="gauge-glow">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
      </svg>

      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        {/* Background Track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(255, 255, 255, 0.05)"
          strokeWidth={strokeWidth}
        />
        {/* Animated Progress */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color.main}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          style={{ strokeDashoffset }}
          filter="url(#gauge-glow)"
        />
      </svg>

      {/* Center Label */}
      <div
        style={{
          position: "absolute",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 2,
        }}
      >
        <span
          style={{
            fontSize: size * 0.22,
            fontWeight: 800,
            color: color.main,
            letterSpacing: "-0.02em",
            textShadow: `0 0 20px ${color.glow}`,
            lineHeight: 1,
          }}
        >
          {displayScore}
        </span>
        <span
          style={{
            fontSize: size * 0.08,
            fontWeight: 600,
            color: "var(--text-tertiary)",
            textTransform: "uppercase",
            letterSpacing: "0.1em",
          }}
        >
          {color.label}
        </span>
      </div>
    </div>
  );
}
