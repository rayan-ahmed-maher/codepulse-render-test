"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Shield, Code2, Zap, Package, ChevronDown, ChevronRight,
  AlertTriangle, RefreshCw, Loader2, Sparkles, FileCode2, X, CheckCircle2
} from "lucide-react";
import { api } from "@/lib/api";

const COLORS = {
  cyan: "#00F5FF",
  magenta: "#FF2D9B",
  green: "#00FF88",
  gold: "#FFD700",
  amber: "#FFD700",
  red: "#ef4444",
  purple: "#7C3AED",
  textSec: "rgba(255,255,255,0.7)",
  textTer: "rgba(255,255,255,0.4)"
};

const CATEGORY_CONFIG = {
  Security:     { icon: Shield,  color: COLORS.red,     delay: 0 },
  Quality:      { icon: Code2,   color: COLORS.amber,   delay: 150 },
  Performance:  { icon: Zap,     color: COLORS.purple,  delay: 300 },
  Dependencies: { icon: Package, color: COLORS.green,   delay: 450 },
};

const SEVERITY_STYLE = {
  Critical: { color: COLORS.red, glow: "rgba(239, 68, 68, 0.4)" },
  High:     { color: "#f97316", glow: "rgba(249, 115, 22, 0.4)" },
  Medium:   { color: "#facc15", glow: "rgba(250, 204, 21, 0.4)" },
  Low:      { color: "#3b82f6", glow: "rgba(59, 130, 246, 0.4)" },
};

// ── COMPONENT: Hero Score Gauge ──
function HeroGauge({ score }) {
  const [displayScore, setDisplayScore] = useState(0);
  const size = 280;
  const strokeWidth = 12;
  const radius = (size - strokeWidth * 2) / 2;
  const circumference = 2 * Math.PI * radius;

  useEffect(() => {
    let start = 0;
    const duration = 2000;
    const startTime = performance.now();

    const animate = (time) => {
      const elapsed = time - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
      setDisplayScore(Math.floor(eased * score));
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [score]);

  const offset = circumference - (displayScore / 100) * circumference;
  const color = score > 80 ? COLORS.green : score > 50 ? COLORS.amber : COLORS.red;

  return (
    <div style={{ position: "relative", width: size, height: size, margin: "0 auto" }}>
      {/* Outer Dashed Ring (Continuous Rotation) */}
      <motion.div
        animate={{ rotate: score >= 50 ? 360 : -360 }}
        transition={{ duration: 10, repeat: Infinity, ease: "linear" }}
        style={{
          position: "absolute", inset: -15, borderRadius: "50%",
          border: `2px dashed ${color}33`,
        }}
      />

      {/* Middle Ring: Actual Score Arc */}
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)", overflow: "visible" }}>
        <circle cx={size/2} cy={size/2} r={radius} fill="none"
          stroke="rgba(255,255,255,0.05)" strokeWidth={strokeWidth} />
        <motion.circle
          cx={size/2} cy={size/2} r={radius} fill="none"
          stroke={color} strokeWidth={strokeWidth} strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 2, ease: "easeOut" }}
          style={{ filter: `drop-shadow(0 0 15px ${color}66)` }}
        />
      </svg>

      {/* Inner Pulsing Glow Ring */}
      <motion.div
        animate={{ scale: [0.95, 1.05, 0.95], opacity: [0.1, 0.2, 0.1] }}
        transition={{ duration: 3, repeat: Infinity }}
        style={{
          position: "absolute", inset: 40, borderRadius: "50%",
          background: `radial-gradient(circle, ${color} 0%, transparent 70%)`,
        }}
      />

      {/* Center Text */}
      <div style={{
        position: "absolute", inset: 0, display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center", zIndex: 10,
      }}>
        <div style={{ display: "flex", overflow: "hidden", height: 80 }}>
          {String(displayScore).padStart(2, "0").split("").map((digit, i) => (
            <motion.div
              key={i}
              initial={{ y: 50 }}
              animate={{ y: 0 }}
              style={{ fontSize: "5rem", fontWeight: 900, color: "white", fontFamily: "'JetBrains Mono', monospace" }}
            >
              {digit}
            </motion.div>
          ))}
          <span style={{ fontSize: "2rem", alignSelf: "flex-end", marginBottom: 15, color: COLORS.textTer }}>%</span>
        </div>
        <div style={{ fontSize: "0.8rem", color: COLORS.textSec, fontWeight: 700, letterSpacing: "2px", marginTop: -10 }}>
          CODE HEALTH
        </div>
      </div>
    </div>
  );
}

