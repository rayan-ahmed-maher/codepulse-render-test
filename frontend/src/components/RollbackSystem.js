"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  History, RotateCcw, Trash2, ExternalLink, ChevronRight,
  Loader2, CheckCircle2, AlertTriangle, X, Clock, Server,
  ArrowRight, Rocket
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
  textTer: "rgba(255,255,255,0.4)",
  border: "rgba(255,255,255,0.1)",
};

const PLATFORM_GRADIENTS = {
  vercel: "linear-gradient(135deg, #000 0%, #333 100%)",
  netlify: "linear-gradient(135deg, #00ada8 0%, #006b6b 100%)",
  cloudflare: "linear-gradient(135deg, #f59e0b 0%, #d97706 100%)",
  render: "linear-gradient(135deg, #7C3AED 0%, #5b21b6 100%)",
};

// ── COMPONENT: Success Toast ──
function SuccessToast({ message, url, onClose }) {
  useEffect(() => {
    const timer = setTimeout(onClose, 5000);
    return () => clearTimeout(timer);
  }, [onClose]);

  return (
    <motion.div
      initial={{ x: 300, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 300, opacity: 0 }}
      style={{
        position: "fixed", bottom: 40, right: 40, zIndex: 2000,
        width: 320, padding: "20px", borderRadius: 16,
        background: "linear-gradient(135deg, #065f46 0%, #10b981 100%)",
        boxShadow: "0 20px 50px rgba(0,0,0,0.4), 0 0 30px rgba(16,185,129,0.3)",
        border: "1px solid rgba(255,255,255,0.2)", color: "white",
        overflow: "hidden",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 15 }}>
        <motion.div animate={{ y: [0, -40], opacity: [1, 0] }} transition={{ duration: 1, repeat: Infinity }}>
          <Rocket size={24} />
        </motion.div>
        <div>
          <div style={{ fontWeight: 800, fontSize: "0.95rem" }}>ROLLBACK SUCCESS</div>
          <div style={{ fontSize: "0.8rem", opacity: 0.9 }}>{message}</div>
          {url && (
            <a href={url} target="_blank" rel="noopener noreferrer" style={{ color: "white", textDecoration: "underline", fontSize: "0.75rem", marginTop: 8, display: "block" }}>
              VIEW LIVE SITE <ExternalLink size={10} style={{ display: "inline", marginLeft: 2 }} />
            </a>
          )}
        </div>
      </div>
      {/* Progress Bar */}
      <motion.div
        initial={{ width: "100%" }}
        animate={{ width: "0%" }}
        transition={{ duration: 5, ease: "linear" }}
        style={{ position: "absolute", bottom: 0, left: 0, height: 4, background: "rgba(255,255,255,0.4)" }}
      />
    </motion.div>
  );
}

