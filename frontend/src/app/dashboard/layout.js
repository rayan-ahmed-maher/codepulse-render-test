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
    <div className="dashboard-container" id="dashboard"
      onMouseMove={(e) => {
        const rect = e.currentTarget.getBoundingClientRect();
        e.currentTarget.style.setProperty('--spotlight-x', `${e.clientX - rect.left}px`);
        e.currentTarget.style.setProperty('--spotlight-y', `${e.clientY - rect.top}px`);
      }}
    >
      <div className="particle-field" />
      <div className="dashboard-spotlight" />
      <aside className="sidebar mini-sidebar" id="sidebar">
        <div className="sidebar-brand mini-brand">
          <div className="sidebar-brand-icon holographic-glow"><Rocket size={20} color="white" /></div>
        </div>

        <nav className="sidebar-nav mini-nav">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.path + item.label}
              className={`nav-link mini-link ${isActive(item.path) ? "active" : ""}`}
              onClick={() => router.push(item.path)}
              title={item.label}
            >
              <span className="nav-link-icon"><item.icon size={20} /></span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer mini-footer">
          <button className="nav-link mini-link" onClick={handleSignOut} title="Sign Out"
            style={{ color: "var(--color-rose-danger)" }}>
            <span className="nav-link-icon"><LogOut size={20} /></span>
          </button>
          
          {user && (
            <div className="mini-user-avatar holographic-glow">
              {user.email?.[0].toUpperCase()}
            </div>
          )}
        </div>
      </aside>

      <main className="main-stage" id="main-stage">{children}</main>

      <AIChat inline={false} />
      <TerminalOverlay logs={terminalLogs} isOpen={terminalOpen} onToggle={toggleTerminal} />
    </div>
  );
}
