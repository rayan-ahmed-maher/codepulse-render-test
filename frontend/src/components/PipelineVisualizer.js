"use client";

import { useState, useEffect, useRef, useMemo } from "react";
import { motion, AnimatePresence, useAnimation } from "framer-motion";
import {
  Upload, ShieldCheck, Search, Hammer, Rocket, CheckCircle2,
  Globe, XCircle, Loader2, SearchIcon, Wifi,
} from "lucide-react";

// ── CONSTANTS & CONFIG ──
const STAGES = [
  { key: "upload",   label: "UPLOAD",   icon: Upload },
  { key: "validate", label: "VALIDATE", icon: ShieldCheck },
  { key: "analyze",  label: "ANALYZE",  icon: Search },
  { key: "build",    label: "BUILD",    icon: Hammer },
  { key: "deploy",   label: "DEPLOY",   icon: Rocket },
  { key: "verify",   label: "VERIFY",   icon: SearchIcon },
  { key: "live",     label: "LIVE",     icon: Wifi },
];

const COLORS = {
  cyan: "#00F5FF",
  magenta: "#FF2D9B",
  green: "#00FF88",
  gold: "#FFD700",
  pending: "#1C2333",
  bg: "rgba(255,255,255,0.05)",
  border: "rgba(255,255,255,0.1)",
};

// ── HELPER: Hexagon Shape ──
const Hexagon = ({ children, status, color, className, style }) => {
  const isActive = status === "active";
  const isComplete = status === "complete";
  const isFailed = status === "failed";

  return (
    <div className={className} style={{ position: "relative", width: 60, height: 68, ...style }}>
      {/* Outer Rotating Ring (Active Only) */}
      {isActive && (
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
          style={{
            position: "absolute", inset: -8,
            border: `2px dashed ${COLORS.cyan}`,
            borderRadius: "50%",
            opacity: 0.6,
            zIndex: 0,
          }}
        />
      )}

      {/* Main Hexagon SVG */}
      <svg width="60" height="68" viewBox="0 0 60 68" style={{ position: "relative", zIndex: 1, overflow: "visible" }}>
        <motion.path
          d="M30 0 L60 17 L60 51 L30 68 L0 51 L0 17 Z"
          fill={isComplete ? "url(#green-grad)" : isFailed ? "url(#red-grad)" : "rgba(10,20,40,0.8)"}
          stroke={isActive ? COLORS.cyan : isComplete ? COLORS.green : isFailed ? "#ef4444" : COLORS.pending}
          strokeWidth="2"
          animate={isActive ? {
            strokeShadow: [`0 0 0px ${COLORS.cyan}`, `0 0 20px ${COLORS.cyan}`, `0 0 0px ${COLORS.cyan}`],
            filter: [`drop-shadow(0 0 2px ${COLORS.cyan})`, `drop-shadow(0 0 12px ${COLORS.cyan})`, `drop-shadow(0 0 2px ${COLORS.cyan})`]
          } : {}}
          transition={isActive ? { duration: 2, repeat: Infinity } : {}}
        />
        <defs>
          <linearGradient id="green-grad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#065f46" />
            <stop offset="100%" stopColor={COLORS.green} />
          </linearGradient>
          <linearGradient id="red-grad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#991b1b" />
            <stop offset="100%" stopColor="#ef4444" />
          </linearGradient>
        </defs>
      </svg>

      {/* Content Overlay */}
      <div style={{
        position: "absolute", inset: 0, zIndex: 2,
        display: "flex", alignItems: "center", justifyContent: "center",
      }}>
        {children}
      </div>
    </div>
  );
};

