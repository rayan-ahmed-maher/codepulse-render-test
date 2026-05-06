"use client";
import { useTheme } from "./ThemeProvider";
import { Sun, Moon, Sparkles } from "lucide-react";

const THEMES = [
  { id: "dark", label: "Dark", icon: Moon },
  { id: "light", label: "Light", icon: Sun },
  { id: "gradient", label: "Gradient", icon: Sparkles },
];

export default function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  return (
    <div style={{
      display: "flex", gap: 4, padding: 3,
      background: "var(--glass-bg)", borderRadius: 10,
      border: "1px solid var(--glass-border)",
    }}>
      {THEMES.map((t) => (
        <button
          key={t.id}
          onClick={() => setTheme(t.id)}
          title={t.label}
          style={{
            display: "flex", alignItems: "center", justifyContent: "center",
            width: 32, height: 28, borderRadius: 8,
            border: "none", cursor: "pointer",
            background: theme === t.id ? "var(--color-electric-indigo)" : "transparent",
            color: theme === t.id ? "#fff" : "var(--text-tertiary)",
            transition: "all 0.2s",
          }}
        >
          <t.icon size={14} />
        </button>
      ))}
    </div>
  );
}
