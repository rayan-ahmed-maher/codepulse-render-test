"use client";
import { motion } from "framer-motion";
import { CreditCard, Wallet } from "lucide-react";

export default function BillingPage() {
  return (
    <div>
      <div className="main-header">
        <div>
          <h1 className="text-gradient">Billing</h1>
          <p style={{ fontSize: "0.82rem", color: "var(--text-tertiary)", marginTop: 4 }}>
            Manage your subscription and payment methods
          </p>
        </div>
      </div>

      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="glass-panel" style={{ padding: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
          <Wallet size={18} color="var(--color-emerald-neon)" />
          <h3 style={{ fontSize: "0.95rem" }}>Current Plan</h3>
        </div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <p style={{ fontSize: "1.2rem", fontWeight: 800, color: "var(--color-emerald-neon)" }}>Free Tier</p>
            <p style={{ fontSize: "0.78rem", color: "var(--text-tertiary)" }}>Unlimited deploys · 100GB bandwidth · Community support</p>
          </div>
          <button className="btn btn-primary">Upgrade to Pro</button>
        </div>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="glass-panel" style={{ padding: 24, marginTop: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
          <CreditCard size={18} color="var(--color-violet-accent)" />
          <h3 style={{ fontSize: "0.95rem" }}>Payment Method</h3>
        </div>
        <p style={{ fontSize: "0.82rem", color: "var(--text-tertiary)" }}>
          No payment method configured. Add UPI or Card to unlock Pro features and domain purchases.
        </p>
        <button className="btn btn-secondary btn-sm" style={{ marginTop: 12 }}>
          Add Payment Method (Razorpay)
        </button>
      </motion.div>
    </div>
  );
}
