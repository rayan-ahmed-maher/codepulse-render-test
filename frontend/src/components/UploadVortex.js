"use client";

import { useState, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, FolderArchive, Scan, CheckCircle2, FileCode2, GitBranch, FolderOpen, Archive } from "lucide-react";

const ACCEPTED_EXTENSIONS = ".js,.jsx,.ts,.tsx,.py,.html,.css,.json,.zip,.md,.toml,.yaml,.yml,.mjs,.cjs,.env.example,.gitignore,.txt,.svg,.png,.jpg,.webp,.ico,.xml,.lock";

export default function UploadVortex({ onUpload, onGitHubImport, isAnalyzing }) {
  const [isDragging, setIsDragging] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);
  const [scannedFiles, setScannedFiles] = useState([]);
  const [gitUrl, setGitUrl] = useState("");
  const [showGitInput, setShowGitInput] = useState(false);
  const folderInputRef = useRef(null);
  const zipInputRef = useRef(null);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      processFiles(files);
    }
  }, [onUpload]);

  const handleFolderSelect = useCallback((e) => {
    const files = Array.from(e.target.files);
    if (files.length > 0) processFiles(files);
  }, [onUpload]);

  const handleZipSelect = useCallback((e) => {
    const files = Array.from(e.target.files);
    if (files.length > 0) processFiles(files);
  }, [onUpload]);

  const processFiles = (files) => {
    // Build file tree from webkitRelativePath
    const fileTree = files.map((f) => ({
      name: f.webkitRelativePath || f.name,
      size: f.size,
      type: f.type,
    }));

    // Show X-ray scan animation
    const names = fileTree.map((f) => f.name.split("/").pop()).slice(0, 10);
    setScanProgress(0);
    setScannedFiles([]);
    let idx = 0;
    const interval = setInterval(() => {
      if (idx < names.length) {
        setScannedFiles((prev) => [...prev, names[idx]]);
        setScanProgress(((idx + 1) / names.length) * 100);
        idx++;
      } else {
        clearInterval(interval);
      }
    }, 150);

    onUpload?.(files, fileTree);
  };

  const handleGitSubmit = () => {
    if (!gitUrl.trim()) return;
    const url = gitUrl.trim();
    if (!url.includes("github.com/")) {
      alert("Please enter a valid GitHub repository URL");
      return;
    }
    onGitHubImport?.(url);
    setShowGitInput(false);
    setGitUrl("");
  };

  return (
    <motion.div
      className="upload-vortex"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      animate={{
        borderColor: isDragging
          ? "rgba(99, 102, 241, 0.5)"
          : isAnalyzing
          ? "rgba(16, 185, 129, 0.3)"
          : "rgba(255, 255, 255, 0.08)",
        boxShadow: isDragging
          ? "0 0 60px rgba(99, 102, 241, 0.2), inset 0 0 60px rgba(99, 102, 241, 0.05)"
          : isAnalyzing
          ? "0 0 60px rgba(16, 185, 129, 0.15)"
          : "0 0 0px transparent",
      }}
      transition={{ type: "spring", stiffness: 300, damping: 25 }}
      style={{
        position: "relative",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "44px 32px",
        borderRadius: "var(--radius-xl)",
        border: "2px dashed var(--glass-border)",
        background: isDragging ? "rgba(99, 102, 241, 0.05)" : "var(--glass-bg)",
        backdropFilter: "var(--glass-blur)",
        overflow: "hidden",
        minHeight: "280px",
        transition: "background 0.3s ease",
      }}
    >
      {/* Hidden file inputs */}
      <input
        ref={folderInputRef}
        type="file"
        webkitdirectory=""
        directory=""
        multiple
        onChange={handleFolderSelect}
        style={{ display: "none" }}
        id="folder-input"
      />
      <input
        ref={zipInputRef}
        type="file"
        accept=".zip"
        onChange={handleZipSelect}
        style={{ display: "none" }}
        id="zip-input"
      />

      <AnimatePresence mode="wait">
        {isAnalyzing ? (
          /* ── Scanning State ──────────────────────────────────── */
          <motion.div
            key="analyzing"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}
          >
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
              style={{
                width: 56, height: 56, borderRadius: "50%",
                border: "3px solid rgba(99, 102, 241, 0.2)",
                borderTopColor: "var(--color-electric-indigo)",
                display: "flex", alignItems: "center", justifyContent: "center",
              }}
            >
              <Scan size={24} color="var(--color-electric-indigo)" />
            </motion.div>
            <p style={{ fontSize: "0.95rem", fontWeight: 600, color: "var(--color-electric-indigo-hover)" }}>
              NVIDIA AI Scanning Project...
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: 4, width: "100%", maxWidth: 300 }}>
              {scannedFiles.map((file, i) => (
                <motion.div
                  key={file + i}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  style={{
                    display: "flex", alignItems: "center", gap: 8,
                    padding: "4px 8px", fontSize: "0.75rem",
                    color: "var(--color-emerald-neon)", fontFamily: "monospace",
                  }}
                >
                  <FileCode2 size={12} />
                  <span>{file}</span>
                  <CheckCircle2 size={12} style={{ marginLeft: "auto" }} />
                </motion.div>
              ))}
            </div>

            {scanProgress > 0 && (
              <div style={{ width: "100%", maxWidth: 300, height: 4, background: "rgba(255,255,255,0.05)", borderRadius: 2, overflow: "hidden" }}>
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${scanProgress}%` }}
                  style={{
                    height: "100%",
                    background: "linear-gradient(90deg, var(--color-electric-indigo), var(--color-emerald-neon))",
                    borderRadius: 2,
                  }}
                />
              </div>
            )}
          </motion.div>
        ) : (
          /* ── Idle State ──────────────────────────────────────── */
          <motion.div
            key="idle"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16, textAlign: "center", width: "100%" }}
          >
            <motion.div
              animate={{
                y: [0, -6, 0],
                boxShadow: [
                  "0 0 20px rgba(99, 102, 241, 0.2)",
                  "0 0 40px rgba(99, 102, 241, 0.4)",
                  "0 0 20px rgba(99, 102, 241, 0.2)",
                ],
              }}
              transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
              style={{
                width: 64, height: 64, borderRadius: "var(--radius-lg)",
                background: "linear-gradient(135deg, var(--color-electric-indigo-dim), rgba(139, 92, 246, 0.15))",
                border: "1px solid rgba(99, 102, 241, 0.2)",
                display: "flex", alignItems: "center", justifyContent: "center",
              }}
            >
              {isDragging ? (
                <FolderArchive size={28} color="var(--color-electric-indigo)" />
              ) : (
                <Upload size={28} color="var(--color-electric-indigo)" />
              )}
            </motion.div>

            <div>
              <p style={{ fontSize: "1rem", fontWeight: 700, marginBottom: 4, color: "var(--text-primary)" }}>
                {isDragging ? "Release to Upload" : "Drop Your Project Here"}
              </p>
              <p style={{ fontSize: "0.8rem", color: "var(--text-tertiary)" }}>
                Drag files, select a folder, upload a .zip, or import from GitHub
              </p>
            </div>

            {/* ── Action Buttons ─────────────────────────────── */}
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "center" }}>
              <button
                className="btn btn-secondary btn-sm"
                onClick={(e) => { e.stopPropagation(); folderInputRef.current?.click(); }}
                style={{ display: "flex", alignItems: "center", gap: 6 }}
              >
                <FolderOpen size={14} /> Select Folder
              </button>
              <button
                className="btn btn-secondary btn-sm"
                onClick={(e) => { e.stopPropagation(); zipInputRef.current?.click(); }}
                style={{ display: "flex", alignItems: "center", gap: 6 }}
              >
                <Archive size={14} /> Upload .zip
              </button>
              <button
                className="btn btn-secondary btn-sm"
                onClick={(e) => { e.stopPropagation(); setShowGitInput(!showGitInput); }}
                style={{ display: "flex", alignItems: "center", gap: 6 }}
              >
                <GitBranch size={14} /> GitHub Import
              </button>
            </div>

            {/* ── GitHub URL Input ───────────────────────────── */}
            <AnimatePresence>
              {showGitInput && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  style={{ width: "100%", maxWidth: 400 }}
                  onClick={(e) => e.stopPropagation()}
                >
                  <div style={{ display: "flex", gap: 6, marginTop: 4 }}>
                    <input
                      type="url"
                      value={gitUrl}
                      onChange={(e) => setGitUrl(e.target.value)}
                      placeholder="https://github.com/user/repo"
                      onKeyDown={(e) => e.key === "Enter" && handleGitSubmit()}
                      style={{ flex: 1, padding: "8px 12px", fontSize: "0.82rem" }}
                    />
                    <button className="btn btn-primary btn-sm" onClick={handleGitSubmit}>
                      Import
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* ── Framework Tags ─────────────────────────────── */}
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "center" }}>
              {["React", "Next.js", "Python", "Static HTML", "Vue"].map((t) => (
                <span key={t} className="badge badge-indigo" style={{ fontSize: "0.65rem" }}>{t}</span>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
