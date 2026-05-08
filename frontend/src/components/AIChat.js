"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageCircle, Send, Bot, User, Sparkles, Terminal as TermIcon, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";

const INITIAL_MESSAGES = [
  {
    role: "assistant",
    content:
      "Hello! I'm the Owl Guide 🦉 — your AI deployment assistant powered by NVIDIA NIM. Drop your project above or ask me about deploying, domains, or optimizing your stack!",
  },
];

export default function AIChat({ inline = false, projectContext = "" }) {
  const [messages, setMessages] = useState(INITIAL_MESSAGES);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [isOpen, setIsOpen] = useState(inline);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, isTyping]);

  const handleSend = async () => {
    if (!input.trim()) return;
    const userMsg = { role: "user", content: input.trim() };
    setMessages((prev) => [...prev, userMsg]);
    const query = input.trim();
    setInput("");
    setIsTyping(true);

    try {
      const result = await api.askAI(query, projectContext);
      const reply = result.response || "Sorry, I couldn't process that request.";
      const isSRE = result.agent === "SRE";

      const assistantMsg = {
        role: "assistant",
        content: reply,
        agent: result.agent,
        diagnosis: result.diagnosis || null,
      };
      setMessages((prev) => [...prev, assistantMsg]);

      // If SRE mode and there's a ghost command, add it as a special message
      if (isSRE && result.diagnosis?.ghost_command) {
        setMessages((prev) => [
          ...prev,
          {
            role: "ghost",
            content: result.diagnosis.ghost_command,
          },
        ]);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `❌ **AI service unavailable**: ${err.message}. Please ensure the backend is running at localhost:8000.`,
          agent: "System",
        },
      ]);
    }
    setIsTyping(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!inline) {
    return (
      <>
        <motion.button
          onClick={() => setIsOpen(!isOpen)}
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.95 }}
          animate={{ y: [0, -5, 0] }}
          transition={{
            y: { duration: 3, repeat: Infinity, ease: "easeInOut" },
            scale: { type: "spring", stiffness: 300, damping: 20 }
          }}
          style={{
            position: "fixed", bottom: 32, right: 32,
            width: 60, height: 60, borderRadius: "50%",
            zIndex: 10000, 
            background: "linear-gradient(135deg, rgba(255,255,255,0.1), rgba(255,255,255,0.05))",
            backdropFilter: "blur(12px)",
            border: "1px solid rgba(255,255,255,0.2)",
            boxShadow: "0 0 30px rgba(118, 185, 0, 0.5), inset 0 1px 1px rgba(255,255,255,0.4)",
            display: "flex", alignItems: "center", justifyContent: "center",
            cursor: "pointer", color: "white"
          }}
        >
          <Bot size={28} />
        </motion.button>
        <AnimatePresence>
          {isOpen && (
            <motion.div
              initial={{ opacity: 0, y: 40, x: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, x: 0, scale: 1 }}
              exit={{ opacity: 0, y: 40, x: 20, scale: 0.95 }}
              transition={{ type: "spring", stiffness: 250, damping: 25 }}
              className="glass-panel-static"
              style={{
                position: "fixed", bottom: 108, right: 32,
                width: 400, height: 600, zIndex: 9999,
                display: "flex", flexDirection: "column", overflow: "hidden",
                background: "rgba(10, 14, 26, 0.65)",
                border: "1px solid rgba(255, 255, 255, 0.15)",
                boxShadow: "0 24px 64px rgba(0, 0, 0, 0.6), 0 0 80px rgba(118, 185, 0, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.3)",
                backdropFilter: "blur(20px)",
                fontFamily: "var(--font-primary)",
              }}
            >
              <ChatContent
                messages={messages} input={input} setInput={setInput}
                isTyping={isTyping} onSend={handleSend} onKeyDown={handleKeyDown}
                scrollRef={scrollRef}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      <ChatContent
        messages={messages} input={input} setInput={setInput}
        isTyping={isTyping} onSend={handleSend} onKeyDown={handleKeyDown}
        scrollRef={scrollRef}
      />
    </div>
  );
}