// ── CANVAS: Confetti & Particles ──
const PipelineCanvas = ({ activeStageIndex, isLive, isFailed }) => {
  const canvasRef = useRef(null);
  const particles = useRef([]);
  const confetti = useRef([]);
  const pulseRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let animationFrame;

    const resize = () => {
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    };
    window.addEventListener("resize", resize);
    resize();

    const createConfetti = () => {
      const colors = [COLORS.cyan, COLORS.magenta, COLORS.green, COLORS.gold];
      for (let i = 0; i < 150; i++) {
        confetti.current.push({
          x: canvas.width / 2,
          y: canvas.height / 2,
          vx: (Math.random() - 0.5) * 15,
          vy: (Math.random() - 0.7) * 20,
          size: Math.random() * 6 + 2,
          color: colors[Math.floor(Math.random() * colors.length)],
          rotation: Math.random() * 360,
          rv: (Math.random() - 0.5) * 10,
          life: 1.0,
        });
      }
    };

    if (isLive) createConfetti();

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // 1. Draw Active Stage Stream
      if (activeStageIndex !== -1 && activeStageIndex < STAGES.length - 1) {
        // Simple logic to find the line between hexagons
        // Assuming horizontal layout for desktop
        const spacing = canvas.width / STAGES.length;
        const startX = spacing * (activeStageIndex + 0.5) + 30;
        const endX = spacing * (activeStageIndex + 1.5) - 30;
        const y = canvas.height / 2;

        if (Math.random() > 0.7) {
          particles.current.push({ x: startX, y, vx: 3, life: 1.0 });
        }

        ctx.shadowBlur = 10;
        ctx.shadowColor = COLORS.cyan;
        ctx.fillStyle = COLORS.cyan;
        particles.current.forEach((p, i) => {
          ctx.beginPath();
          ctx.arc(p.x, p.y, 2, 0, Math.PI * 2);
          ctx.fill();
          p.x += p.vx;
          p.life -= 0.01;
          if (p.x > endX || p.life <= 0) particles.current.splice(i, 1);
        });
        ctx.shadowBlur = 0;
      }

      // 2. Draw Confetti
      confetti.current.forEach((c, i) => {
        ctx.save();
        ctx.translate(c.x, c.y);
        ctx.rotate((c.rotation * Math.PI) / 180);
        ctx.fillStyle = c.color;
        ctx.globalAlpha = c.life;
        ctx.fillRect(-c.size / 2, -c.size / 2, c.size, c.size);
        ctx.restore();

        c.x += c.vx;
        c.y += c.vy;
        c.vy += 0.4; // gravity
        c.rotation += c.rv;
        c.life -= 0.01;
        if (c.life <= 0) confetti.current.splice(i, 1);
      });

      // 3. Radial Pulse (Green)
      if (isLive && pulseRef.current < 1) {
        pulseRef.current += 0.01;
        const grad = ctx.createRadialGradient(
          canvas.width / 2, canvas.height / 2, 0,
          canvas.width / 2, canvas.height / 2, canvas.width * pulseRef.current
        );
        grad.addColorStop(0, "rgba(0, 255, 136, 0.2)");
        grad.addColorStop(1, "rgba(0, 255, 136, 0)");
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
      }

      animationFrame = requestAnimationFrame(draw);
    };

    draw();
    return () => {
      cancelAnimationFrame(animationFrame);
      window.removeEventListener("resize", resize);
    };
  }, [activeStageIndex, isLive]);

  return <canvas ref={canvasRef} style={{ position: "absolute", inset: 0, pointerEvents: "none", zIndex: 5 }} />;
};

// ── COMPONENT: Animated Icon ──
const AnimatedIcon = ({ icon: Icon, stage, status }) => {
  const isActive = status === "active";
  const isComplete = status === "complete";

  if (isComplete) {
    return (
      <motion.svg
        width="24" height="24" viewBox="0 0 24 24" fill="none"
        stroke={COLORS.green} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"
      >
        <motion.path
          d="M20 6L9 17L4 12"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 0.5, ease: "easeInOut" }}
        />
      </motion.svg>
    );
  }

  const iconColor = isActive ? COLORS.cyan : COLORS.pending;

  switch (stage) {
    case "upload":
      return (
        <motion.div animate={isActive ? { y: [0, -4, 0] } : {}} transition={{ repeat: Infinity, duration: 1 }}>
          <Icon size={22} color={iconColor} />
        </motion.div>
      );
    case "analyze":
      return (
        <motion.div animate={isActive ? { rotate: 360 } : {}} transition={{ repeat: Infinity, duration: 3, ease: "linear" }}>
          <Icon size={22} color={iconColor} />
        </motion.div>
      );
    case "deploy":
      return (
        <motion.div animate={isActive ? { y: [0, -2, 0], x: [0, 1, -1, 0] } : {}} transition={{ repeat: Infinity, duration: 0.1 }}>
          <Icon size={22} color={iconColor} />
        </motion.div>
      );
    case "live":
      return (
        <motion.div animate={isActive ? { opacity: [0.4, 1, 0.4] } : {}} transition={{ repeat: Infinity, duration: 1 }}>
          <Icon size={22} color={iconColor} />
        </motion.div>
      );
    default:
      return <Icon size={22} color={iconColor} />;
  }
};

