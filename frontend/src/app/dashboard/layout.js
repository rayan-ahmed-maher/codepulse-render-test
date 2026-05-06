"use client";

import { useState, useCallback, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import {
  Rocket, LayoutDashboard, Globe, Activity,
  Settings, HelpCircle, LogOut
} from "lucide-react";
import { supabase } from "@/lib/supabase";
import AIChat from "@/components/AIChat";
import TerminalOverlay from "@/components/TerminalOverlay";
import ThemeToggle from "@/components/ThemeToggle";
import "./dashboard.css";

const NAV_ITEMS = [
  { icon: LayoutDashboard, label: "Dashboard", path: "/dashboard" },
  { icon: Globe, label: "Domains", path: "/dashboard/domains" },
  { icon: Activity, label: "Analytics", path: "/dashboard/analytics" },
  { icon: Settings, label: "Settings", path: "/dashboard/settings" },
  { icon: HelpCircle, label: "Help", path: "/dashboard/help" },
];

export default function DashboardLayout({ children }) {
  const router = useRouter();
  const pathname = usePathname();
  const [terminalOpen, setTerminalOpen] = useState(false);
  const [terminalLogs, setTerminalLogs] = useState([]);
  const [user, setUser] = useState(null);

  // Auth guard — redirect to login if no session
  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (data.session?.user) {
        setUser(data.session.user);
      } else {
        router.push("/");
      }
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session?.user) {
        setUser(session.user);
      } else {
        router.push("/");
      }
    });

    return () => subscription.unsubscribe();
  }, [router]);

  const toggleTerminal = useCallback(() => setTerminalOpen((p) => !p), []);

  useEffect(() => {
    window.__deployai = {
      pushLog: (line) => setTerminalLogs((p) => [...p, line]),
      setLogs: (logs) => setTerminalLogs(logs),
      clear: () => setTerminalLogs([]),
      open: () => setTerminalOpen(true),
    };
    return () => { delete window.__deployai; };
  }, []);

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    router.push("/");
  };

  const isActive = (path) => {
    if (path === "/dashboard" && pathname === "/dashboard") return true;
    if (path !== "/dashboard" && pathname.startsWith(path)) return true;
    return false;
  };

  return (
    <div className="dashboard-container" id="dashboard">
      <aside className="sidebar" id="sidebar">
        <div className="sidebar-brand">
          <div className="sidebar-brand-icon"><Rocket size={18} color="white" /></div>
          <div>
            <h2>DeployAI</h2>
            <p>SaaS Platform</p>
          </div>
        </div>

        <div className="sidebar-section">
          <div className="sidebar-section-title">Navigation</div>
          <nav className="sidebar-nav">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.path + item.label}
                className={`nav-link ${isActive(item.path) ? "active" : ""}`}
                onClick={() => router.push(item.path)}
              >
                <span className="nav-link-icon"><item.icon size={16} /></span>
                {item.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="sidebar-section" style={{ marginTop: "auto" }}>
          <div style={{ padding: "8px 12px" }}><ThemeToggle /></div>

          {user && (
            <div style={{
              padding: "10px 12px", margin: "8px 0", borderRadius: "var(--radius-md)",
              background: "var(--glass-bg)", fontSize: "0.75rem",
            }}>
              <div style={{ fontWeight: 600, color: "var(--text-primary)", marginBottom: 2 }}>
                {user.user_metadata?.full_name || user.email?.split("@")[0] || "User"}
              </div>
              <div style={{ color: "var(--text-tertiary)", fontSize: "0.65rem" }}>{user.email}</div>
            </div>
          )}

          <button className="nav-link" onClick={handleSignOut}
            style={{ color: "var(--color-rose-danger)" }}>
            <span className="nav-link-icon"><LogOut size={16} /></span>
            Sign Out
          </button>
        </div>
      </aside>

      <main className="main-stage" id="main-stage">{children}</main>

      <aside className="ai-wing" id="ai-wing">
        <AIChat inline={true} />
      </aside>

      <TerminalOverlay logs={terminalLogs} isOpen={terminalOpen} onToggle={toggleTerminal} />
    </div>
  );
}