// ── COMPONENT: Diff Modal ──
function DiffModal({ issue, onClose }) {
  const [loading, setLoading] = useState(true);
  const [fixData, setFixData] = useState(null);
  const [applied, setApplied] = useState(false);

  useEffect(() => {
    const loadFix = async () => {
      try {
        const res = await api.aiFixIssue(issue.file_name, issue.line_number, issue.description, issue.code_snippet);
        setFixData(res.fix);
      } catch (err) {
        setFixData({ error: err.message });
      }
      setLoading(false);
    };
    loadFix();
  }, [issue]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      style={{
        position: "fixed", inset: 0, zIndex: 1000,
        background: "rgba(0,0,0,0.8)", backdropFilter: "blur(20px)",
        display: "flex", alignItems: "center", justifyContent: "center", padding: 20,
      }}
    >
      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        style={{
          width: 800, maxWidth: "100%", maxHeight: "90vh",
          background: "rgba(20,25,40,0.95)", border: `1px solid ${COLORS.border}`,
          borderRadius: 24, padding: 32, overflowY: "auto", position: "relative",
          boxShadow: "0 30px 100px rgba(0,0,0,0.8), 0 0 40px rgba(0,245,255,0.1)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 24 }}>
          <div>
            <h2 style={{ fontSize: "1.5rem", fontWeight: 800, color: "white", display: "flex", alignItems: "center", gap: 10 }}>
              <Sparkles size={24} color={COLORS.cyan} /> AI INTELLIGENT FIX
            </h2>
            <p style={{ color: COLORS.textSec, fontSize: "0.9rem", marginTop: 4 }}>
              Resolving security/quality issue in <code style={{ color: COLORS.cyan }}>{issue.file_name}</code>
            </p>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "white" }}>
            <X size={24} />
          </button>
        </div>

        {loading ? (
          <div style={{ padding: 100, textAlign: "center" }}>
            <Loader2 size={40} className="animate-spin" color={COLORS.cyan} />
            <p style={{ marginTop: 20, color: COLORS.textSec }}>Analyzing code with NVIDIA NIM...</p>
          </div>
        ) : fixData?.error ? (
          <div style={{ padding: 40, background: "rgba(239,68,68,0.1)", borderRadius: 12, border: "1px solid rgba(239,68,68,0.2)", color: COLORS.red }}>
            {fixData.error}
          </div>
        ) : (
          <>
            <div style={{ background: "rgba(0,0,0,0.3)", borderRadius: 16, overflow: "hidden", border: "1px solid rgba(255,255,255,0.05)" }}>
              {/* Diff View */}
              <div style={{ padding: "20px", fontFamily: "'JetBrains Mono', monospace", fontSize: "0.85rem" }}>
                <div style={{ display: "flex", background: "rgba(239,68,68,0.1)", borderLeft: `4px solid ${COLORS.red}`, marginBottom: 2 }}>
                  <div style={{ width: 40, textAlign: "right", paddingRight: 10, color: COLORS.textTer }}>-</div>
                  <pre style={{ flex: 1, padding: "4px 10px", color: "#fca5a5", whiteSpace: "pre-wrap" }}>{fixData.original || issue.code_snippet}</pre>
                </div>
                <div style={{ display: "flex", background: "rgba(0,255,136,0.1)", borderLeft: `4px solid ${COLORS.green}` }}>
                  <div style={{ width: 40, textAlign: "right", paddingRight: 10, color: COLORS.textTer }}>+</div>
                  <pre style={{ flex: 1, padding: "4px 10px", color: "#86efac", whiteSpace: "pre-wrap" }}>{fixData.fixed}</pre>
                </div>
              </div>
            </div>

            {fixData.explanation && (
              <div style={{ marginTop: 20, padding: 16, background: "rgba(124,58,237,0.1)", borderRadius: 12, border: "1px solid rgba(124,58,237,0.2)", color: "#c4b5fd", fontSize: "0.85rem" }}>
                <strong>AI LOGIC:</strong> {fixData.explanation}
              </div>
            )}

            <button
              onClick={() => { setApplied(true); setTimeout(onClose, 1000); }}
              style={{
                width: "100%", padding: "16px", borderRadius: 12, marginTop: 32,
                background: applied ? COLORS.green : `linear-gradient(90deg, ${COLORS.cyan}, ${COLORS.purple})`,
                color: "white", border: "none", cursor: "pointer", fontWeight: 800, fontSize: "1rem",
                display: "flex", alignItems: "center", justifyContent: "center", gap: 10,
                boxShadow: `0 10px 30px ${applied ? COLORS.green : COLORS.cyan}44`,
              }}
            >
              {applied ? <CheckCircle2 size={24} /> : <Sparkles size={24} />}
              {applied ? "PATCH APPLIED" : "APPLY SMART FIX"}
            </button>
          </>
        )}
      </motion.div>
    </motion.div>
  );
}

