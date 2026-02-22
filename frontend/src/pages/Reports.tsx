import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { BarChart3, Download, FileText, FileSpreadsheet } from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import { formatDate } from "@/lib/formatters";
import { useQuorumData } from "@/hooks/useQuorumData";
import { downloadReport, generateReport } from "@/lib/api-functions";
import { toast } from "sonner";

export default function Reports() {
  const { reports, sessions, refresh } = useQuorumData();
  const [reportType, setReportType] = useState<"PDF" | "CSV">("PDF");
  const [selectedSession, setSelectedSession] = useState("");
  const [generating, setGenerating] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedSession && sessions.length > 0) {
      setSelectedSession(sessions[0].id);
    }
  }, [sessions, selectedSession]);

  const handleGenerate = async () => {
    if (!selectedSession) {
      toast.error("Select a session first");
      return;
    }

    setGenerating(true);
    try {
      const result = await generateReport(reportType, selectedSession);
      await refresh();
      toast.success(`Generated ${result.filename}`);
    } catch (error) {
      console.error("Report generation failed", error);
      toast.error("Failed to generate report");
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = async (filename: string) => {
    setDownloading(filename);
    try {
      const blob = await downloadReport(filename);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Download failed", error);
      toast.error("Failed to download report");
    } finally {
      setDownloading(null);
    }
  };

  return (
    <AppLayout title="Reports" subtitle="Generate and download analysis reports">
      <div className="space-y-6">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="cyber-card p-6"
        >
          <h3 className="text-sm font-semibold mb-5 flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-cyan" /> Generate Report
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
            <div>
              <label className="text-xs text-muted-foreground uppercase tracking-wide block mb-2">
                Report Type
              </label>
              <div className="flex gap-2">
                {(["PDF", "CSV"] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => setReportType(t)}
                    className="flex-1 flex items-center justify-center gap-2 py-2 rounded-md text-sm font-semibold border transition-all"
                    style={
                      reportType === t
                        ? {
                            background: "hsl(var(--cyan) / 0.1)",
                            borderColor: "hsl(var(--cyan) / 0.4)",
                            color: "hsl(var(--cyan))",
                          }
                        : {
                            background: "hsl(var(--muted))",
                            borderColor: "hsl(var(--border))",
                            color: "hsl(var(--muted-foreground))",
                          }
                    }
                  >
                    {t === "PDF" ? (
                      <FileText className="w-4 h-4" />
                    ) : (
                      <FileSpreadsheet className="w-4 h-4" />
                    )}
                    {t}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-xs text-muted-foreground uppercase tracking-wide block mb-2">
                Analysis Session
              </label>
              <select
                value={selectedSession}
                onChange={(e) => setSelectedSession(e.target.value)}
                className="w-full bg-muted border border-border rounded-md px-3 py-2 text-sm text-foreground font-mono outline-none focus:border-cyan/40"
              >
                {sessions.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.id} - {s.algorithm} ({s.anomalies_found} anomalies)
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={handleGenerate}
              disabled={generating || !selectedSession}
              className="flex items-center justify-center gap-2 py-2.5 rounded-md text-sm font-semibold transition-all"
              style={{
                background: generating ? "hsl(var(--muted))" : "hsl(var(--cyan))",
                color: generating
                  ? "hsl(var(--muted-foreground))"
                  : "hsl(var(--background))",
              }}
            >
              <Download className="w-4 h-4" />
              {generating ? "Generating..." : `Generate ${reportType}`}
            </button>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="cyber-card overflow-hidden"
        >
          <div className="px-5 py-4 border-b border-border">
            <h3 className="text-sm font-semibold">Available Reports</h3>
            <p className="text-xs text-muted-foreground">
              {reports.length} reports ready for download
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  {["Report", "Type", "Session", "Size", "Created", "Action"].map((h) => (
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
                {reports.map((r, i) => (
                  <motion.tr
                    key={r.id}
                    className="table-row-cyber border-b border-border/50 last:border-0"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.06 }}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {r.type === "PDF" ? (
                          <FileText className="w-4 h-4 text-cyber-critical shrink-0" />
                        ) : (
                          <FileSpreadsheet className="w-4 h-4 text-cyber-low shrink-0" />
                        )}
                        <span className="text-xs text-foreground">{r.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className="font-mono text-xs px-2 py-0.5 rounded"
                        style={
                          r.type === "PDF"
                            ? {
                                background: "hsl(var(--critical) / 0.1)",
                                color: "hsl(var(--critical))",
                              }
                            : {
                                background: "hsl(var(--low) / 0.1)",
                                color: "hsl(var(--low))",
                              }
                        }
                      >
                        {r.type}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-cyan">{r.session_id}</td>
                    <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                      {r.size_kb} KB
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                      {formatDate(r.created_at)}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleDownload(r.name)}
                        disabled={downloading === r.name}
                        className="flex items-center gap-1.5 text-xs text-cyan hover:text-cyan/80 transition-colors font-semibold disabled:opacity-50"
                      >
                        <Download className="w-3.5 h-3.5" />
                        {downloading === r.name ? "Downloading..." : "Download"}
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

