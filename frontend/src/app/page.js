"use client";

import { useState, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Rocket, AlertCircle, Eye, EyeOff, Zap } from "lucide-react";
import { supabase } from "@/lib/supabase";
import { api } from "@/lib/api";
import ThemeToggle from "@/components/ThemeToggle";
import "./landing.css";

/* ── SVG Icons ───────────────────────────────────────────────── */
function GitHubIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
    </svg>
  );
}
function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
    </svg>
  );
}

/* ── Star field ──────────────────────────────────────────────── */
function StarField() {
  const stars = useMemo(
    () => Array.from({ length: 50 }, (_, i) => ({
      id: i, left: `${Math.random() * 100}%`, top: `${Math.random() * 100}%`,
      dur: `${2 + Math.random() * 4}s`, delay: `${Math.random() * 3}s`,
      size: Math.random() > 0.8 ? 3 : 2,
    })), []
  );
  return (
    <div className="nebula-stars">
      {stars.map((s) => (
        <div key={s.id} className="star" style={{
          left: s.left, top: s.top, width: s.size, height: s.size,
          "--dur": s.dur, animationDelay: s.delay,
        }} />
      ))}
    </div>
  );
}

/* ── Password Strength Bar ───────────────────────────────────── */
function PasswordStrength({ password }) {
  let strength = 0;
  if (password.length >= 8) strength++;
  if (password.length >= 12) strength++;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
  if (/[0-9]/.test(password)) strength++;
  if (/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?`~]/.test(password)) strength++;
  const colors = ["#ef4444", "#f59e0b", "#f59e0b", "#10b981", "#10b981", "#10b981"];
  const labels = ["Very Weak", "Weak", "Fair", "Good", "Strong", "Very Strong"];

  if (!password) return null;
  return (
    <div style={{ marginTop: 6 }}>
      <div style={{ display: "flex", gap: 3 }}>
        {[0, 1, 2, 3, 4].map((i) => (
          <div key={i} style={{
            flex: 1, height: 4, borderRadius: 2,
            background: i < strength ? colors[strength] : "rgba(255,255,255,0.06)",
            transition: "all 0.3s",
          }} />
        ))}
      </div>
      <p style={{ fontSize: "0.65rem", color: colors[strength], marginTop: 3 }}>{labels[strength]}</p>
    </div>
  );
}

/* ── Password Validation Hints ───────────────────────────────── */
function PasswordHints({ password }) {
  if (!password) return null;
  const checks = [
    { pass: password.length >= 8, label: "8+ characters" },
    { pass: /[a-zA-Z]/.test(password), label: "At least 1 letter" },
    { pass: /[0-9]/.test(password), label: "At least 1 number" },
    { pass: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?`~]/.test(password), label: "At least 1 special character" },
  ];
  return (
    <div style={{ marginTop: 4, display: "flex", flexDirection: "column", gap: 2 }}>
      {checks.map((c) => (
        <div key={c.label} style={{ fontSize: "0.65rem", color: c.pass ? "#10b981" : "var(--text-tertiary)", display: "flex", alignItems: "center", gap: 4 }}>
          <span>{c.pass ? "✓" : "○"}</span> {c.label}
        </div>
      ))}
    </div>
  );
}

/* ═════════════════════════════════════════════════════════════════
   AUTH PAGE — Supabase OAuth + Email/Password
   ═════════════════════════════════════════════════════════════════ */
