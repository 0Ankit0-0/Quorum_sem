import { motion } from "framer-motion";
import { Activity, AlertTriangle, FileText, Server, TrendingUp, Zap } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, Legend,
  ResponsiveContainer, Area, AreaChart
} from "recharts";
import {
  formatTimeAgo, formatNumber
} from "@/lib/formatters";
import { useQuorumData } from "@/hooks/useQuorumData";

const fadeUp = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0 } };
const container = { hidden: {}, show: { transition: { staggerChildren: 0.06 } } };

const SeverityBadge = ({ severity }: { severity: string }) => {
  const map: Record<string, string> = {
    CRITICAL: "badge-critical",
    HIGH: "badge-high",
    MEDIUM: "badge-medium",
    LOW: "badge-low",
  };
  return <span className={map[severity] || "badge-low"}>{severity}</span>;
};

const StatCard = ({
  icon: Icon,
  label,
  value,
  sub,
  color = "cyan",
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  sub?: string;
  color?: string;
}) => {
  const colorMap: Record<string, string> = {
    cyan: "var(--cyan)",
    critical: "var(--critical)",
    high: "var(--high)",
    low: "var(--low)",
  };
  const c = colorMap[color] || colorMap.cyan;

  return (
    <motion.div
      variants={fadeUp}
      className="cyber-card p-5 flex items-start gap-4"
    >
      <div
        className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
        style={{ background: `hsl(${c} / 0.12)`, border: `1px solid hsl(${c} / 0.3)` }}
      >
        <Icon className="w-5 h-5" style={{ color: `hsl(${c})` }} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">{label}</p>
        <p className="stat-value" style={{ color: `hsl(${c})` }}>{value}</p>
        {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
      </div>
    </motion.div>
  );
};

interface TooltipItem {
  name: string;
  value: string | number;
  color?: string;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipItem[];
  label?: string | number;
}

const CustomTooltip = ({ active, payload, label }: CustomTooltipProps) => {
  if (active && payload?.length) {
    return (
      <div className="cyber-card px-3 py-2 text-xs font-mono">
        <p className="text-muted-foreground mb-1">{label}</p>
        {payload.map((p) => (
          <p key={p.name} style={{ color: p.color }}>
            {p.name}: {p.value}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

export default function Dashboard() {
  const { systemStatus, severityDistribution, timelineData, anomalies } =
    useQuorumData();

  return (
    <AppLayout title="Dashboard" subtitle="System overview — Air-Gapped Environment">
      <motion.div variants={container} initial="hidden" animate="show" className="space-y-6">
        {/* Stats Row */}
        <motion.div variants={container} className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard icon={FileText} label="Total Logs" value={formatNumber(systemStatus.total_logs)} sub="All-time ingested" color="cyan" />
          <StatCard icon={AlertTriangle} label="Anomalies" value={formatNumber(systemStatus.total_anomalies)} sub="Detected threats" color="critical" />
          <StatCard icon={Activity} label="Sessions" value={String(systemStatus.active_sessions)} sub="Analysis runs" color="high" />
          <StatCard icon={Server} label="Nodes Online" value={`${systemStatus.nodes_online}/8`} sub="Hub + terminals" color="low" />
        </motion.div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
          {/* Severity Distribution */}
          <motion.div variants={fadeUp} className="cyber-card p-5 lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-semibold">Severity Distribution</h3>
                <p className="text-xs text-muted-foreground">Current session</p>
              </div>
              <TrendingUp className="w-4 h-4 text-muted-foreground" />
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={severityDistribution} barSize={36} barCategoryGap="30%">
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                <XAxis dataKey="severity" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))", fontFamily: "JetBrains Mono" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} width={32} />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: "hsl(var(--cyan) / 0.05)" }} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={48}>
                  {severityDistribution.map((entry, index) => (
                    <Cell key={index} fill={entry.fill} fillOpacity={0.85} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </motion.div>

          {/* Timeline */}
          <motion.div variants={fadeUp} className="cyber-card p-5 lg:col-span-3">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-semibold">Anomaly Timeline</h3>
                <p className="text-xs text-muted-foreground">Last 24 hours</p>
              </div>
              <Zap className="w-4 h-4 text-muted-foreground" />
            </div>
            {timelineData.length === 0 ? (
              <div className="h-[200px] flex flex-col items-center justify-center gap-2">
                <Zap className="w-6 h-6 text-muted-foreground/30" />
                <p className="text-xs text-muted-foreground/50 font-mono">No timeline data</p>
              </div>
            ) : (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={timelineData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="gradAnomalies" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(192 100% 50%)" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="hsl(192 100% 50%)" stopOpacity={0.02} />
                  </linearGradient>
                  <linearGradient id="gradCritical" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(0 84% 60%)" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="hsl(0 84% 60%)" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))", fontFamily: "JetBrains Mono" }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
                <YAxis tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} width={32} />
                <Tooltip content={<CustomTooltip />} />
                <Legend
                  iconType="circle"
                  iconSize={6}
                  wrapperStyle={{ fontSize: "10px", fontFamily: "JetBrains Mono", paddingTop: "4px" }}
                  formatter={(value) => <span style={{ color: "hsl(var(--muted-foreground))" }}>{value}</span>}
                />
                <Area type="monotone" dataKey="anomalies" stroke="hsl(192 100% 50%)" fill="url(#gradAnomalies)" strokeWidth={1.5} name="Anomalies" dot={false} activeDot={{ r: 3, strokeWidth: 0, fill: "hsl(192 100% 50%)" }} />
                <Area type="monotone" dataKey="critical" stroke="hsl(0 84% 60%)" fill="url(#gradCritical)" strokeWidth={1.5} name="Critical" dot={false} activeDot={{ r: 3, strokeWidth: 0, fill: "hsl(0 84% 60%)" }} />
              </AreaChart>
            </ResponsiveContainer>
            )}
          </motion.div>
        </div>

        {/* Recent Anomalies Table */}
        <motion.div variants={fadeUp} className="cyber-card overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-border">
            <div>
              <h3 className="text-sm font-semibold">Recent Anomalies</h3>
              <p className="text-xs text-muted-foreground">Latest detected threats</p>
            </div>
            <span className="badge-critical">{anomalies.filter(a => a.severity === "CRITICAL").length} CRITICAL</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  {["ID", "Time", "Severity", "Source", "MITRE", "Score", "Message"].map(h => (
                    <th key={h} className="text-left px-4 py-2.5 text-xs font-semibold text-muted-foreground uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {anomalies.map((a, i) => (
                  <motion.tr
                    key={a.id}
                    className="table-row-cyber border-b border-border/50 last:border-0"
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.04 }}
                  >
                    <td className="px-4 py-3 font-mono text-xs text-cyan">{a.id}</td>
                    <td className="px-4 py-3 font-mono text-xs text-muted-foreground whitespace-nowrap">{formatTimeAgo(a.timestamp)}</td>
                    <td className="px-4 py-3"><SeverityBadge severity={a.severity} /></td>
                    <td className="px-4 py-3 font-mono text-xs text-foreground">{a.source}</td>
                    <td className="px-4 py-3">
                      <div>
                        <span className="font-mono text-xs text-cyan">{a.mitre_id}</span>
                        <p className="text-xs text-muted-foreground">{a.mitre_tactic}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 rounded-full bg-muted overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${a.score * 100}%`,
                              background: a.score > 0.9 ? "hsl(var(--critical))" : a.score > 0.75 ? "hsl(var(--high))" : a.score > 0.55 ? "hsl(var(--medium))" : "hsl(var(--low))"
                            }}
                          />
                        </div>
                        <span className="font-mono text-xs text-muted-foreground">{a.score.toFixed(2)}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs text-foreground max-w-xs truncate">{a.message}</td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      </motion.div>
    </AppLayout>
  );
}

