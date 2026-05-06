"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { User, Key, Palette } from "lucide-react";
import { supabase } from "@/lib/supabase";

export default function SettingsPage() {
  const [user, setUser] = useState(null);

  useEffect(() => {
    const getUser = async () => {
      const { data, error } = await supabase.auth.getUser();

      if (error) {
        console.error("Error fetching user:", error.message);
        return;
      }

      setUser(data.user);
    };

    getUser();
  }, []);

  return (
    <div>
      {/* HEADER */}
      <div className="main-header">
        <div>
          <h1 className="text-gradient">Settings</h1>
          <p
            style={{
              fontSize: "0.82rem",
              color: "var(--text-tertiary)",
              marginTop: 4,
            }}
          >
            Manage your account, API keys, and preferences
          </p>
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        
        {/* PROFILE */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel"
          style={{ padding: 24 }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
            <User size={18} color="var(--color-electric-indigo)" />
            <h3 style={{ fontSize: "0.95rem" }}>Profile</h3>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <label style={labelStyle}>Name</label>
              <input
                type="text"
                defaultValue={
                  user?.user_metadata?.full_name ||
                  user?.email?.split("@")[0] ||
                  ""
                }
                style={inputStyle}
              />
            </div>

            <div>
              <label style={labelStyle}>Email</label>
              <input
                type="email"
                defaultValue={user?.email || ""}
                style={inputStyle}
                readOnly
              />
            </div>
          </div>

          <div style={{ marginTop: 8, fontSize: "0.72rem", color: "var(--text-tertiary)" }}>
            Provider:{" "}
            <span style={{ color: "var(--color-electric-indigo)", fontWeight: 700 }}>
              {user?.app_metadata?.provider || "email"}
            </span>
          </div>
        </motion.div>

        {/* SERVICE STATUS */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="glass-panel"
          style={{ padding: 24 }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
            <Key size={18} color="var(--color-amber-warning)" />
            <h3 style={{ fontSize: "0.95rem" }}>Service Status</h3>
          </div>

          {[
            { label: "Supabase Auth", status: "connected", color: "#10b981" },
            { label: "NVIDIA NIM", status: "connected", color: "#10b981" },
            { label: "Vercel", status: "connected", color: "#10b981" },
            { label: "Netlify", status: "connected", color: "#10b981" },
            { label: "Serper", status: "connected", color: "#10b981" },
          ].map((key) => (
            <div
              key={key.label}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "8px 0",
                borderBottom: "1px solid var(--glass-border)",
                fontSize: "0.82rem",
              }}
            >
              <span>{key.label}</span>
              <span style={{ color: key.color, fontWeight: 600, fontSize: "0.72rem" }}>
                ● {key.status}
              </span>
            </div>
          ))}
        </motion.div>

        {/* APPEARANCE */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="glass-panel"
          style={{ padding: 24 }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
            <Palette size={18} color="var(--color-violet-accent)" />
            <h3 style={{ fontSize: "0.95rem" }}>Appearance</h3>
          </div>

          <p style={{ fontSize: "0.78rem", color: "var(--text-tertiary)" }}>
            Use the theme toggle to switch between{" "}
            <strong style={{ color: "var(--text-primary)" }}>Dark</strong>,{" "}
            <strong style={{ color: "var(--text-primary)" }}>Light</strong>, and{" "}
            <strong style={{ color: "var(--text-primary)" }}>Gradient</strong>.
          </p>
        </motion.div>
      </div>
    </div>
  );
}

/* STYLES */
const labelStyle = {
  fontSize: "0.72rem",
  color: "var(--text-tertiary)",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
};

const inputStyle = {
  width: "100%",
  marginTop: 4,
  padding: "8px 12px",
  fontSize: "0.85rem",
};