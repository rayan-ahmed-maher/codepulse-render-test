"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Activity, Clock, Globe, CheckCircle, XCircle, Loader } from "lucide-react";
import { api } from "@/lib/api";

export default function AnalyticsPage() {
  const [deployments, setDeployments] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getDeployList()
      .then((data) => { setDeployments(Array.isArray(data) ? data : []); })
      .catch((err) => {
        console.error("Failed to fetch deployments:", err.message);
        setDeployments([]);
      })
      .finally(() => setLoading(false));
  }, []);

  const statusIcon = (s) => {
    if (s === "READY") return <CheckCircle size={14} color="#10b981" />;
    if (s === "FAILED") return <XCircle size={14} color="#ef4444" />;
    return <Loader size={14} color="#f59e0b" />;
  };

  return (
    <div>
      <div className="main-header">
        <div>
          <h1 className="text-gradient">Analytics</h1>
          <p style={{ fontSize: "0.82rem", color: "var(--text-tertiary)", marginTop: 4 }}>
            Deployment history and performance metrics
          </p>
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: "center", padding: 40, color: "var(--text-tertiary)" }}>Loading deployment history...</div>
      ) : deployments.length === 0 ? (
        <div style={{ textAlign: "center", padding: 40, color: "var(--text-tertiary)" }}>
          <Activity size={48} style={{ opacity: 0.2, marginBottom: 12 }} />
          <p>No deployments yet. Deploy your first project to see analytics here.</p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div className="section-label">Deployment History</div>
          {deployments.map((d, i) => (
            <motion.div
              key={d.id || i}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.06 }}
              className="glass-panel"
              style={{
                padding: "14px 20px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                {statusIcon(d.status)}
                <div>
                  <div style={{ fontSize: "0.88rem", fontWeight: 600 }}>{d.project_name || d.id}</div>
                  <div style={{ fontSize: "0.72rem", color: "var(--text-tertiary)", display: "flex", gap: 8 }}>
                    <span>{d.platform}</span>
                    {d.url && <span style={{ color: "var(--color-cyan-info)" }}>{d.url}</span>}
                    {d.error && <span style={{ color: "#ef4444" }}>{d.error}</span>}
                  </div>
                </div>
              </div>
              <span className="badge" style={{
                background: d.status === "READY" ? "rgba(16,185,129,0.1)" : d.status === "FAILED" ? "rgba(239,68,68,0.1)" : "rgba(245,158,11,0.1)",
                color: d.status === "READY" ? "#10b981" : d.status === "FAILED" ? "#ef4444" : "#f59e0b",
              }}>
                {d.status}
              </span>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
