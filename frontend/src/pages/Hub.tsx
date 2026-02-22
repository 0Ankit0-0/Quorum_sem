import { useState } from "react";
import { motion } from "framer-motion";
import { Network, Download, Plus, AlertTriangle } from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import { formatTimeAgo, formatNumber } from "@/lib/formatters";
import { useQuorumData } from "@/hooks/useQuorumData";
import { exportSyncPackage, registerNode } from "@/lib/api-functions";
import { toast } from "sonner";

export default function Hub() {
  const { nodes, correlations, refresh } = useQuorumData();
  const [registering, setRegistering] = useState(false);
  const [exporting, setExporting] = useState(false);

  const handleRegister = async () => {
    setRegistering(true);
    try {
      const node = await registerNode("terminal");
      await refresh();
      toast.success(`Node registered: ${node.hostname}`);
    } catch (error) {
      console.error("Node registration failed", error);
      toast.error("Failed to register node");
    } finally {
      setRegistering(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const { blob, filename } = await exportSyncPackage("hub", true);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success(`Exported ${filename}`);
    } catch (error) {
      console.error("Sync export failed", error);
      toast.error("Failed to export sync package");
    } finally {
      setExporting(false);
    }
  };

  return (
    <AppLayout
      title="Multi-Node Hub"
      subtitle="Cross-node correlation and sync management"
    >
      <div className="space-y-6">
        <div className="flex gap-3 flex-wrap">
          <button
            onClick={handleRegister}
            disabled={registering}
            className="flex items-center gap-2 px-4 py-2.5 rounded-md text-sm font-semibold transition-all disabled:opacity-50"
            style={{
              background: "hsl(var(--cyan) / 0.15)",
              color: "hsl(var(--cyan))",
              border: "1px solid hsl(var(--cyan) / 0.3)",
            }}
          >
            <Plus className="w-4 h-4" />
            {registering ? "Registering..." : "Register Node"}
          </button>
          <button
            onClick={handleExport}
            disabled={exporting}
            className="flex items-center gap-2 px-4 py-2.5 rounded-md text-sm font-semibold transition-all disabled:opacity-50"
            style={{
              background: "hsl(var(--muted))",
              color: "hsl(var(--foreground))",
              border: "1px solid hsl(var(--border))",
            }}
          >
            <Download className="w-4 h-4" />
            {exporting ? "Exporting..." : "Export Sync Package (.qsp)"}
          </button>
        </div>

        <div>
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <Network className="w-4 h-4 text-cyan" /> Node Registry
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {nodes.map((node, i) => (
              <motion.div
                key={node.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.06 }}
                className="cyber-card p-4"
                style={
                  node.status === "ONLINE"
                    ? { borderColor: "hsl(var(--cyan) / 0.2)" }
                    : { borderColor: "hsl(var(--border))", opacity: 0.7 }
                }
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <p className="font-mono text-sm font-semibold text-foreground">
                      {node.hostname}
                    </p>
                    <p className="text-xs text-muted-foreground font-mono">
                      {node.id} - {node.role.toUpperCase()}
                    </p>
                  </div>
                  <span
                    className="text-xs font-mono"
                    style={{
                      color:
                        node.status === "ONLINE"
                          ? "hsl(var(--low))"
                          : "hsl(var(--muted-foreground))",
                    }}
                  >
                    {node.status}
                  </span>
                </div>
                <div className="space-y-1.5 text-xs font-mono">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Total Logs</span>
                    <span className="text-foreground">{formatNumber(node.total_logs)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Anomalies</span>
                    <span className="text-cyber-critical">
                      {formatNumber(node.anomalies)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Last Sync</span>
                    <span className="text-cyan">{formatTimeAgo(node.last_sync)}</span>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="cyber-card overflow-hidden"
        >
          <div className="px-5 py-4 border-b border-border flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-cyber-critical" />
            <div>
              <h3 className="text-sm font-semibold">Cross-Node Correlations</h3>
              <p className="text-xs text-muted-foreground">
                Coordinated attack patterns detected across multiple nodes
              </p>
            </div>
          </div>
          <div className="p-4 space-y-3">
            {correlations.map((c, i) => (
              <motion.div
                key={c.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + i * 0.08 }}
                className="p-4 rounded-md border"
                style={{
                  background: "hsl(var(--critical) / 0.04)",
                  borderColor: "hsl(var(--critical) / 0.2)",
                }}
              >
                <div className="flex items-start justify-between flex-wrap gap-3">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono text-sm text-cyan">{c.mitre_id}</span>
                      <span className="text-sm font-semibold text-foreground">
                        {c.technique}
                      </span>
                      <span className="badge-critical">{c.severity}</span>
                    </div>
                    <p className="text-xs text-muted-foreground mb-2">{c.tactic}</p>
                    <div className="flex flex-wrap gap-1.5">
                      {c.affected_nodes.map((n) => (
                        <span
                          key={n}
                          className="text-xs font-mono px-2 py-0.5 rounded"
                          style={{
                            background: "hsl(var(--cyan) / 0.1)",
                            color: "hsl(var(--cyan))",
                            border: "1px solid hsl(var(--cyan) / 0.2)",
                          }}
                        >
                          {n}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-bold font-mono text-cyber-critical">
                      {formatNumber(c.total_events)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      events across {c.node_count} nodes
                    </p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </AppLayout>
  );
}