// ── MAIN COMPONENT ──
export default function PipelineVisualizer({ trackingId, wsUrl }) {
  const [stages, setStages] = useState(
    STAGES.reduce((acc, s) => ({ ...acc, [s.key]: { status: "pending", elapsed: 0, start: null } }), {})
  );
  const [activeStageIndex, setActiveStageIndex] = useState(-1);
  const [timers, setTimers] = useState({});
  const [isLive, setIsLive] = useState(false);
  const [isFailed, setIsFailed] = useState(false);

  useEffect(() => {
    if (!trackingId) return;

    const WS_BASE = wsUrl || process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
    const url = `${WS_BASE}/ws/terminal/${trackingId}`;
    const ws = new WebSocket(url);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type !== "pipeline") return;

        setStages((prev) => {
          const newStages = { ...prev };
          newStages[data.stage] = {
            status: data.status,
            elapsed: data.stage_elapsed || 0,
            error: data.error || "",
          };

          if (data.status === "active") {
            const idx = STAGES.findIndex(s => s.key === data.stage);
            setActiveStageIndex(idx);
          } else if (data.status === "complete" || data.status === "failed") {
            setActiveStageIndex(-1);
          }

          if (data.stage === "live" && data.status === "complete") setIsLive(true);
          if (data.status === "failed") setIsFailed(true);

          return newStages;
        });
      } catch {}
    };

    return () => ws.close();
  }, [trackingId, wsUrl]);

  // Update real-time timers for active stage
  useEffect(() => {
    const interval = setInterval(() => {
      if (activeStageIndex !== -1) {
        const key = STAGES[activeStageIndex].key;
        setTimers(prev => ({
          ...prev,
          [key]: (prev[key] || 0) + 0.1
        }));
      }
    }, 100);
    return () => clearInterval(interval);
  }, [activeStageIndex]);

  return (
    <div style={{
      padding: "32px",
      background: "rgba(10, 15, 30, 0.7)",
      backdropFilter: "blur(20px)",
      border: `1px solid ${COLORS.border}`,
      borderRadius: 24,
      position: "relative",
      overflow: "hidden",
      boxShadow: "0 20px 50px rgba(0,0,0,0.5), inset 0 0 20px rgba(0,245,255,0.05)",
    }}>
      {/* Deep Space Background Overlay */}
      <div style={{
        position: "absolute", inset: 0, zIndex: 0,
        background: "radial-gradient(circle at 50% 50%, rgba(0, 245, 255, 0.05) 0%, transparent 70%)",
        opacity: 0.5,
      }} />

      <PipelineCanvas activeStageIndex={activeStageIndex} isLive={isLive} isFailed={isFailed} />

      <div style={{ position: "relative", zIndex: 10 }}>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 40 }}>
          <h3 style={{ fontSize: "1rem", fontWeight: 800, color: "white", letterSpacing: "1px", display: "flex", alignItems: "center", gap: 10 }}>
            <Rocket size={20} color={COLORS.cyan} />
            DEPLOYMENT PIPELINE
          </h3>
          <div style={{ fontFamily: "JetBrains Mono", fontSize: "0.75rem", color: COLORS.cyan, background: "rgba(0,245,255,0.1)", padding: "4px 12px", borderRadius: 20, border: `1px solid ${COLORS.cyan}44` }}>
            SYSTEM_STABLE: 200 OK
          </div>
        </div>

        {/* Pipeline Body */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
          {STAGES.map((stage, i) => {
            const state = stages[stage.key];
            const isActive = state.status === "active";
            const isComplete = state.status === "complete";
            const isFailed = state.status === "failed";
            const timerValue = isActive ? (timers[stage.key] || 0) : state.elapsed;

            return (
              <div key={stage.key} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", position: "relative" }}>
                {/* Node */}
                <motion.div
                  animate={isFailed ? { x: [-5, 5, -5, 5, 0] } : {}}
                  transition={isFailed ? { duration: 0.3 } : {}}
                >
                  <Hexagon status={state.status}>
                    <AnimatedIcon icon={stage.icon} stage={stage.key} status={state.status} />
                  </Hexagon>
                </motion.div>

                {/* Label */}
                <div style={{
                  fontSize: "0.65rem", fontWeight: 900, marginTop: 12,
                  color: isActive ? COLORS.cyan : isComplete ? COLORS.green : isFailed ? "#ef4444" : "rgba(255,255,255,0.3)",
                  letterSpacing: "0.5px",
                  textShadow: isActive ? `0 0 10px ${COLORS.cyan}` : "none",
                }}>
                  {stage.label}
                </div>

                {/* Timer */}
                <div style={{
                  fontFamily: "JetBrains Mono", fontSize: "0.6rem", marginTop: 4,
                  color: isActive ? COLORS.cyan : isComplete ? COLORS.green : "rgba(255,255,255,0.2)",
                  opacity: (isActive || isComplete) ? 1 : 0.5,
                  textShadow: isActive ? `0 0 8px ${COLORS.cyan}` : "none",
                }}>
                  {timerValue > 0 ? timerValue.toFixed(1) + "s" : "0.0s"}
                </div>

                {/* Error Tooltip */}
                {isFailed && state.error && (
                  <div style={{
                    position: "absolute", top: 100, padding: "8px 12px", background: "rgba(239, 68, 68, 0.9)",
                    borderRadius: 8, fontSize: "0.65rem", color: "white", width: 140, textAlign: "center", zIndex: 50,
                    boxShadow: "0 10px 20px rgba(0,0,0,0.5)", border: "1px solid rgba(255,255,255,0.1)",
                  }}>
                    {state.error}
                  </div>
                )}

                {/* Connecting Line (Desktop) */}
                {i < STAGES.length - 1 && (
                  <div style={{
                    position: "absolute", top: 34, left: "100%", width: "calc(100% - 60px)", height: 2,
                    background: "rgba(255,255,255,0.05)", transform: "translateX(-30px)", zIndex: 1,
                  }}>
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: isComplete ? "100%" : 0 }}
                      transition={{ duration: 0.8, ease: "easeOut" }}
                      style={{ height: "100%", background: `linear-gradient(90deg, ${COLORS.cyan}, ${COLORS.green})`, boxShadow: `0 0 10px ${COLORS.cyan}` }}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <style jsx>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
