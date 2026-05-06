"use client";

import { motion } from "framer-motion";
import { Code2, Globe, Zap, FileCode2 } from "lucide-react";

const TEMPLATES = [
  {
    id: "react",
    name: "React Starter",
    icon: Code2,
    color: "#61dafb",
    bg: "rgba(97, 218, 251, 0.08)",
    glow: "rgba(97, 218, 251, 0.2)",
    desc: "Vite + React 19 with hot reload",
    files: ["package.json", "src/App.jsx", "src/main.jsx", "index.html", "vite.config.js"],
    packageJson: {
      name: "react-starter",
      scripts: { dev: "vite", build: "vite build", preview: "vite preview" },
      dependencies: { react: "^19.0.0", "react-dom": "^19.0.0" },
      devDependencies: { vite: "^6.0.0", "@vitejs/plugin-react": "^4.0.0" },
    },
  },
  {
    id: "static",
    name: "Static Site",
    icon: Globe,
    color: "#10b981",
    bg: "rgba(16, 185, 129, 0.08)",
    glow: "rgba(16, 185, 129, 0.2)",
    desc: "Pure HTML/CSS/JS — zero config",
    files: ["index.html", "style.css", "script.js"],
    packageJson: null,
  },
  {
    id: "python",
    name: "Python API",
    icon: Zap,
    color: "#f59e0b",
    bg: "rgba(245, 158, 11, 0.08)",
    glow: "rgba(245, 158, 11, 0.2)",
    desc: "FastAPI + Uvicorn starter",
    files: ["main.py", "requirements.txt", ".gitignore"],
    packageJson: null,
  },
  {
    id: "nextjs",
    name: "Next.js App",
    icon: FileCode2,
    color: "#fff",
    bg: "rgba(255, 255, 255, 0.05)",
    glow: "rgba(255, 255, 255, 0.1)",
    desc: "Next.js 16 App Router scaffold",
    files: ["package.json", "next.config.mjs", "src/app/page.js", "src/app/layout.js"],
    packageJson: {
      name: "nextjs-starter",
      scripts: { dev: "next dev", build: "next build", start: "next start" },
      dependencies: { next: "^16.0.0", react: "^19.0.0", "react-dom": "^19.0.0" },
    },
  },
];

export default function TemplateCards({ onSelect }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12 }}>
      {TEMPLATES.map((t, i) => (
        <motion.button
          key={t.id}
          onClick={() => onSelect(t)}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.08 }}
          whileHover={{ y: -4, boxShadow: `0 8px 30px ${t.glow}` }}
          style={{
            padding: 20,
            borderRadius: "var(--radius-lg)",
            background: t.bg,
            border: `1px solid ${t.glow}`,
            cursor: "pointer",
            textAlign: "left",
            display: "flex",
            flexDirection: "column",
            gap: 10,
            transition: "all 0.3s ease",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <t.icon size={18} color={t.color} />
            <span style={{ fontSize: "0.88rem", fontWeight: 700, color: "var(--text-primary)" }}>{t.name}</span>
          </div>
          <p style={{ fontSize: "0.72rem", color: "var(--text-tertiary)", lineHeight: 1.4 }}>{t.desc}</p>
          <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
            {t.files.slice(0, 3).map((f) => (
              <span key={f} style={{
                fontSize: "0.6rem", padding: "2px 6px", borderRadius: 4,
                background: "rgba(255,255,255,0.04)", color: "var(--text-tertiary)",
                fontFamily: "monospace",
              }}>
                {f}
              </span>
            ))}
          </div>
        </motion.button>
      ))}
    </div>
  );
}
