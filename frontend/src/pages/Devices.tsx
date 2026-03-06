import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, Cpu, Link2Off, Usb } from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import { getDeviceEvents, type DeviceEvent } from "@/lib/api-functions";

const fmtTime = (value?: string | null) => {
  if (!value) return "-";
  return new Date(value).toLocaleString();
};

const fmtDuration = (seconds?: number | null) => {
  if (!seconds || seconds <= 0) return "-";
  const total = Math.floor(seconds);
  const min = Math.floor(total / 60);
  const sec = total % 60;
  return `${min}m ${String(sec).padStart(2, "0")}s`;
};

export default function Devices() {
  const [events, setEvents] = useState<DeviceEvent[]>([]);
  const [loading, setLoading] = useState(false);

  const loadEvents = async () => {
    setLoading(true);
    try {
      const rows = await getDeviceEvents(300);
      setEvents(rows);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadEvents();
    const timer = window.setInterval(() => {
      void loadEvents();
    }, 3000);
    return () => window.clearInterval(timer);
  }, []);

  const stats = useMemo(() => {
    const connected = events.filter((e) => e.event === "connected").length;
    const removed = events.filter((e) => e.event === "disconnected").length;
    const highRisk = events.filter((e) => {
      const r = String(e.risk_level ?? "").toUpperCase();
      return r === "HIGH" || r === "CRITICAL";
    }).length;
    return { connected, removed, highRisk };
  }, [events]);

  return (
    <AppLayout title="Device Monitor" subtitle="Automatic USB/LAN event tracking with duration history">
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="cyber-card p-4 flex items-center gap-3">
            <Usb className="w-5 h-5 text-cyan" />
            <div>
              <p className="text-xs text-muted-foreground">Connected Events</p>
              <p className="text-xl font-mono text-foreground">{stats.connected}</p>
            </div>
          </div>
          <div className="cyber-card p-4 flex items-center gap-3">
            <Link2Off className="w-5 h-5 text-cyber-high" />
            <div>
              <p className="text-xs text-muted-foreground">Removed Events</p>
              <p className="text-xl font-mono text-foreground">{stats.removed}</p>
            </div>
          </div>
          <div className="cyber-card p-4 flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-cyber-critical" />
            <div>
              <p className="text-xs text-muted-foreground">High Risk</p>
              <p className="text-xl font-mono text-cyber-critical">{stats.highRisk}</p>
            </div>
          </div>
        </div>

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="cyber-card overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-border">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-cyan" />
              <h3 className="text-sm font-semibold">Device Event History</h3>
            </div>
            <span className="text-xs font-mono text-muted-foreground">
              {loading ? "Refreshing..." : `${events.length} records`}
            </span>
          </div>
          <div className="overflow-x-auto max-h-[560px]">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  {["Device Name", "Type", "Event", "Connected", "Removed", "Duration", "Risk"].map((h) => (
                    <th
                      key={h}
                      className="text-left px-4 py-2.5 text-xs font-semibold text-muted-foreground uppercase tracking-wide"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {events.map((row, i) => (
                  <motion.tr
                    key={`${row.device_id}-${row.connected_at}-${i}`}
                    className="table-row-cyber border-b border-border/50 last:border-0"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.01 }}
                  >
                    <td className="px-4 py-3 text-xs font-medium text-foreground">{row.name}</td>
                    <td className="px-4 py-3 font-mono text-xs text-cyan">{row.device_class}</td>
                    <td className="px-4 py-3 font-mono text-xs text-foreground">{row.event.toUpperCase()}</td>
                    <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{fmtTime(row.connected_at)}</td>
                    <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{fmtTime(row.removed_at)}</td>
                    <td className="px-4 py-3 font-mono text-xs text-foreground">{fmtDuration(row.duration_seconds)}</td>
                    <td className="px-4 py-3 font-mono text-xs text-cyber-high">{row.risk_level ?? "INFO"}</td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      </div>
    </AppLayout>
  );
}