function ChatContent({ messages, input, setInput, isTyping, onSend, onKeyDown, scrollRef }) {
  return (
    <>
      {/* Header */}
      <div style={{
        display: "flex", alignItems: "center", gap: 10,
        padding: "14px 16px", borderBottom: "1px solid var(--glass-border)",
        background: "rgba(0, 0, 0, 0.2)", flexShrink: 0,
      }}>
        <div style={{
          width: 32, height: 32, borderRadius: "50%",
          background: "linear-gradient(135deg, var(--color-electric-indigo), var(--color-violet-accent))",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <Sparkles size={16} color="white" />
        </div>
        <div>
          <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-primary)" }}>Owl Guide</div>
          <div style={{ fontSize: "0.65rem", color: "var(--color-emerald-neon)", display: "flex", alignItems: "center", gap: 4 }}>
            <div style={{ width: 5, height: 5, borderRadius: "50%", background: "var(--color-emerald-neon)" }} />
            NVIDIA NIM Active
          </div>
        </div>
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
              /* Ghost Command */
              <div style={{
                width: "100%", padding: "10px 14px", borderRadius: "var(--radius-md)",
                background: "rgba(16, 185, 129, 0.08)", border: "1px solid rgba(16, 185, 129, 0.15)",
                fontFamily: "'JetBrains Mono', monospace", fontSize: "0.78rem",
                color: "var(--color-emerald-neon)", display: "flex", alignItems: "center", gap: 8,
              }}>
                <TermIcon size={14} />
                <span style={{ opacity: 0.6 }}>$</span> {msg.content}
                <span style={{ marginLeft: "auto", fontSize: "0.65rem", color: "var(--text-tertiary)" }}>Ghost Cmd</span>
              </div>
            ) : (
              <>
                <div style={{
                  width: 28, height: 28, borderRadius: "50%",
                  background: msg.role === "assistant"
                    ? "linear-gradient(135deg, var(--color-electric-indigo-dim), rgba(139, 92, 246, 0.15))"
                    : "rgba(255, 255, 255, 0.06)",
                  display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                }}>
                  {msg.role === "assistant" ? <Bot size={14} color="var(--color-electric-indigo)" /> : <User size={14} color="var(--text-secondary)" />}
                </div>
                <div style={{
                  maxWidth: "80%", padding: "10px 14px",
                  borderRadius: msg.role === "user"
                    ? "var(--radius-md) var(--radius-md) 4px var(--radius-md)"
                    : "var(--radius-md) var(--radius-md) var(--radius-md) 4px",
                  background: msg.role === "user"
                    ? "linear-gradient(135deg, var(--color-electric-indigo), var(--color-violet-accent))"
                    : "rgba(255, 255, 255, 0.04)",
                  border: msg.role === "assistant" ? "1px solid var(--glass-border)" : "none",
                  fontSize: "0.82rem", lineHeight: 1.6,
                  color: msg.role === "user" ? "white" : "var(--text-primary)",
                }}>
                  {msg.agent === "SRE" && (
                    <div style={{ display: "flex", alignItems: "center", gap: 4, marginBottom: 6, fontSize: "0.65rem", color: "var(--color-amber-warning)" }}>
                      <AlertTriangle size={10} /> SRE Mode
                    </div>
                  )}
                  {msg.content}
                </div>
              </>
            )}
          </motion.div>
        ))}

        {isTyping && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <div style={{
              width: 28, height: 28, borderRadius: "50%",
              background: "linear-gradient(135deg, var(--color-electric-indigo-dim), rgba(139, 92, 246, 0.15))",
              display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
            }}>
              <Bot size={14} color="var(--color-electric-indigo)" />
            </div>
            <div style={{ display: "flex", gap: 4, padding: "12px 16px" }}>
              {[0, 1, 2].map((i) => (
                <motion.div key={i} animate={{ y: [0, -6, 0] }} transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15 }}
                  style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--color-electric-indigo)" }}
                />
              ))}
            </div>
          </motion.div>
        )}
      </div>

      {/* Input */}
      <div style={{
        padding: "12px 16px", borderTop: "1px solid var(--glass-border)",
        display: "flex", gap: 8, flexShrink: 0, background: "rgba(0, 0, 0, 0.15)",
      }}>
        <input
          type="text" value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={onKeyDown}
          placeholder="Ask the Owl anything..." id="ai-chat-input"
          style={{ flex: 1, padding: "10px 14px", fontSize: "0.82rem" }}
        />
        <button className="btn btn-primary btn-icon" onClick={onSend} disabled={!input.trim()}
          style={{ width: 40, height: 40 }} id="ai-chat-send"
        >
          <Send size={16} />
        </button>
      </div>
    </>
  );
}