// ── COMPONENT: Rollback Confirmation Modal ──
function RollbackModal({ target, current, onConfirm, onClose, loading }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      style={{
        position: "fixed", inset: 0, zIndex: 1100,
        background: "rgba(0,0,0,0.85)", backdropFilter: "blur(15px)",
        display: "flex", alignItems: "center", justifyContent: "center",
      }}
    >
      <motion.div
        initial={{ y: -100, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ type: "spring", damping: 20 }}
        style={{
          width: 500, background: "rgba(15, 20, 35, 0.95)", borderRadius: 24, padding: 32,
          border: `1px solid ${COLORS.amber}33`, boxShadow: "0 40px 100px rgba(0,0,0,0.8)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 24 }}>
          <h3 style={{ display: "flex", alignItems: "center", gap: 10, color: COLORS.amber, fontWeight: 900 }}>
            <RotateCcw size={22} /> CONFIRM ROLLBACK
          </h3>
          <button onClick={onClose} style={{ background: "none", border: "none", color: "white", cursor: "pointer" }}><X size={24} /></button>
        </div>

        {/* Animated Comparison */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, marginBottom: 32 }}>
          <div style={{ flex: 1, padding: 16, background: "rgba(239,68,68,0.1)", borderRadius: 16, border: "1px solid rgba(239,68,68,0.2)", textAlign: "center" }}>
            <div style={{ fontSize: "0.6rem", fontWeight: 900, color: COLORS.red, marginBottom: 8 }}>CURRENT ACTIVE</div>
            <div style={{ fontFamily: "JetBrains Mono", fontSize: "1.1rem", color: "white" }}>v{current?.version_number || "?"}</div>
          </div>
          
          <motion.div animate={{ x: [0, 10, 0] }} transition={{ repeat: Infinity, duration: 1.5 }}>
            <ArrowRight size={24} color={COLORS.amber} />
          </motion.div>

          <div style={{ flex: 1, padding: 16, background: "rgba(0,255,136,0.1)", borderRadius: 16, border: "1px solid rgba(0,255,136,0.2)", textAlign: "center" }}>
            <div style={{ fontSize: "0.6rem", fontWeight: 900, color: COLORS.green, marginBottom: 8 }}>TARGET VERSION</div>
            <div style={{ fontFamily: "JetBrains Mono", fontSize: "1.1rem", color: "white" }}>v{target.version_number}</div>
          </div>
        </div>

        <p style={{ color: COLORS.textSec, fontSize: "0.9rem", textAlign: "center", marginBottom: 32 }}>
          Warning: This will override your current production deployment with the build from v{target.version_number}.
        </p>

        <div style={{ display: "flex", gap: 12 }}>
          <button onClick={onClose} style={{ flex: 1, padding: 16, background: "rgba(255,255,255,0.05)", border: "none", borderRadius: 12, color: "white", fontWeight: 700, cursor: "pointer" }}>CANCEL</button>
          <motion.button
            animate={{ boxShadow: [`0 0 0px ${COLORS.amber}00`, `0 0 20px ${COLORS.amber}44`, `0 0 0px ${COLORS.amber}00`] }}
            transition={{ repeat: Infinity, duration: 3 }}
            onClick={onConfirm}
            disabled={loading}
            style={{
              flex: 1.5, padding: 16, background: `linear-gradient(90deg, ${COLORS.amber}, #d97706)`,
              border: "none", borderRadius: 12, color: "black", fontWeight: 900, cursor: "pointer",
              display: "flex", alignItems: "center", justifyContent: "center", gap: 8
            }}
          >
            {loading ? <Loader2 size={20} className="animate-spin" /> : <RotateCcw size={20} />}
            CONFIRM ROLLBACK
          </motion.button>
        </div>
      </motion.div>
    </motion.div>
  );
}

