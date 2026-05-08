"use client";

import { motion } from "framer-motion";
import { Scan, Shield, Server, Rocket, Check, Loader2 } from "lucide-react";

const STEPS = [
  { id: "analyze", label: "Analyze", icon: Scan, color: "var(--color-electric-indigo)" },
  { id: "scan", label: "Security", icon: Shield, color: "var(--color-violet-accent)" },
  { id: "recommend", label: "Recommend", icon: Server, color: "var(--color-cyan-info)" },
  { id: "deploy", label: "Deploy", icon: Rocket, color: "var(--color-emerald-neon)" },
];

export default function DeployStepper({ currentStep = "analyze", status = "idle" }) {
  const currentIndex = STEPS.findIndex((s) => s.id === currentStep);

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 0,
        padding: "20px 0",
        width: "100%",
      }}
    >
      {STEPS.map((step, i) => {
        const isCompleted = i < currentIndex;
        const isCurrent = i === currentIndex;
        const isPending = i > currentIndex;
        const Icon = step.icon;

        return (
          <div
            key={step.id}
            style={{ display: "flex", alignItems: "center" }}
          >
            {/* Step Node */}
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{
                scale: isCurrent ? 1.1 : 1,
                opacity: 1,
              }}
              transition={{ type: "spring", stiffness: 200, damping: 15, delay: i * 0.1 }}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 8,
              }}
            >
              <div
                style={{
                  width: 44,
                  height: 44,
                  borderRadius: "50%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  background: isCompleted
                    ? `linear-gradient(135deg, ${step.color}, rgba(255,255,255,0.1))`
                    : isCurrent
                    ? `rgba(99, 102, 241, 0.15)`
                    : "rgba(255, 255, 255, 0.03)",
                  border: `2px solid ${
                    isCompleted
                      ? step.color
                      : isCurrent
                      ? "var(--color-electric-indigo)"
                      : "rgba(255, 255, 255, 0.08)"
                  }`,
                  boxShadow: isCurrent
                    ? `0 0 20px ${step.color}40`
                    : "none",
                  transition: "all 0.3s ease",
                }}
              >
                {isCompleted ? (
                  <Check size={18} color="white" />
                ) : isCurrent && status === "loading" ? (
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  >
                    <Loader2 size={18} color={step.color} />
                  </motion.div>
                ) : (
                  <div className={isCurrent && step.id === 'recommend' ? 'css-ripple' : isCurrent && step.id === 'deploy' ? 'engine-glow' : ''} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Icon
                      size={18}
                      color={
                        isCurrent ? step.color : "var(--text-tertiary)"
                      }
                    />
                  </div>
                )}
              </div>

              <span
                style={{
                  fontSize: "0.7rem",
                  fontWeight: isCurrent ? 700 : 500,
                  color: isCompleted
                    ? step.color
                    : isCurrent
                    ? "var(--text-primary)"
                    : "var(--text-tertiary)",
                  letterSpacing: "0.02em",
                  textTransform: "uppercase",
                }}
              >
                {step.label}
              </span>
            </motion.div>

            {/* Connector Line */}
            {i < STEPS.length - 1 && (
              <div style={{ width: 60, height: 24, marginBottom: 24, display: 'flex', alignItems: 'center' }}>
                <svg width="100%" height="2" style={{ overflow: "visible" }}>
                  <defs>
                    <linearGradient id={`grad-${i}`}>
                      <stop offset="0%" stopColor={STEPS[i].color} />
                      <stop offset="100%" stopColor={STEPS[i + 1].color} />
                    </linearGradient>
                  </defs>
                  <line x1="0" y1="1" x2="100%" y2="1"
                    stroke={isCompleted ? `url(#grad-${i})` : "rgba(255, 255, 255, 0.06)"}
                    strokeWidth="2"
                    strokeDasharray={isCompleted || isCurrent ? "6 6" : "0"}
                    className={isCompleted || isCurrent ? "data-flow-line" : ""}
                  />
                  {isCurrent && (
                    <motion.line x1="0" y1="1" x2="100%" y2="1"
                      stroke={step.color}
                      strokeWidth="2"
                      strokeDasharray="60"
                      initial={{ strokeDashoffset: 60 }}
                      animate={{ strokeDashoffset: -60 }}
                      transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                    />
                  )}
                </svg>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
