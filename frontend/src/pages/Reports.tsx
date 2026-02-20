import { useState } from "react";
import { motion } from "framer-motion";
import { BarChart3, Download, FileText, FileSpreadsheet } from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import { mockReports, mockSessions, formatDate } from "@/lib/mockData";

export default function Reports() {
  const [reportType, setReportType] = useState("PDF");
  const [selectedSession, setSelectedSession] = useState(mockSessions[0].id);
  const [generating, setGenerating] = useState(false);

  const handleGenerate = () => {
    setGenerating(true);
    setTimeout(() => setGenerating(false), 2000);
  };

  return (
    <AppLayout title="Reports" subtitle="Generate & download analysis reports">
      <div className="space-y-6">
        {/* Generator Form */}
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="cyber-card p-6">
          <h3 className="text-sm font-semibold mb-5 flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-cyan" /> Generate Report
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
            {/* Report Type */}
            <div>
              <label className="text-xs text-muted-foreground uppercase tracking-wide block mb-2">Report Type</label>
              <div className="flex gap-2">
                {["PDF", "CSV"].map(t => (
                  <button key={t} onClick={() => setReportType(t)}
                    className="flex-1 flex items-center justify-center gap-2 py-2 rounded-md text-sm font-semibold border transition-all"
                    style={reportType === t
                      ? { background: "hsl(var(--cyan) / 0.1)", borderColor: "hsl(var(--cyan) / 0.4)", color: "hsl(var(--cyan))" }
                      : { background: "hsl(var(--muted))", borderColor: "hsl(var(--border))", color: "hsl(var(--muted-foreground))" }
                    }
                  >
                    {t === "PDF" ? <FileText className="w-4 h-4" /> : <FileSpreadsheet className="w-4 h-4" />}
                    {t}
                  </button>
                ))}
              </div>
            </div>

            {/* Session Selector */}
            <div>
              <label className="text-xs text-muted-foreground uppercase tracking-wide block mb-2">Analysis Session</label>
              <select
                value={selectedSession}
                onChange={e => setSelectedSession(e.target.value)}
                className="w-full bg-muted border border-border rounded-md px-3 py-2 text-sm text-foreground font-mono outline-none focus:border-cyan/40"
              >
                {mockSessions.map(s => (
                  <option key={s.id} value={s.id}>{s.id} — {s.algorithm} ({s.anomalies_found} anomalies)</option>
                ))}
              </select>
            </div>

            {/* Generate Button */}
            <button onClick={handleGenerate} disabled={generating}
              className="flex items-center justify-center gap-2 py-2.5 rounded-md text-sm font-semibold transition-all"
              style={{ background: generating ? "hsl(var(--muted))" : "hsl(var(--cyan))", color: generating ? "hsl(var(--muted-foreground))" : "hsl(var(--background))" }}
            >
              <Download className="w-4 h-4" />
              {generating ? "Generating..." : `Generate ${reportType}`}
            </button>
          </div>
        </motion.div>

        {/* Reports List */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }} className="cyber-card overflow-hidden">
          <div className="px-5 py-4 border-b border-border">
            <h3 className="text-sm font-semibold">Available Reports</h3>
            <p className="text-xs text-muted-foreground">{mockReports.length} reports ready for download</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  {["Report", "Type", "Session", "Size", "Created", "Action"].map(h => (
                    <th key={h} className="text-left px-4 py-2.5 text-xs font-semibold text-muted-foreground uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {mockReports.map((r, i) => (
                  <motion.tr key={r.id} className="table-row-cyber border-b border-border/50 last:border-0"
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.06 }}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {r.type === "PDF" ? <FileText className="w-4 h-4 text-cyber-critical shrink-0" /> : <FileSpreadsheet className="w-4 h-4 text-cyber-low shrink-0" />}
                        <span className="text-xs text-foreground">{r.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="font-mono text-xs px-2 py-0.5 rounded" style={r.type === "PDF"
                        ? { background: "hsl(var(--critical) / 0.1)", color: "hsl(var(--critical))" }
                        : { background: "hsl(var(--low) / 0.1)", color: "hsl(var(--low))" }
                      }>{r.type}</span>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-cyan">{r.session_id}</td>
                    <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{r.size_kb} KB</td>
                    <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{formatDate(r.created_at)}</td>
                    <td className="px-4 py-3">
                      <button className="flex items-center gap-1.5 text-xs text-cyan hover:text-cyan/80 transition-colors font-semibold">
                        <Download className="w-3.5 h-3.5" /> Download
                      </button>
                    </td>
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
