"use client";

import { motion } from "framer-motion";
import { Check, X, Crown, Sparkles, Zap } from "lucide-react";

const FREE_FEATURES = [
  { label: "100GB Bandwidth / month", available: true },
  { label: "Sleeps after 15 min inactivity", available: true, warning: true },
  { label: "Shared SSL Certificate", available: true },
  { label: "Community Support", available: true },
  { label: "Custom Domain", available: false },
  { label: "24/7 Uptime Guarantee", available: false },
  { label: "Global Edge Network", available: false },
  { label: "Priority Builds", available: false },
];

const PAID_FEATURES = [
  { label: "Unlimited Bandwidth", available: true },
  { label: "Always On — No Sleep", available: true, highlight: true },
  { label: "Auto SSL + Wildcard", available: true },
  { label: "24/7 Priority Support", available: true, highlight: true },
  { label: "Custom Domain Included", available: true },
  { label: "99.99% Uptime SLA", available: true, highlight: true },
  { label: "Global Edge (300+ PoPs)", available: true },
  { label: "Priority Build Queue", available: true },
];

function FeatureRow({ feature, isPaid }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: isPaid ? 10 : -10 }}
      animate={{ opacity: 1, x: 0 }}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "8px 0",
        borderBottom: "1px solid rgba(255,255,255,0.03)",
      }}
    >
      {feature.available ? (
        <div
          style={{
            width: 20,
            height: 20,
            borderRadius: "50%",
            background: feature.highlight
              ? "var(--color-emerald-neon-dim)"
              : "rgba(255,255,255,0.05)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Check
            size={12}
            color={
              feature.highlight
                ? "var(--color-emerald-neon)"
                : "var(--text-secondary)"
            }
          />
        </div>
      ) : (
        <div
          style={{
            width: 20,
            height: 20,
            borderRadius: "50%",
            background: "var(--color-rose-dim)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <X size={12} color="var(--color-rose-danger)" />
        </div>
      )}
      <span
        style={{
          fontSize: "0.82rem",
          color: feature.available
            ? feature.warning
              ? "var(--color-amber-warning)"
              : "var(--text-primary)"
            : "var(--text-tertiary)",
          fontWeight: feature.highlight ? 600 : 400,
          textDecoration: !feature.available ? "line-through" : "none",
          opacity: !feature.available ? 0.5 : 1,
        }}
      >
        {feature.label}
      </span>
    </motion.div>
  );
}

export default function ComparisonMatrix() {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: 16,
        width: "100%",
      }}
    >
      {/* Free Tier */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="glass-panel"
        style={{ padding: "24px 20px", position: "relative" }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            marginBottom: 20,
          }}
        >
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: "var(--radius-md)",
              background: "rgba(255,255,255,0.05)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Zap size={18} color="var(--text-secondary)" />
          </div>
          <div>
            <h4 style={{ fontSize: "1rem", fontWeight: 700 }}>Free</h4>
            <p
              style={{
                fontSize: "0.72rem",
                color: "var(--text-tertiary)",
              }}
            >
              Perfect for testing
            </p>
          </div>
          <div
            style={{
              marginLeft: "auto",
              fontSize: "1.5rem",
              fontWeight: 800,
              color: "var(--text-secondary)",
            }}
          >
            $0
          </div>
        </div>

        {FREE_FEATURES.map((f, i) => (
          <FeatureRow key={i} feature={f} isPaid={false} />
        ))}
      </motion.div>

      {/* Pro Tier */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="glass-panel"
        style={{
          padding: "24px 20px",
          position: "relative",
          borderColor: "rgba(99, 102, 241, 0.2)",
          background:
            "linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(139, 92, 246, 0.03) 100%)",
        }}
      >
        {/* Recommended Badge */}
        <div
          style={{
            position: "absolute",
            top: -1,
            left: 20,
            right: 20,
            height: 2,
            background:
              "linear-gradient(90deg, var(--color-electric-indigo), var(--color-violet-accent), var(--color-pink-accent))",
            borderRadius: "0 0 2px 2px",
          }}
        />

        <div
          style={{
            position: "absolute",
            top: 12,
            right: 16,
          }}
        >
          <span className="badge badge-indigo">
            <Crown size={10} /> Recommended
          </span>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            marginBottom: 20,
          }}
        >
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: "var(--radius-md)",
              background:
                "linear-gradient(135deg, var(--color-electric-indigo-dim), rgba(139, 92, 246, 0.15))",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Sparkles size={18} color="var(--color-electric-indigo)" />
          </div>
          <div>
            <h4 style={{ fontSize: "1rem", fontWeight: 700 }}>Pro</h4>
            <p
              style={{
                fontSize: "0.72rem",
                color: "var(--text-tertiary)",
              }}
            >
              Production-grade
            </p>
          </div>
          <div style={{ marginLeft: "auto", textAlign: "right" }}>
            <span
              style={{
                fontSize: "1.5rem",
                fontWeight: 800,
                background:
                  "linear-gradient(135deg, var(--color-electric-indigo), var(--color-violet-accent))",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}
            >
              $20
            </span>
            <span
              style={{
                fontSize: "0.7rem",
                color: "var(--text-tertiary)",
                marginLeft: 2,
              }}
            >
              /mo
            </span>
          </div>
        </div>

        {PAID_FEATURES.map((f, i) => (
          <FeatureRow key={i} feature={f} isPaid={true} />
        ))}
      </motion.div>
    </div>
  );
}
