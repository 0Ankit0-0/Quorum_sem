import { Shield, LayoutDashboard, FileText, Radio, Cpu, FlaskConical, Network, BarChart3, Terminal, Settings, ChevronRight } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { motion } from "framer-motion";

const navItems = [
  { icon: LayoutDashboard, label: "Dashboard", path: "/" },
  { icon: FileText, label: "Logs", path: "/logs" },
  { icon: Radio, label: "Monitor", path: "/monitor" },
  { icon: Cpu, label: "Devices", path: "/devices" },
  { icon: FlaskConical, label: "Analysis", path: "/analysis" },
  { icon: Network, label: "Hub", path: "/hub" },
  { icon: BarChart3, label: "Reports", path: "/reports" },
  { icon: Terminal, label: "Terminal", path: "/terminal" },
  { icon: Settings, label: "Settings", path: "/settings" },
];

export default function Sidebar() {
  const location = useLocation();

  return (
    <aside className="fixed left-0 top-0 h-screen w-60 flex flex-col z-50 border-r border-border" style={{ background: "hsl(var(--sidebar-background))" }}>
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-border">
        <div className="relative">
          <div className="w-8 h-8 rounded-md flex items-center justify-center" style={{ background: "hsl(var(--cyan) / 0.15)", border: "1px solid hsl(var(--cyan) / 0.4)" }}>
            <Shield className="w-4 h-4 text-cyan" />
          </div>
          <div className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-cyber-low animate-pulse" />
        </div>
        <div>
          <p className="font-bold text-base tracking-wide text-foreground">QUORUM</p>
          <p className="text-xs text-muted-foreground font-mono">v2.4.1 · OFFLINE</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest px-3 mb-2">Navigation</p>
        {navItems.map((item) => {
          const isActive = location.pathname === item.path || (item.path !== "/" && location.pathname.startsWith(item.path));
          return (
            <Link key={item.path} to={item.path}>
              <motion.div
                className={`nav-item ${isActive ? "active" : ""}`}
                whileHover={{ x: 2 }}
                transition={{ duration: 0.15 }}
              >
                <item.icon className="w-4 h-4 shrink-0" />
                <span className="flex-1">{item.label}</span>
                {isActive && <ChevronRight className="w-3 h-3 opacity-60" />}
              </motion.div>
            </Link>
          );
        })}
      </nav>

      {/* System status footer */}
      <div className="px-4 py-4 border-t border-border">
        <div className="rounded-md p-3 space-y-2" style={{ background: "hsl(var(--cyan) / 0.05)", border: "1px solid hsl(var(--cyan) / 0.15)" }}>
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">Environment</span>
            <span className="text-xs font-semibold text-cyber-low font-mono">AIR-GAPPED</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">Nodes Online</span>
            <span className="text-xs font-semibold text-cyan font-mono">7/8</span>
          </div>
          <div className="flex items-center gap-2 pt-1">
            <div className="pulse-dot bg-cyber-low" />
            <span className="text-xs text-cyber-low">System Operational</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
