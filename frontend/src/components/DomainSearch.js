"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search, Globe, ShoppingCart, X, Check, AlertTriangle,
  Loader2, Crown, Sparkles, ExternalLink, RefreshCw, Trash2,
} from "lucide-react";
import { api } from "@/lib/api";

// ── Skeleton Loader Card ─────────────────────────────────
function SkeletonCard() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      style={{
        padding: "16px 20px",
        borderRadius: 12,
        background: "rgba(255,255,255,0.03)",
        border: "1px solid rgba(255,255,255,0.06)",
        display: "flex", justifyContent: "space-between", alignItems: "center",
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <div style={{ width: 180, height: 16, borderRadius: 6, background: "rgba(255,255,255,0.08)", animation: "pulse 1.5s infinite" }} />
        <div style={{ width: 80, height: 12, borderRadius: 4, background: "rgba(255,255,255,0.05)", animation: "pulse 1.5s infinite" }} />
      </div>
      <div style={{ width: 90, height: 36, borderRadius: 8, background: "rgba(255,255,255,0.06)", animation: "pulse 1.5s infinite" }} />
    </motion.div>
  );
}

export default function DomainSearch({ userId, userEmail }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [cart, setCart] = useState([]);
  const [showCart, setShowCart] = useState(false);
  const [showCheckout, setShowCheckout] = useState(false);
  const [paymentStatus, setPaymentStatus] = useState(null); // null | "processing" | "success" | "error"
  const [paymentError, setPaymentError] = useState("");
  const [registeredDomains, setRegisteredDomains] = useState([]);
  const debounceRef = useRef(null);

  // ── Debounced search (500ms) ───────────────────────────
  const handleSearch = useCallback((value) => {
    setQuery(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (!value.trim() || value.trim().length < 2) {
      setResults([]);
      setSuggestions([]);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const [searchRes, suggestRes] = await Promise.all([
          api.searchDomains(value.trim()),
          api.suggestDomains(value.trim()),
        ]);
        setResults(searchRes.results || []);
        setSuggestions(suggestRes.suggestions || []);
      } catch (err) {
        console.error("Domain search error:", err);
      }
      setLoading(false);
    }, 500);
  }, []);

  // ── Cart Management ────────────────────────────────────
  const addToCart = (domain) => {
    if (!cart.find((d) => d.domain === domain.domain)) {
      setCart((prev) => [...prev, domain]);
      setShowCart(true);
    }
  };

  const removeFromCart = (domainName) => {
    setCart((prev) => prev.filter((d) => d.domain !== domainName));
  };

  const cartTotal = cart.reduce((sum, d) => sum + (d.price_inr || 0), 0);

  // ── Razorpay Checkout ──────────────────────────────────
  const handleCheckout = async () => {
    if (cart.length === 0) return;
    setPaymentStatus("processing");
    setPaymentError("");

    try {
      // Step 1: Create Razorpay order
      const orderRes = await api.createPaymentOrder(
        cart.map((d) => d.domain),
        cartTotal,
        userId,
        userEmail
      );

      if (orderRes.status !== "success") {
        throw new Error(orderRes.reason || "Order creation failed");
      }

      // Step 2: Open Razorpay checkout
      const options = {
        key: orderRes.key_id,
        amount: orderRes.amount,
        currency: orderRes.currency,
        name: "DeployAI",
        description: `Domain Registration: ${cart.map((d) => d.domain).join(", ")}`,
        order_id: orderRes.order_id,
        handler: async function (response) {
          // Step 3: Verify payment
          try {
            const verifyRes = await api.verifyPayment(
              response.razorpay_order_id,
              response.razorpay_payment_id,
              response.razorpay_signature,
              userId,
              userEmail,
              cart.map((d) => d.domain)
            );

            if (verifyRes.verified) {
              setPaymentStatus("success");
              setRegisteredDomains(verifyRes.registered_domains || []);
              setCart([]);
              setShowCheckout(false);
            } else {
              setPaymentStatus("error");
              setPaymentError(verifyRes.reason || "Verification failed");
            }
          } catch (err) {
            setPaymentStatus("error");
            setPaymentError(err.message);
          }
        },
        prefill: { email: userEmail || "" },
        theme: { color: "#6366f1" },
        modal: {
          ondismiss: () => setPaymentStatus(null),
        },
      };

      if (typeof window !== "undefined" && window.Razorpay) {
        const rzp = new window.Razorpay(options);
        rzp.open();
      } else {
        throw new Error("Razorpay SDK not loaded. Add the Razorpay script to your page.");
      }
    } catch (err) {
      setPaymentStatus("error");
      setPaymentError(err.message);
    }
  };

  // ── Domain Result Card ─────────────────────────────────
  const DomainCard = ({ domain, index }) => {
    const isAvailable = domain.available === true;
    const isPremium = domain.premium;
    const isTaken = domain.available === false;
    const inCart = cart.find((d) => d.domain === domain.domain);

    let borderColor = "rgba(255,255,255,0.08)";
    let glowColor = "none";
    if (isAvailable && isPremium) {
      borderColor = "rgba(139, 92, 246, 0.4)";
      glowColor = "0 0 20px rgba(139, 92, 246, 0.2)";
    } else if (isAvailable) {
      borderColor = "rgba(16, 185, 129, 0.4)";
      glowColor = "0 0 20px rgba(16, 185, 129, 0.15)";
    } else if (isTaken) {
      borderColor = "rgba(239, 68, 68, 0.25)";
    }

    return (
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: index * 0.05 }}
        style={{
          padding: "16px 20px",
          borderRadius: 12,
          background: isTaken ? "rgba(239,68,68,0.04)" : "rgba(255,255,255,0.04)",
          backdropFilter: "blur(12px)",
          border: `1px solid ${borderColor}`,
          boxShadow: glowColor,
          display: "flex", justifyContent: "space-between", alignItems: "center",
          transition: "all 0.2s ease",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Globe size={14} style={{ color: isAvailable ? "#10b981" : "#6b7280" }} />
            <span style={{
              fontSize: "0.95rem", fontWeight: 600,
              color: isTaken ? "rgba(255,255,255,0.4)" : "var(--text-primary)",
            }}>
              {domain.domain}
            </span>
            {isPremium && (
              <span style={{
                fontSize: "0.6rem", padding: "2px 8px", borderRadius: 20,
                background: "rgba(139,92,246,0.15)", color: "#a78bfa",
                border: "1px solid rgba(139,92,246,0.3)", fontWeight: 700,
                display: "flex", alignItems: "center", gap: 3,
              }}>
                <Crown size={9} /> PREMIUM
              </span>
            )}
            {isTaken && (
              <span style={{
                fontSize: "0.6rem", padding: "2px 8px", borderRadius: 20,
                background: "rgba(239,68,68,0.1)", color: "#f87171",
                border: "1px solid rgba(239,68,68,0.2)", fontWeight: 700,
              }}>
                TAKEN
              </span>
            )}
          </div>
          {isAvailable && (
            <div style={{ fontSize: "0.75rem", color: "var(--text-tertiary)", marginTop: 4 }}>
              {domain.source}
            </div>
          )}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {isAvailable && (
            <span style={{
              fontSize: "0.95rem", fontWeight: 700,
              color: isPremium ? "#a78bfa" : "#10b981",
            }}>
              ₹{domain.price_inr?.toLocaleString("en-IN")}
            </span>
          )}
          {isAvailable && (
            <button
              onClick={() => inCart ? removeFromCart(domain.domain) : addToCart(domain)}
              style={{
                padding: "8px 16px", borderRadius: 8, fontSize: "0.78rem", fontWeight: 600,
                cursor: "pointer", border: "none", transition: "all 0.2s",
                background: inCart
                  ? "rgba(16,185,129,0.15)"
                  : "linear-gradient(135deg, #6366f1, #8b5cf6)",
                color: "white",
              }}
            >
              {inCart ? <><Check size={12} /> Added</> : "Add to Cart"}
            </button>
          )}
        </div>
      </motion.div>
    );
  };

  return (
    <div style={{ position: "relative" }}>
      {/* ── Search Bar ─────────────────────────────────── */}
      <div style={{ position: "relative", marginBottom: 24 }}>
        <div style={{
          position: "relative",
          background: "rgba(255,255,255,0.04)",
          borderRadius: 16,
          border: "1px solid rgba(255,255,255,0.1)",
          backdropFilter: "blur(20px)",
          boxShadow: "0 0 40px rgba(0,245,255,0.08), inset 0 1px 0 rgba(255,255,255,0.1)",
          overflow: "hidden",
        }}>
          <div style={{ display: "flex", alignItems: "center", padding: "0 20px" }}>
            <Search size={20} style={{
              color: "#00F5FF", filter: "drop-shadow(0 0 6px rgba(0,245,255,0.5))",
              animation: loading ? "pulse 1s infinite" : "none",
            }} />
            <input
              type="text"
              value={query}
              onChange={(e) => handleSearch(e.target.value)}
              placeholder="Find your perfect domain..."
              id="domain-search-input"
              style={{
                flex: 1, padding: "18px 16px", fontSize: "1.05rem",
                background: "transparent", border: "none", outline: "none",
                color: "var(--text-primary)", fontWeight: 500,
              }}
            />
            {loading && <Loader2 size={18} style={{ color: "#00F5FF", animation: "spin 1s linear infinite" }} />}
          </div>
        </div>
        <p style={{ fontSize: "0.72rem", color: "var(--text-tertiary)", marginTop: 8, textAlign: "center" }}>
          Searches .com .in .io .dev .app .net .org .co — powered by DomScan
        </p>
      </div>

      {/* ── Cart Floating Badge ────────────────────────── */}
      {cart.length > 0 && (
        <motion.button
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          onClick={() => setShowCart(!showCart)}
          style={{
            position: "fixed", bottom: 100, right: 32, zIndex: 9998,
            width: 56, height: 56, borderRadius: "50%",
            background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
            border: "none", cursor: "pointer", display: "flex",
            alignItems: "center", justifyContent: "center", color: "white",
            boxShadow: "0 0 30px rgba(99,102,241,0.5)",
          }}
          id="domain-cart-btn"
        >
          <ShoppingCart size={22} />
          <span style={{
            position: "absolute", top: -4, right: -4,
            width: 22, height: 22, borderRadius: "50%",
            background: "#ef4444", fontSize: "0.7rem",
            fontWeight: 700, display: "flex", alignItems: "center",
            justifyContent: "center",
          }}>
            {cart.length}
          </span>
        </motion.button>
      )}

      {/* ── Results ────────────────────────────────────── */}
      {loading && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {[...Array(6)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
      )}

      {!loading && results.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 32 }}>
          {results.map((d, i) => <DomainCard key={d.domain} domain={d} index={i} />)}
        </div>
      )}

      {/* ── Suggestions ────────────────────────────────── */}
      {!loading && suggestions.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <h3 style={{
            fontSize: "0.85rem", fontWeight: 700, color: "var(--text-secondary)",
            marginBottom: 12, display: "flex", alignItems: "center", gap: 6,
          }}>
            <Sparkles size={14} style={{ color: "#f59e0b" }} />
            You might also like
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {suggestions.filter(s => s.available).map((d, i) => (
              <DomainCard key={d.domain} domain={d} index={i} />
            ))}
          </div>
        </div>
      )}

      {/* ── Cart Panel (Slide-in) ──────────────────────── */}
      <AnimatePresence>
        {showCart && cart.length > 0 && (
          <motion.div
            initial={{ opacity: 0, x: 40 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 40 }}
            style={{
              position: "fixed", top: 80, right: 24, bottom: 24,
              width: 360, zIndex: 9999,
              background: "rgba(10,14,26,0.85)",
              backdropFilter: "blur(24px)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 16,
              display: "flex", flexDirection: "column",
              boxShadow: "0 24px 64px rgba(0,0,0,0.6)",
            }}
          >
            {/* Cart Header */}
            <div style={{
              padding: "16px 20px", display: "flex", justifyContent: "space-between",
              alignItems: "center", borderBottom: "1px solid rgba(255,255,255,0.08)",
            }}>
              <span style={{ fontWeight: 700, fontSize: "0.95rem", color: "var(--text-primary)" }}>
                <ShoppingCart size={16} style={{ marginRight: 8, verticalAlign: "middle" }} />
                Cart ({cart.length})
              </span>
              <button onClick={() => setShowCart(false)} style={{
                background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)",
              }}>
                <X size={18} />
              </button>
            </div>

            {/* Cart Items */}
            <div style={{ flex: 1, overflowY: "auto", padding: "12px 16px" }}>
              {cart.map((d) => (
                <div key={d.domain} style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "10px 0", borderBottom: "1px solid rgba(255,255,255,0.05)",
                }}>
                  <div>
                    <div style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-primary)" }}>{d.domain}</div>
                    <div style={{ fontSize: "0.72rem", color: "var(--text-tertiary)" }}>1 year registration</div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "#10b981" }}>
                      ₹{d.price_inr?.toLocaleString("en-IN")}
                    </span>
                    <button onClick={() => removeFromCart(d.domain)} style={{
                      background: "none", border: "none", cursor: "pointer", color: "#ef4444", padding: 4,
                    }}>
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* Cart Footer */}
            <div style={{
              padding: "16px 20px", borderTop: "1px solid rgba(255,255,255,0.08)",
            }}>
              <div style={{
                display: "flex", justifyContent: "space-between", marginBottom: 12,
                fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)",
              }}>
                <span>Total</span>
                <span style={{ color: "#10b981" }}>₹{cartTotal.toLocaleString("en-IN")}</span>
              </div>
              <button
                onClick={handleCheckout}
                disabled={paymentStatus === "processing"}
                id="domain-checkout-btn"
                style={{
                  width: "100%", padding: "14px", borderRadius: 10,
                  background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
                  color: "white", border: "none", cursor: "pointer",
                  fontSize: "0.9rem", fontWeight: 700,
                  opacity: paymentStatus === "processing" ? 0.6 : 1,
                }}
              >
                {paymentStatus === "processing" ? (
                  <><Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} /> Processing...</>
                ) : (
                  "Proceed to Payment"
                )}
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Success Overlay ────────────────────────────── */}
      <AnimatePresence>
        {paymentStatus === "success" && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{
              position: "fixed", inset: 0, zIndex: 10001,
              background: "rgba(0,0,0,0.7)", backdropFilter: "blur(8px)",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}
          >
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              style={{
                padding: "40px", borderRadius: 20, width: 420,
                background: "rgba(10,14,26,0.9)", border: "1px solid rgba(16,185,129,0.3)",
                boxShadow: "0 0 60px rgba(16,185,129,0.2)",
                textAlign: "center",
              }}
            >
              <motion.div
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ duration: 0.5 }}
                style={{
                  width: 64, height: 64, borderRadius: "50%", margin: "0 auto 16px",
                  background: "rgba(16,185,129,0.15)", display: "flex",
                  alignItems: "center", justifyContent: "center",
                  border: "2px solid #10b981",
                }}
              >
                <Check size={32} color="#10b981" />
              </motion.div>
              <h3 style={{ color: "#10b981", fontSize: "1.2rem", marginBottom: 8 }}>
                Domains Registered!
              </h3>
              <div style={{ marginBottom: 20 }}>
                {registeredDomains.map((d) => (
                  <div key={d} style={{
                    padding: "8px 16px", margin: "6px 0", borderRadius: 8,
                    background: "rgba(16,185,129,0.08)", color: "var(--text-primary)",
                    fontSize: "0.9rem", fontWeight: 600,
                  }}>
                    {d}
                  </div>
                ))}
              </div>
              <p style={{ fontSize: "0.78rem", color: "var(--text-tertiary)", marginBottom: 16 }}>
                Nameserver details have been sent to your email.
              </p>
              <button
                onClick={() => setPaymentStatus(null)}
                style={{
                  padding: "12px 24px", borderRadius: 10,
                  background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
                  color: "white", border: "none", cursor: "pointer",
                  fontSize: "0.85rem", fontWeight: 600,
                }}
              >
                Connect to Deployment
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Error Overlay ──────────────────────────────── */}
      <AnimatePresence>
        {paymentStatus === "error" && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{
              position: "fixed", inset: 0, zIndex: 10001,
              background: "rgba(0,0,0,0.7)", backdropFilter: "blur(8px)",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}
          >
            <motion.div
              initial={{ scale: 0.8 }}
              animate={{ scale: 1 }}
              style={{
                padding: "40px", borderRadius: 20, width: 420,
                background: "rgba(10,14,26,0.9)", border: "1px solid rgba(239,68,68,0.3)",
                textAlign: "center",
              }}
            >
              <AlertTriangle size={40} color="#ef4444" style={{ marginBottom: 12 }} />
              <h3 style={{ color: "#ef4444", fontSize: "1.1rem", marginBottom: 8 }}>
                Payment Failed
              </h3>
              <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: 20 }}>
                {paymentError || "An unexpected error occurred during payment."}
              </p>
              <div style={{ display: "flex", gap: 12, justifyContent: "center" }}>
                <button
                  onClick={() => { setPaymentStatus(null); handleCheckout(); }}
                  style={{
                    padding: "10px 20px", borderRadius: 8,
                    background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
                    color: "white", border: "none", cursor: "pointer",
                    fontSize: "0.82rem", fontWeight: 600,
                    display: "flex", alignItems: "center", gap: 6,
                  }}
                >
                  <RefreshCw size={14} /> Retry
                </button>
                <button
                  onClick={() => setPaymentStatus(null)}
                  style={{
                    padding: "10px 20px", borderRadius: 8,
                    background: "rgba(255,255,255,0.06)", color: "var(--text-secondary)",
                    border: "1px solid rgba(255,255,255,0.1)", cursor: "pointer",
                    fontSize: "0.82rem",
                  }}
                >
                  Cancel
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
