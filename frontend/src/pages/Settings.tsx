import { useEffect, useMemo, useState } from "react";
import { Shield, Database, Key, Bell } from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import { motion } from "framer-motion";
import { getRootInfo, getSystemStatus, type RootInfo, type SystemStatusData } from "@/lib/api-functions";

const fallbackSystem: SystemStatusData = {
  total_logs: 0,
  total_anomalies: 0,
  active_sessions: 0,
  environment: "AIR-GAPPED",
  nodes_online: 0,
  uptime_hours: 0,
  last_analysis: new Date().toISOString(),
};

const fallbackRoot: RootInfo = {
  name: "Quorum",
  version: "unknown",
  status: "offline",
  docs: "/docs",
};

export default function Settings() {
  const [system, setSystem] = useState<SystemStatusData>(fallbackSystem);
  const [root, setRoot] = useState<RootInfo>(fallbackRoot);

  useEffect(() => {
    const load = async () => {
      try {
        const [s, r] = await Promise.all([getSystemStatus(), getRootInfo()]);
        setSystem(s);
        setRoot(r);
      } catch {
        // Fallback values are already set
      }
    };

    void load();
  }, []);

  const settingsCards = useMemo(
    () => [
      {
        icon: Shield,
        label: "Security",
        desc: "Cryptographic keys and signature verification",
        value: "RSA-PSS 4096-bit",
      },
      {
        icon: Database,
        label: "Database",
        desc: "Backend storage statistics",
        value: `${system.total_logs.toLocaleString()} logs, ${system.total_anomalies.toLocaleString()} anomalies`,
      },
      {
        icon: Bell,
        label: "Alerts",
        desc: "Current operational state",
        value: `${root.status.toUpperCase()} - ${system.environment}`,
      },
      {
        icon: Key,
        label: "API Endpoint",
        desc: "Backend server address",
        value: import.meta.env.VITE_API_URL || "http://localhost:8000",
      },
    ],
    [root.status, system.environment, system.total_anomalies, system.total_logs],
  );

  return (
    <AppLayout title="Settings" subtitle="System configuration">
      <div className="space-y-4 max-w-2xl">
        {settingsCards.map((s, i) => (
          <motion.div
            key={s.label}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.07 }}
            className="cyber-card p-5 flex items-center justify-between"
          >
            <div className="flex items-center gap-4">
              <div
                className="w-9 h-9 rounded-lg flex items-center justify-center"
                style={{
                  background: "hsl(var(--cyan) / 0.1)",
                  border: "1px solid hsl(var(--cyan) / 0.2)",
                }}
              >
                <s.icon className="w-4 h-4 text-cyan" />
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">{s.label}</p>
                <p className="text-xs text-muted-foreground">{s.desc}</p>
              </div>
            </div>
            <span className="font-mono text-xs text-muted-foreground">{s.value}</span>
          </motion.div>
        ))}
      </div>
    </AppLayout>
  );
}