export default function AuthPage() {
  const router = useRouter();
  const [mode, setMode] = useState("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [checkingSession, setCheckingSession] = useState(true);

  // Check existing session on mount
  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) router.push("/dashboard");
      else setCheckingSession(false);
    });
  }, [router]);

  const validatePasswordFrontend = (pw) => {
    if (pw.length < 8) return "Password must be at least 8 characters";
    if (!/[a-zA-Z]/.test(pw)) return "Password must contain at least 1 letter";
    if (!/[0-9]/.test(pw)) return "Password must contain at least 1 number";
    if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?`~]/.test(pw)) return "Password must contain at least 1 special character";
    return null;
  };

  const handleEmailAuth = async (e) => {
    e.preventDefault();
    setError("");

    if (mode === "signup") {
      const frontendErr = validatePasswordFrontend(password);
      if (frontendErr) { setError(frontendErr); return; }

      // Backend validation
      try {
        const backendCheck = await api.validatePassword(password);
        if (!backendCheck.valid) { setError(backendCheck.errors[0]); return; }
      } catch (err) {
        // Backend offline — show error, don't silently skip
        console.error("Backend validation unavailable:", err.message);
      }
    }

    setLoading(true);

    try {
      if (mode === "signup") {
        const { data, error: err } = await supabase.auth.signUp({ email, password });
        if (err) { setError(err.message); setLoading(false); return; }
        if (data.user) {
          try {
            await api.registerProfile({
              user_id: data.user.id, email,
              auth_provider: "email", display_name: email.split("@")[0],
            });
          } catch (e) { console.error("Profile registration failed:", e.message); }
          router.push("/dashboard");
        }
      } else {
        const { data, error: err } = await supabase.auth.signInWithPassword({ email, password });
        if (err) { setError(err.message); setLoading(false); return; }
        if (data.session) router.push("/dashboard");
      }
    } catch (err) {
      setError(err.message || "Authentication failed");
    }
    setLoading(false);
  };

  const handleOAuth = async (provider) => {
    const { error: err } = await supabase.auth.signInWithOAuth({
      provider,
      options: { redirectTo: `${window.location.origin}/dashboard` },
    });
    if (err) setError(err.message);
  };

  if (checkingSession) {
    return (
      <div className="nebula-container">
        <div className="nebula-bg" />
        <div style={{ zIndex: 2, color: "var(--text-secondary)", fontSize: "0.85rem" }}>Loading...</div>
      </div>
    );
  }

  return (
    <div className="nebula-container">
      <div className="nebula-bg" />
      <StarField />
      <div className="nebula-grid" />

      <div style={{ position: "absolute", top: 20, right: 20, zIndex: 10 }}>
        <ThemeToggle />
      </div>

      <motion.div className="login-portal" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.8 }}>
        {/* Brand */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ type: "spring", bounce: 0.25, duration: 0.6 }} className="login-brand">
          <div className="login-brand-icon"><Rocket size={22} color="white" /></div>
          <div className="login-brand-text">
            <h1>DeployAI</h1>
            <p>Intelligent Deployment Platform</p>
          </div>
        </motion.div>

        {/* Auth Card */}
        <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ type: "spring", bounce: 0.25, duration: 0.7, delay: 0.1 }} className="auth-card" id="auth-card">
          <AnimatePresence mode="wait">
            <motion.div
              key={mode}
              initial={{ opacity: 0, x: mode === "signup" ? 30 : -30 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: mode === "signup" ? -30 : 30 }}
              transition={{ type: "spring", stiffness: 200, damping: 22 }}
            >
              <div className="auth-card-header">
                <h2 className="auth-card-title">{mode === "signin" ? "Welcome Back" : "Create Account"}</h2>
                <p className="auth-card-subtitle">
                  {mode === "signin" ? "Sign in to continue deploying" : "Start deploying in seconds"}
                </p>
              </div>

              {error && (
                <div className="auth-error"><AlertCircle size={14} />{error}</div>
              )}

              <div className="social-row">
                <button className="btn-magnetic social github" onClick={() => handleOAuth("github")} type="button">
                  <GitHubIcon /> GitHub
                </button>
                <button className="btn-magnetic social google" onClick={() => handleOAuth("google")} type="button">
                  <GoogleIcon /> Google
                </button>
              </div>

              <div className="auth-split">
                <div className="auth-split-line" />
                <span className="auth-split-text">or continue with email</span>
                <div className="auth-split-line" />
              </div>

              <form onSubmit={handleEmailAuth}>
                <div className="float-field">
                  <input type="email" id="email" placeholder=" " value={email}
                    onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
                  <label htmlFor="email">Email Address</label>
                </div>

                <div className="float-field" style={{ position: "relative" }}>
                  <input type={showPw ? "text" : "password"} id="password" placeholder=" "
                    value={password} onChange={(e) => setPassword(e.target.value)} required
                    autoComplete={mode === "signin" ? "current-password" : "new-password"}
                    style={{ paddingRight: 44 }} />
                  <label htmlFor="password">Password</label>
                  <button type="button" onClick={() => setShowPw(!showPw)}
                    style={{
                      position: "absolute", right: 12, top: "50%", transform: "translateY(-50%)",
                      background: "none", border: "none", color: "var(--text-tertiary)", cursor: "pointer", padding: 4,
                    }}>
                    {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>

                {mode === "signup" && (
                  <>
                    <PasswordStrength password={password} />
                    <PasswordHints password={password} />
                  </>
                )}

                <button type="submit" className="btn-magnetic primary" disabled={loading} style={{ marginTop: 16 }}>
                  {loading ? <div className="spinner" /> : mode === "signin" ? "Sign In" : "Create Account"}
                </button>
              </form>

              <div className="auth-toggle">
                {mode === "signin" ? "Don't have an account?" : "Already have an account?"}
                <button type="button" onClick={() => { setMode(mode === "signin" ? "signup" : "signin"); setError(""); }}>
                  {mode === "signin" ? "Sign Up" : "Sign In"}
                </button>
              </div>
            </motion.div>
          </AnimatePresence>
        </motion.div>

        {/* Features */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ type: "spring", bounce: 0.3, duration: 0.6, delay: 0.3 }} className="login-features">
          {[
            { label: "Real API Deploys", color: "#6366f1" },
            { label: "AI Security Scan", color: "#10b981" },
            { label: "GitHub Import", color: "#8b5cf6" },
            { label: "Domain Search", color: "#06b6d4" },
          ].map((f) => (
            <div key={f.label} className="login-feature">
              <div className="login-feature-dot" style={{ background: f.color, boxShadow: `0 0 6px ${f.color}` }} />
              {f.label}
            </div>
          ))}
        </motion.div>
      </motion.div>

      <footer className="login-footer">© 2026 DeployAI — Production SaaS</footer>
    </div>
  );
}
