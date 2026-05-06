"use client";
import { motion } from "framer-motion";
import { HelpCircle, BookOpen, MessageCircle, ExternalLink } from "lucide-react";

export default function HelpPage() {
  return (
    <div>
      <div className="main-header">
        <div>
          <h1 className="text-gradient">Help & Support</h1>
          <p style={{ fontSize: "0.82rem", color: "var(--text-tertiary)", marginTop: 4 }}>
            Get started with AutoDeploy AI
          </p>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 16 }}>
        {[
          { icon: BookOpen, title: "Quick Start Guide", desc: "Upload a .zip or select a folder to deploy in seconds.", color: "#6366f1" },
          { icon: MessageCircle, title: "AI Assistant", desc: "Use the Owl Guide (right panel) to ask deployment questions.", color: "#8b5cf6" },
          { icon: HelpCircle, title: "Keyboard Shortcuts", desc: "Press Ctrl + ` to toggle the cinematic terminal overlay.", color: "#06b6d4" },
          { icon: ExternalLink, title: "Platform Docs", desc: "Visit Vercel, Netlify, or Cloudflare docs for platform-specific help.", color: "#10b981" },
        ].map((item, i) => (
          <motion.div
            key={item.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08 }}
            className="glass-panel"
            style={{ padding: 24 }}
          >
            <item.icon size={24} color={item.color} style={{ marginBottom: 12 }} />
            <h3 style={{ fontSize: "0.95rem", marginBottom: 6 }}>{item.title}</h3>
            <p style={{ fontSize: "0.78rem", color: "var(--text-tertiary)", lineHeight: 1.5 }}>{item.desc}</p>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
