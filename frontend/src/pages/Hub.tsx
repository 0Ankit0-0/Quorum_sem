import { motion } from "framer-motion";
import { Network, Download, Plus, AlertTriangle } from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import { mockNodes, mockCorrelations, formatTimeAgo, formatNumber } from "@/lib/mockData";

export default function Hub() {
  return (
    <AppLayout title="Multi-Node Hub" subtitle="Cross-node correlation & sync management">
      <div className="space-y-6">
        {/* Actions */}
        <div className="flex gap-3 flex-wrap">
          <button className="flex items-center gap-2 px-4 py-2.5 rounded-md text-sm font-semibold transition-all"
            style={{ background: "hsl(var(--cyan) / 0.15)", color: "hsl(var(--cyan))", border: "1px solid hsl(var(--cyan) / 0.3)" }}>
            <Plus className="w-4 h-4" /> Register Node
          </button>
          <button className="flex items-center gap-2 px-4 py-2.5 rounded-md text-sm font-semibold transition-all"
            style={{ background: "hsl(var(--muted))", color: "hsl(var(--foreground))", border: "1px solid hsl(var(--border))" }}>
            <Download className="w-4 h-4" /> Export Sync Package (.qsp)
          </button>
        </div>

        {/* Nodes Grid */}
        <div>
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <Network className="w-4 h-4 text-cyan" /> Node Registry
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {mockNodes.map((node, i) => (
              <motion.div key={node.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.06 }}
                className="cyber-card p-4"
                style={node.status === "ONLINE" ? { borderColor: "hsl(var(--cyan) / 0.2)" } : { borderColor: "hsl(var(--border))", opacity: 0.7 }}
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <p className="font-mono text-sm font-semibold text-foreground">{node.hostname}</p>
                    <p className="text-xs text-muted-foreground font-mono">{node.id} · {node.role.toUpperCase()}</p>
                  </div>
                  <span className="text-xs font-mono" style={{ color: node.status === "ONLINE" ? "hsl(var(--low))" : "hsl(var(--muted-foreground))" }}>
                    ● {node.status}
                  </span>
                </div>
                <div className="space-y-1.5 text-xs font-mono">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Total Logs</span>
                    <span className="text-foreground">{formatNumber(node.total_logs)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Anomalies</span>
                    <span className="text-cyber-critical">{formatNumber(node.anomalies)}</span>
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

        {/* Cross-Node Correlations */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }} className="cyber-card overflow-hidden">
          <div className="px-5 py-4 border-b border-border flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-cyber-critical" />
            <div>
              <h3 className="text-sm font-semibold">Cross-Node Correlations</h3>
              <p className="text-xs text-muted-foreground">Coordinated attack patterns detected across multiple nodes</p>
            </div>
          </div>
          <div className="p-4 space-y-3">
            {mockCorrelations.map((c, i) => (
              <motion.div key={c.id} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.3 + i * 0.08 }}
                className="p-4 rounded-md border"
                style={{ background: "hsl(var(--critical) / 0.04)", borderColor: "hsl(var(--critical) / 0.2)" }}
              >
                <div className="flex items-start justify-between flex-wrap gap-3">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono text-sm text-cyan">{c.mitre_id}</span>
                      <span className="text-sm font-semibold text-foreground">{c.technique}</span>
                      <span className="badge-critical">{c.severity}</span>
                    </div>
                    <p className="text-xs text-muted-foreground mb-2">{c.tactic}</p>
                    <div className="flex flex-wrap gap-1.5">
                      {c.affected_nodes.map(n => (
                        <span key={n} className="text-xs font-mono px-2 py-0.5 rounded" style={{ background: "hsl(var(--cyan) / 0.1)", color: "hsl(var(--cyan))", border: "1px solid hsl(var(--cyan) / 0.2)" }}>{n}</span>
                      ))}
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-bold font-mono text-cyber-critical">{formatNumber(c.total_events)}</p>
                    <p className="text-xs text-muted-foreground">events across {c.node_count} nodes</p>
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