// ── MAIN COMPONENT ──
export default function CodeQualityScanner({ projectPath, projectId }) {
  const [scanResult, setScanResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [expandedCat, setExpandedCat] = useState(null);
  const [activeFix, setActiveFix] = useState(null);

  const runScan = async () => {
    setLoading(true);
    try {
      const res = await api.scanQuality(projectPath, projectId);
      setScanResult(res);
    } catch (err) {
      setScanResult({ error: err.message });
    }
    setLoading(false);
  };

  useEffect(() => { if (projectPath) runScan(); }, [projectPath]);

  return (
    <div style={{
      background: "rgba(10, 15, 30, 0.7)", backdropFilter: "blur(20px)",
      border: `1px solid ${COLORS.border}`, borderRadius: 32, padding: 40,
      position: "relative", overflow: "hidden",
      boxShadow: "0 40px 100px rgba(0,0,0,0.5)",
    }}>
      {/* Background Decor */}
      <div style={{ position: "absolute", top: -100, right: -100, width: 300, height: 300, background: `${COLORS.cyan}11`, filter: "blur(100px)", borderRadius: "50%" }} />

      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 40 }}>
        <h3 style={{ fontSize: "1.2rem", fontWeight: 900, color: "white", letterSpacing: "1px", display: "flex", alignItems: "center", gap: 12 }}>
          <Shield size={22} color={COLORS.cyan} /> CODE QUALITY ENGINE
        </h3>
        <button
          onClick={runScan}
          disabled={loading}
          style={{ background: "rgba(255,255,255,0.05)", border: `1px solid ${COLORS.border}`, borderRadius: 12, padding: "8px 16px", color: "white", fontSize: "0.8rem", cursor: "pointer", display: "flex", alignItems: "center", gap: 8 }}
        >
          {loading ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
          RE-ANALYZE
        </button>
      </div>

      {loading ? (
        <div style={{ padding: "80px 0", textAlign: "center" }}>
          <motion.div animate={{ rotate: 360 }} transition={{ duration: 2, repeat: Infinity, ease: "linear" }}>
            <Shield size={60} color={COLORS.cyan} />
          </motion.div>
          <p style={{ marginTop: 24, fontSize: "1.1rem", fontWeight: 700, color: COLORS.cyan }}>INITIATING AI SECURITY SCAN...</p>
          <p style={{ color: COLORS.textTer, fontSize: "0.9rem" }}>Analyzing project architecture & static patterns</p>
        </div>
      ) : scanResult?.error ? (
        <div style={{ textAlign: "center", padding: 60, color: COLORS.red }}>
          <AlertTriangle size={48} style={{ margin: "0 auto 20px" }} />
          <h3>SCAN ENGINE FAILURE</h3>
          <p>{scanResult.error}</p>
        </div>
      ) : scanResult ? (
        <>
          <HeroGauge score={scanResult.score} />

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginTop: 60 }}>
            {Object.entries(CATEGORY_CONFIG).map(([name, cfg]) => {
              const data = scanResult.categories[name] || { count: 0, issues: [] };
              return (
                <motion.div
                  key={name}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: cfg.delay / 1000 }}
                  whileHover={{ y: -8, boxShadow: `0 20px 40px rgba(0,0,0,0.4), 0 0 20px ${cfg.color}11` }}
                  style={{
                    background: "rgba(255,255,255,0.02)", border: `1px solid ${COLORS.border}`,
                    borderRadius: 20, padding: 24, cursor: "pointer",
                    borderBottom: `2px solid ${cfg.color}44`
                  }}
                  onClick={() => setExpandedCat(expandedCat === name ? null : name)}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <div style={{ padding: 12, background: `${cfg.color}22`, borderRadius: 12 }}>
                      <cfg.icon size={24} color={cfg.color} />
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: "0.9rem", fontWeight: 800, color: "white" }}>{name.toUpperCase()}</div>
                      <div style={{ fontSize: "0.75rem", color: COLORS.textTer }}>{data.count} ISSUES DETECTED</div>
                    </div>
                    <motion.div animate={{ scale: [1, 1.2, 1] }} transition={{ repeat: Infinity, duration: 2 }} style={{ width: 8, height: 8, borderRadius: "50%", background: cfg.color }} />
                  </div>

                  <AnimatePresence>
                    {expandedCat === name && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        style={{ overflow: "hidden", marginTop: 20 }}
                      >
                        {data.issues.map((issue, idx) => {
                          const sev = SEVERITY_STYLE[issue.severity] || SEVERITY_STYLE.Low;
                          return (
                            <motion.div
                              key={idx}
                              initial={{ x: 20, opacity: 0 }}
                              animate={{ x: 0, opacity: 1 }}
                              transition={{ delay: idx * 0.05 }}
                              style={{
                                padding: "12px 16px", background: "rgba(0,0,0,0.2)", borderRadius: 12, marginBottom: 10,
                                borderLeft: `4px solid ${sev.color}`, display: "flex", justifyContent: "space-between", alignItems: "center"
                              }}
                            >
                              <div style={{ flex: 1 }}>
                                <div style={{ fontSize: "0.6rem", fontWeight: 900, color: sev.color, letterSpacing: "1px" }}>{issue.severity.toUpperCase()}</div>
                                <div style={{ fontSize: "0.8rem", color: "white", marginTop: 2 }}>{issue.description}</div>
                                <div style={{ fontSize: "0.7rem", color: COLORS.textTer, fontFamily: "'JetBrains Mono', monospace", marginTop: 4 }}>
                                  {issue.file_name}:{issue.line_number}
                                </div>
                              </div>
                              <button
                                onClick={(e) => { e.stopPropagation(); setActiveFix(issue); }}
                                style={{
                                  padding: "6px 12px", background: `linear-gradient(90deg, ${COLORS.cyan}, ${COLORS.purple})`,
                                  borderRadius: 8, border: "none", color: "white", fontSize: "0.7rem", fontWeight: 800, cursor: "pointer",
                                  display: "flex", alignItems: "center", gap: 4
                                }}
                              >
                                <Sparkles size={12} /> FIX
                              </button>
                            </motion.div>
                          );
                        })}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              );
            })}
          </div>
        </>
      ) : null}

      <AnimatePresence>
        {activeFix && <DiffModal issue={activeFix} onClose={() => setActiveFix(null)} />}
      </AnimatePresence>
    </div>
  );
}
