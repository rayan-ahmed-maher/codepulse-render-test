"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Globe, Search, ShieldCheck, ExternalLink, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";

export default function DomainsPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState("");

  const handleSearch = async () => {
    if (!query.trim()) return;
    setSearching(true);
    setError("");
    setResults([]);

    try {
      const data = await api.searchDomain(query.trim());

      if (data.error) {
        setError(data.error + (data.details ? ` — ${data.details}` : ""));
        setSearching(false);
        return;
      }

      if (data.results && data.results.length > 0) {
        setResults(data.results);
      } else {
        setError("No domain results returned from API.");
      }
    } catch (err) {
      setError(`Failed to search domains: ${err.message}`);
    }
    setSearching(false);
  };

  return (
    <div style={{ padding: 0 }}>
      <div className="main-header">
        <div>
          <h1 className="text-gradient">Domain Intelligence</h1>
          <p style={{ fontSize: "0.82rem", color: "var(--text-tertiary)", marginTop: 4 }}>
            Real-time domain availability via DNS lookup
          </p>
        </div>
      </div>

      <div className="glass-panel" style={{ padding: 20, display: "flex", gap: 10, alignItems: "center" }}>
        <Globe size={18} color="var(--color-electric-indigo)" />
        <input
          type="text" value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="Enter a domain name (e.g. myproject)"
          style={{ flex: 1, padding: "10px 14px", fontSize: "0.88rem" }}
        />
        <button className="btn btn-primary" onClick={handleSearch} disabled={searching}>
          {searching ? "Searching..." : "Search"} <Search size={16} />
        </button>
      </div>

      {error && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass-panel"
          style={{ marginTop: 16, padding: 16, borderLeft: "3px solid var(--color-rose-danger)", display: "flex", alignItems: "center", gap: 10 }}>
          <AlertTriangle size={18} color="var(--color-rose-danger)" />
          <div>
            <p style={{ fontSize: "0.85rem", color: "var(--color-rose-danger)", fontWeight: 600 }}>Search Failed</p>
            <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)" }}>{error}</p>
          </div>
        </motion.div>
      )}

      {results.length > 0 && (
        <div style={{ marginTop: 20, display: "flex", flexDirection: "column", gap: 10 }}>
          <div className="section-label">
            Domain Availability — via {results[0]?.source || "DNS"}
          </div>
          {results.map((d, i) => (
            <motion.div key={d.domain} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.08 }} className="glass-panel"
              style={{ padding: "16px 20px", display: "flex", alignItems: "center", justifyContent: "space-between",
                borderLeft: d.available ? "3px solid var(--color-emerald-neon)" : d.available === false ? "3px solid rgba(239,68,68,0.3)" : "3px solid rgba(255,255,255,0.1)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <span style={{ fontSize: "0.95rem", fontWeight: 700 }}>{d.domain}</span>
                {d.available && <ShieldCheck size={14} color="var(--color-emerald-neon)" />}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                <span style={{ fontSize: "0.78rem", color: "var(--text-tertiary)" }}>{d.registrar}</span>
                <span style={{ fontSize: "0.85rem", fontWeight: 700, color: d.available ? "var(--color-emerald-neon)" : d.available === false ? "var(--color-rose-danger)" : "var(--text-tertiary)" }}>
                  {d.available ? d.price : d.available === false ? "Taken" : "Unknown"}
                </span>
                {d.available && (
                  <button className="btn btn-primary btn-sm"><ExternalLink size={12} /> Register</button>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {results.length === 0 && !searching && !error && (
        <div style={{ marginTop: 40, textAlign: "center", color: "var(--text-tertiary)" }}>
          <Globe size={48} style={{ opacity: 0.2, marginBottom: 12 }} />
          <p style={{ fontSize: "0.88rem" }}>Search for your perfect domain name</p>
          <p style={{ fontSize: "0.75rem", marginTop: 4 }}>Powered by real-time DNS lookups</p>
        </div>
      )}
    </div>
  );
}
