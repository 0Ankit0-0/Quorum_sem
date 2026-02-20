import { Shield, Settings as SettingsIcon, Database, Key, Bell } from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import { motion } from "framer-motion";

export default function Settings() {
  return (
    <AppLayout title="Settings" subtitle="System configuration">
      <div className="space-y-4 max-w-2xl">
        {[
          { icon: Shield, label: "Security", desc: "Cryptographic keys, signature verification", value: "RSA-PSS 4096-bit" },
          { icon: Database, label: "Database", desc: "SQLite storage configuration", value: "quorum.db · 2.4 GB" },
          { icon: Bell, label: "Alerts", desc: "Notification thresholds", value: "CRITICAL + HIGH" },
          { icon: Key, label: "API Endpoint", desc: "Backend server address", value: "localhost:8000" },
        ].map((s, i) => (
          <motion.div key={s.label} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.07 }}
            className="cyber-card p-5 flex items-center justify-between"
          >
            <div className="flex items-center gap-4">
              <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ background: "hsl(var(--cyan) / 0.1)", border: "1px solid hsl(var(--cyan) / 0.2)" }}>
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