// ── MAIN COMPONENT ──
export default function RollbackSystem({ projectId, userId }) {
  const [versions, setVersions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [rollbackTarget, setRollbackTarget] = useState(null);
  const [rollbackLoading, setRollbackLoading] = useState(false);
  const [toast, setToast] = useState(null);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const res = await api.getRollbackHistory(projectId);
      setVersions(res.versions || []);
    } catch {}
    setLoading(false);
  };

  useEffect(() => { if (projectId) fetchHistory(); }, [projectId]);

  const handleRollback = async () => {
    setRollbackLoading(true);
    try {
      const res = await api.executeRollback(projectId, rollbackTarget.version_number, userId);
      if (res.status === "success") {
        setToast({ message: `Reverted to v${rollbackTarget.version_number}`, url: res.url });
        setRollbackTarget(null);
        fetchHistory();
      }
    } catch {}
    setRollbackLoading(false);
  };

  return (
    <div style={{
      background: "rgba(10, 15, 30, 0.7)", backdropFilter: "blur(20px)",
      border: `1px solid ${COLORS.border}`, borderRadius: 32, padding: 40,
      position: "relative", boxShadow: "0 40px 100px rgba(0,0,0,0.5)",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 40 }}>
        <h3 style={{ fontSize: "1.2rem", fontWeight: 900, color: "white", letterSpacing: "1px", display: "flex", alignItems: "center", gap: 12 }}>
          <History size={22} color={COLORS.cyan} /> DEPLOYMENT TIMELINE
        </h3>
        <div style={{ fontSize: "0.75rem", color: COLORS.textTer, fontWeight: 700 }}>{versions.length} SNAPSHOTS STORED</div>
      </div>

      {loading ? (
        <div style={{ padding: 100, textAlign: "center" }}><Loader2 size={40} className="animate-spin" color={COLORS.cyan} /></div>
      ) : (
        <div style={{ position: "relative", paddingLeft: 30 }}>
          {/* Vertical Timeline Line */}
          <div style={{ position: "absolute", top: 0, bottom: 0, left: 10, width: 2, background: `linear-gradient(180deg, ${COLORS.cyan}, transparent)` }} />

          {versions.map((v, i) => {
            const isLatest = i === 0;
            const gradient = PLATFORM_GRADIENTS[v.platform?.toLowerCase()] || PLATFORM_GRADIENTS.vercel;

            return (
              <motion.div
                key={v.version_number}
                initial={{ x: -50, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                transition={{ delay: i * 0.08 }}
                style={{ position: "relative", marginBottom: 24 }}
              >
                {/* Timeline Dot */}
                <div style={{
                  position: "absolute", left: -26, top: 22, width: isLatest ? 14 : 8, height: isLatest ? 14 : 8,
                  borderRadius: "50%", background: isLatest ? COLORS.cyan : "#4b5563",
                  boxShadow: isLatest ? `0 0 15px ${COLORS.cyan}` : "none",
                  zIndex: 10
                }} />

                {/* Card */}
                <div style={{
                  background: isLatest ? "rgba(0,245,255,0.03)" : "rgba(255,255,255,0.02)",
                  border: `1px solid ${isLatest ? COLORS.cyan + "33" : COLORS.border}`,
                  borderRadius: 20, padding: 20, display: "flex", alignItems: "center", gap: 20,
                  boxShadow: isLatest ? `0 10px 30px rgba(0,245,255,0.05)` : "none"
                }}>
                  <div style={{ fontFamily: "JetBrains Mono", fontSize: "1.2rem", fontWeight: 900, color: isLatest ? COLORS.cyan : "white", minWidth: 60 }}>
                    v{v.version_number}
                  </div>

                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                      <span style={{ fontSize: "0.6rem", fontWeight: 900, padding: "2px 8px", borderRadius: 6, background: gradient, color: "white" }}>
                        {v.platform?.toUpperCase()}
                      </span>
                      <span style={{ fontSize: "0.75rem", color: COLORS.textTer, display: "flex", alignItems: "center", gap: 4 }}>
                        <Clock size={12} /> {new Date(v.created_at).toLocaleString()}
                      </span>
                    </div>
                    <a href={v.deployment_url} target="_blank" rel="noopener noreferrer" style={{ fontSize: "0.85rem", color: COLORS.cyan, textDecoration: "none", display: "flex", alignItems: "center", gap: 4 }}>
                      {v.deployment_url?.replace(/https?:\/\//, "")} <ExternalLink size={12} />
                    </a>
                  </div>

                  <div style={{ display: "flex", gap: 10 }}>
                    {!isLatest && (
                      <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={() => setRollbackTarget(v)}
                        style={{
                          padding: "10px 16px", background: "rgba(245,158,11,0.1)", border: `1px solid ${COLORS.amber}33`,
                          borderRadius: 12, color: COLORS.amber, fontSize: "0.75rem", fontWeight: 800, cursor: "pointer",
                          display: "flex", alignItems: "center", gap: 6
                        }}
                      >
                        <RotateCcw size={14} className="hover:rotate-[-360deg] transition-transform duration-500" /> ROLLBACK
                      </motion.button>
                    )}
                    <button style={{ padding: 10, background: "rgba(239,68,68,0.05)", border: "none", borderRadius: 12, color: COLORS.red, cursor: "pointer" }}>
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}

      <AnimatePresence>
        {rollbackTarget && (
          <RollbackModal
            target={rollbackTarget}
            current={versions[0]}
            loading={rollbackLoading}
            onClose={() => setRollbackTarget(null)}
            onConfirm={handleRollback}
          />
        )}
        {toast && <SuccessToast {...toast} onClose={() => setToast(null)} />}
      </AnimatePresence>
    </div>
  );
}
