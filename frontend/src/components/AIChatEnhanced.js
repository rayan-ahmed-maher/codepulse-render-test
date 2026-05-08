"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  MessageCircle, Send, Bot, User, Sparkles, Search,
  Terminal as TermIcon, AlertTriangle, X, Zap,
} from "lucide-react";
import { api } from "@/lib/api";

const QUICK_CHIPS = [
  { label: "Why did deploy fail?", icon: AlertTriangle },
  { label: "What framework is my project?", icon: Zap },
  { label: "How to fix errors?", icon: Search },
  { label: "Deploy to Vercel", icon: Sparkles },
];

const INITIAL_MESSAGES = [
  {
    role: "assistant",
    content:
      "Hello! I'm the Owl Guide 🦉 — your AI deployment assistant powered by NVIDIA NIM. I can see your full project context. Ask me about deploying, debugging, or optimizing your stack!",
  },
];

export default function AIChatEnhanced({ inline = false, projectContext = {} }) {
  const [messages, setMessages] = useState(INITIAL_MESSAGES);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [isOpen, setIsOpen] = useState(inline);
  const [sessionId] = useState(() => `session_${Date.now()}`);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, isTyping]);

  const handleSend = useCallback(async (text) => {
    const msg = (text || input).trim();
    if (!msg) return;

    const userMsg = { role: "user", content: msg };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    // Detect if searching docs
    const errorKw = ["error", "fail", "crash", "bug", "fix", "broken", "not working", "why"];
    const willSearch = errorKw.some((kw) => msg.toLowerCase().includes(kw));
    if (willSearch) setIsSearching(true);

    try {
      const result = await api.chatMessage(msg, sessionId, projectContext);
      const reply = result.response || "Sorry, I couldn't process that request.";
      const isSRE = result.agent === "SRE";

      const assistantMsg = {
        role: "assistant",
        content: reply,
        agent: result.agent,
        diagnosis: result.diagnosis || null,
        serperUsed: result.serper_used || false,
      };
      setMessages((prev) => [...prev, assistantMsg]);

      // Ghost command
      if (isSRE && result.diagnosis?.ghost_command) {
        setMessages((prev) => [
          ...prev,
          { role: "ghost", content: result.diagnosis.ghost_command },
        ]);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `❌ **AI service unavailable**: ${err.message}. Ensure the backend is running.`,
          agent: "System",
        },
      ]);
    }
    setIsTyping(false);
    setIsSearching(false);
  }, [input, sessionId, projectContext]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const chatPanel = (
    <>
      {/* Header */}
      <div style={{
        display: "flex", alignItems: "center", gap: 10,
        padding: "14px 16px", borderBottom: "1px solid rgba(255,255,255,0.08)",
        background: "rgba(0, 0, 0, 0.2)", flexShrink: 0,
      }}>
        <div style={{
          width: 32, height: 32, borderRadius: "50%",
          background: "linear-gradient(135deg, var(--color-electric-indigo), var(--color-violet-accent))",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <Sparkles size={16} color="white" />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-primary)" }}>Owl Guide</div>
          <div style={{ fontSize: "0.65rem", color: "#10b981", display: "flex", alignItems: "center", gap: 4 }}>
            <div style={{ width: 5, height: 5, borderRadius: "50%", background: "#10b981" }} />
            NVIDIA NIM Active
          </div>
        </div>
        {!inline && (
          <button onClick={() => setIsOpen(false)} style={{
            background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)", padding: 4,
          }}>
            <X size={16} />
          </button>
        )}
      </div>

      {/* Quick Action Chips */}
      <div style={{
        display: "flex", gap: 6, padding: "10px 16px",
        overflowX: "auto", flexShrink: 0,
        borderBottom: "1px solid rgba(255,255,255,0.05)",
      }}>
        {QUICK_CHIPS.map((chip) => (
          <button
            key={chip.label}
            onClick={() => handleSend(chip.label)}
            style={{
              padding: "6px 12px", borderRadius: 20, fontSize: "0.68rem",
              fontWeight: 600, whiteSpace: "nowrap", cursor: "pointer",
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.1)",
              color: "var(--text-secondary)", transition: "all 0.2s",
              display: "flex", alignItems: "center", gap: 4,
            }}
          >
            <chip.icon size={10} />
            {chip.label}
          </button>
        ))}
      </div>

      {/* Messages */}
      <div ref={scrollRef} style={{
        flex: 1, overflowY: "auto", padding: "16px",
        display: "flex", flexDirection: "column", gap: 12,
      }}>
        {messages.map((msg, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ type: "spring", stiffness: 200, damping: 20 }}
            style={{
              display: "flex", gap: 10, alignItems: "flex-start",
              flexDirection: msg.role === "user" ? "row-reverse" : "row",
            }}
          >
            {msg.role === "ghost" ? (
              <div style={{
                width: "100%", padding: "10px 14px", borderRadius: 8,
                background: "rgba(16, 185, 129, 0.08)", border: "1px solid rgba(16, 185, 129, 0.15)",
                fontFamily: "'JetBrains Mono', monospace", fontSize: "0.78rem",
                color: "#10b981", display: "flex", alignItems: "center", gap: 8,
              }}>
                <TermIcon size={14} />
                <span style={{ opacity: 0.6 }}>$</span> {msg.content}
                <span style={{ marginLeft: "auto", fontSize: "0.65rem", color: "var(--text-tertiary)" }}>Ghost Cmd</span>
              </div>
            ) : (
              <>
                <div style={{
                  width: 28, height: 28, borderRadius: "50%", flexShrink: 0,
                  background: msg.role === "assistant"
                    ? "linear-gradient(135deg, rgba(99,102,241,0.2), rgba(139,92,246,0.15))"
                    : "rgba(255,255,255,0.06)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}>
                  {msg.role === "assistant" ? <Bot size={14} color="#6366f1" /> : <User size={14} color="#9ca3af" />}
                </div>
                <div style={{
                  maxWidth: "80%", padding: "10px 14px",
                  borderRadius: msg.role === "user"
                    ? "12px 12px 4px 12px" : "12px 12px 12px 4px",
                  background: msg.role === "user"
                    ? "linear-gradient(135deg, #00D4FF, #0099CC)" : "rgba(255,255,255,0.04)",
                  border: msg.role === "assistant" ? "1px solid rgba(255,255,255,0.08)" : "none",
                  fontSize: "0.82rem", lineHeight: 1.6,
                  color: msg.role === "user" ? "white" : "var(--text-primary)",
                }}>
                  {/* Agent / Serper badges */}
                  {msg.agent === "SRE" && (
                    <div style={{ display: "flex", alignItems: "center", gap: 4, marginBottom: 6, fontSize: "0.65rem", color: "#f59e0b" }}>
                      <AlertTriangle size={10} /> SRE Mode
                    </div>
                  )}
                  {msg.serperUsed && (
                    <div style={{
                      display: "flex", alignItems: "center", gap: 4, marginBottom: 6,
                      fontSize: "0.62rem", color: "#00D4FF",
                      padding: "2px 8px", borderRadius: 12,
                      background: "rgba(0,212,255,0.08)", width: "fit-content",
                    }}>
                      <Search size={9} /> Searched live docs
                    </div>
                  )}
                  {msg.content}
                </div>
              </>
            )}
          </motion.div>
        ))}

        {/* Typing Indicator */}
        {isTyping && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <div style={{
              width: 28, height: 28, borderRadius: "50%",
              background: "linear-gradient(135deg, rgba(99,102,241,0.2), rgba(139,92,246,0.15))",
              display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
            }}>
              <Bot size={14} color="#6366f1" />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <div style={{ display: "flex", gap: 4, padding: "12px 16px" }}>
                {[0, 1, 2].map((i) => (
                  <motion.div
                    key={i}
                    animate={{ y: [0, -6, 0] }}
                    transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15 }}
                    style={{ width: 6, height: 6, borderRadius: "50%", background: "#6366f1" }}
                  />
                ))}
              </div>
              {isSearching && (
                <div style={{
                  fontSize: "0.62rem", color: "#00D4FF", display: "flex",
                  alignItems: "center", gap: 4, paddingLeft: 16,
                }}>
                  <Search size={9} style={{ animation: "pulse 1s infinite" }} />
                  Searching documentation...
                </div>
              )}
            </div>
          </motion.div>
        )}
      </div>

      {/* Input */}
      <div style={{
        padding: "12px 16px", borderTop: "1px solid rgba(255,255,255,0.08)",
        display: "flex", gap: 8, flexShrink: 0, background: "rgba(0, 0, 0, 0.15)",
      }}>
        <input
          type="text" value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about your project..."
          id="ai-chat-input"
          style={{
            flex: 1, padding: "10px 14px", fontSize: "0.82rem",
            background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 8, color: "var(--text-primary)", outline: "none",
          }}
        />
        <button
          onClick={() => handleSend()}
          disabled={!input.trim() || isTyping}
          id="ai-chat-send"
          style={{
            width: 40, height: 40, borderRadius: 8,
            background: input.trim()
              ? "linear-gradient(135deg, #00D4FF, #0099CC)" : "rgba(255,255,255,0.04)",
            border: "none", cursor: input.trim() ? "pointer" : "default",
            display: "flex", alignItems: "center", justifyContent: "center",
            color: "white", transition: "all 0.2s",
          }}
        >
          <Send size={16} />
        </button>
      </div>
    </>
  );

  // ── Inline mode ─────────────────────────────────
  if (inline) {
    return (
      <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
        {chatPanel}
      </div>
    );
  }

  // ── Floating mode ───────────────────────────────
  return (
    <>
      {/* Floating Button */}
      <motion.button
        onClick={() => setIsOpen(!isOpen)}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.95 }}
        style={{
          position: "fixed", bottom: 32, right: 32,
          width: 60, height: 60, borderRadius: "50%",
          zIndex: 10000,
          background: "linear-gradient(135deg, rgba(0,212,255,0.2), rgba(0,212,255,0.05))",
          backdropFilter: "blur(12px)",
          border: "1px solid rgba(0,212,255,0.3)",
          boxShadow: "0 0 30px rgba(0,212,255,0.4), 0 0 60px rgba(0,212,255,0.15)",
          display: "flex", alignItems: "center", justifyContent: "center",
          cursor: "pointer", color: "#00D4FF",
        }}
        id="ai-chat-toggle"
      >
        {/* Pulse ring */}
        <motion.div
          animate={{ scale: [1, 1.4, 1], opacity: [0.4, 0, 0.4] }}
          transition={{ duration: 2, repeat: Infinity }}
          style={{
            position: "absolute", inset: -4, borderRadius: "50%",
            border: "2px solid rgba(0,212,255,0.3)",
          }}
        />
        <Bot size={28} />
      </motion.button>

      {/* Chat Panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 40, x: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, x: 0, scale: 1 }}
            exit={{ opacity: 0, y: 40, x: 20, scale: 0.95 }}
            transition={{ type: "spring", stiffness: 250, damping: 25 }}
            style={{
              position: "fixed", bottom: 108, right: 32,
              width: 400, height: 600, zIndex: 9999,
              display: "flex", flexDirection: "column", overflow: "hidden",
              background: "rgba(10, 14, 26, 0.85)",
              border: "1px solid rgba(255, 255, 255, 0.12)",
              borderRadius: 16,
              boxShadow: "0 24px 64px rgba(0,0,0,0.6), 0 0 80px rgba(0,212,255,0.1), inset 0 1px 0 rgba(255,255,255,0.2)",
              backdropFilter: "blur(24px)",
            }}
          >
            {chatPanel}
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
