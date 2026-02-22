import { useState } from "react";
import { motion } from "framer-motion";
import { Scan, AlertTriangle, Usb, Network } from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import { formatDate } from "@/lib/formatters";
import { useQuorumData } from "@/hooks/useQuorumData";
import { toast } from "sonner";

const RiskBadge = ({ risk }: { risk: string }) => {
  const map: Record<string, string> = {
    CRITICAL: "badge-critical",
    HIGH: "badge-high",
    MEDIUM: "badge-medium",
    LOW: "badge-low",
  };
  return <span className={map[risk] || "badge-low"}>{risk}</span>;
};

export default function Devices() {
  const { devices, refresh } = useQuorumData();
  const [scanning, setScanning] = useState(false);

  const handleScan = async () => {
    setScanning(true);
    try {
      await refresh();
      toast.success("Device scan refreshed from backend");
    } catch (error) {
      console.error("Device refresh failed", error);
      toast.error("Failed to refresh devices");
    } finally {
      setScanning(false);
    }
  };

  const criticalDevices = [...devices.usb, ...devices.lan].filter(
    (d) => d.risk === "CRITICAL" || d.risk === "HIGH",
  );

  return (
    <AppLayout
      title="Device Scanner"
      subtitle="USB hotplug detection and LAN discovery"
    >
      <div className="space-y-6">
        <div className="flex items-center gap-4 flex-wrap">
          <button
            onClick={handleScan}
            disabled={scanning}
            className="flex items-center gap-2 px-5 py-2.5 rounded-md text-sm font-semibold transition-all"
            style={{
              background: "hsl(var(--cyan) / 0.15)",
              color: "hsl(var(--cyan))",
              border: "1px solid hsl(var(--cyan) / 0.3)",
            }}
          >
            <Scan className={`w-4 h-4 ${scanning ? "animate-spin" : ""}`} />
            {scanning ? "Scanning..." : "Scan Devices"}
          </button>

          <div className="flex gap-3">
            {[
              {
                label: "USB Devices",
                value: devices.usb.length,
                icon: Usb,
                color: "cyan",
              },
              {
                label: "LAN Nodes",
                value: devices.lan.length,
                icon: Network,
                color: "cyan",
              },
              {
                label: "Risky Devices",
                value: criticalDevices.length,
                icon: AlertTriangle,
                color: "critical",
              },
            ].map((s) => (
              <div key={s.label} className="cyber-card px-4 py-3 flex items-center gap-3">
                <s.icon
                  className="w-4 h-4"
                  style={{ color: `hsl(var(--${s.color}))` }}
                />
                <div>
                  <p className="text-xs text-muted-foreground">{s.label}</p>
                  <p
                    className="text-lg font-bold font-mono"
                    style={{ color: `hsl(var(--${s.color}))` }}
                  >
                    {s.value}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {criticalDevices.length > 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="rounded-lg p-4 flex items-start gap-3"
            style={{
              background: "hsl(var(--critical) / 0.08)",
              border: "1px solid hsl(var(--critical) / 0.3)",
            }}
          >
            <AlertTriangle className="w-4 h-4 text-cyber-critical shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-cyber-critical">Security Alert</p>
              <p className="text-xs text-muted-foreground">
                {criticalDevices.length} high-risk device(s) detected. Potential
                unauthorized hardware or unknown network adapters present in the
                air-gapped environment.
              </p>
            </div>
          </motion.div>
        )}

        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="cyber-card overflow-hidden"
        >
          <div className="flex items-center gap-2 px-5 py-4 border-b border-border">
            <Usb className="w-4 h-4 text-cyan" />
            <h3 className="text-sm font-semibold">USB Devices</h3>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                {["Device", "VID:PID", "Type", "Risk", "Inserted", "Status"].map(
                  (h) => (
                    <th
                      key={h}
                      className="text-left px-4 py-2.5 text-xs font-semibold text-muted-foreground uppercase tracking-wide"
                    >
                      {h}
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {devices.usb.map((device, i) => (
                <motion.tr
                  key={device.id}
                  className="table-row-cyber border-b border-border/50 last:border-0"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.05 }}
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-foreground">
                        {device.name}
                      </span>
                      {device.is_new && (
                        <span
                          className="text-xs font-mono px-1.5 py-0.5 rounded"
                          style={{
                            background: "hsl(var(--high) / 0.15)",
                            color: "hsl(var(--high))",
                          }}
                        >
                          NEW
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                    {device.vid}:{device.pid}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-foreground">
                    {device.type}
                  </td>
                  <td className="px-4 py-3">
                    <RiskBadge risk={device.risk} />
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                    {formatDate(device.inserted_at)}
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs text-cyber-low">Connected</span>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="cyber-card overflow-hidden"
        >
          <div className="flex items-center gap-2 px-5 py-4 border-b border-border">
            <Network className="w-4 h-4 text-cyan" />
            <h3 className="text-sm font-semibold">LAN Nodes</h3>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                {["IP Address", "Hostname", "MAC", "OS", "Risk", "Status"].map(
                  (h) => (
                    <th
                      key={h}
                      className="text-left px-4 py-2.5 text-xs font-semibold text-muted-foreground uppercase tracking-wide"
                    >
                      {h}
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {devices.lan.map((node, i) => (
                <motion.tr
                  key={node.id}
                  className="table-row-cyber border-b border-border/50 last:border-0"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.05 }}
                >
                  <td className="px-4 py-3 font-mono text-xs text-cyan">{node.ip}</td>
                  <td className="px-4 py-3 font-mono text-xs text-foreground">
                    {node.hostname}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                    {node.mac}
                  </td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">{node.os}</td>
                  <td className="px-4 py-3">
                    <RiskBadge risk={node.risk} />
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs text-cyber-low">{node.status}</span>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </motion.div>
      </div>
    </AppLayout>
  );
}

