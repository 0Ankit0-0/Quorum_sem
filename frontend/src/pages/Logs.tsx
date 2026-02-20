import { useState } from "react";
import { motion } from "framer-motion";
import { Upload, FileText, CheckCircle, XCircle, AlertCircle } from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import { mockLogs, formatDate } from "@/lib/mockData";

const SeverityBadge = ({ severity }: { severity: string }) => {
  const map: Record<string, string> = { CRITICAL: "badge-critical", HIGH: "badge-high", MEDIUM: "badge-medium", LOW: "badge-low" };
  return <span className={map[severity] || "badge-low"}>{severity}</span>;
};

export default function Logs() {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadResult, setUploadResult] = useState<null | { entries: number; errors: number; duration: number }>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    simulateUpload();
  };

  const simulateUpload = () => {
    setUploading(true);
    setUploadProgress(0);
    const interval = setInterval(() => {
      setUploadProgress(p => {
        if (p >= 100) {
          clearInterval(interval);
          setUploading(false);
          setUploadResult({ entries: 84312, errors: 3, duration: 11.4 });
          return 100;
        }
        return p + Math.random() * 15;
      });
    }, 150);
  };

  return (
    <AppLayout title="Log Management" subtitle="Upload & analyze log files">
      <div className="space-y-6">
        {/* Upload Zone */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className={`relative rounded-lg border-2 border-dashed transition-all duration-200 p-12 text-center cursor-pointer ${
            dragOver
              ? "border-cyan bg-cyan/5"
              : "border-border hover:border-muted-foreground"
          }`}
          style={{ background: dragOver ? "hsl(var(--cyan) / 0.05)" : "hsl(var(--card))" }}
          onDragOver={e => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={simulateUpload}
        >
          <Upload className="w-10 h-10 text-muted-foreground mx-auto mb-4" />
          <p className="text-base font-medium text-foreground mb-1">Drop log files here or click to upload</p>
          <p className="text-sm text-muted-foreground">Supports .evtx, .log, .syslog, .csv, .txt — Max 100MB</p>

          {uploading && (
            <div className="mt-6">
              <div className="flex justify-between text-xs font-mono text-muted-foreground mb-1">
                <span>Uploading & ingesting...</span>
                <span>{Math.round(uploadProgress)}%</span>
              </div>
              <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                <motion.div
                  className="h-full rounded-full"
                  style={{ background: "hsl(var(--cyan))" }}
                  animate={{ width: `${uploadProgress}%` }}
                  transition={{ duration: 0.1 }}
                />
              </div>
            </div>
          )}
        </motion.div>

        {/* Upload Result */}
        {uploadResult && (
          <motion.div
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            className="cyber-card p-4 flex items-center gap-6"
            style={{ borderColor: "hsl(var(--low) / 0.4)" }}
          >
            <CheckCircle className="w-6 h-6 text-cyber-low shrink-0" />
            <div className="flex gap-6 text-sm">
              <div><p className="text-muted-foreground text-xs">Entries Inserted</p><p className="font-mono font-semibold text-foreground">{uploadResult.entries.toLocaleString()}</p></div>
              <div><p className="text-muted-foreground text-xs">Errors</p><p className="font-mono font-semibold text-cyber-critical">{uploadResult.errors}</p></div>
              <div><p className="text-muted-foreground text-xs">Duration</p><p className="font-mono font-semibold text-cyan">{uploadResult.duration}s</p></div>
            </div>
          </motion.div>
        )}

        {/* Logs Table */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }} className="cyber-card overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-border">
            <div>
              <h3 className="text-sm font-semibold">Recent Logs</h3>
              <p className="text-xs text-muted-foreground">Last 50 ingested entries</p>
            </div>
            <div className="flex items-center gap-2">
              <input
                placeholder="Filter logs..."
                className="text-xs bg-muted border border-border rounded-md px-3 py-1.5 text-foreground placeholder:text-muted-foreground font-mono outline-none focus:border-cyan/50 w-48"
              />
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  {["ID", "Timestamp", "Severity", "Source", "Message", "Entries"].map(h => (
                    <th key={h} className="text-left px-4 py-2.5 text-xs font-semibold text-muted-foreground uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {mockLogs.map((log, i) => (
                  <motion.tr
                    key={log.id}
                    className="table-row-cyber border-b border-border/50 last:border-0 cursor-pointer"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.05 }}
                  >
                    <td className="px-4 py-3 font-mono text-xs text-cyan">{log.id}</td>
                    <td className="px-4 py-3 font-mono text-xs text-muted-foreground whitespace-nowrap">{formatDate(log.timestamp)}</td>
                    <td className="px-4 py-3"><SeverityBadge severity={log.severity} /></td>
                    <td className="px-4 py-3 font-mono text-xs text-foreground">{log.source}</td>
                    <td className="px-4 py-3 text-xs text-foreground max-w-sm truncate">{log.message}</td>
                    <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{log.entries}</td>
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
