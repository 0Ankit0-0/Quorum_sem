import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { CheckCircle2, Copy, Download, FileArchive, FileJson, FileSpreadsheet, RefreshCw } from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import {
  downloadDatasetReportFile,
  downloadDatasetReportZip,
  generateDatasetReport,
  getUploadedFiles,
  listDatasetReports,
  type UploadedFile,
} from "@/lib/api-functions";
import { formatDate } from "@/lib/formatters";
import { toast } from "sonner";

interface DatasetReport {
  report_id: string;
  created_at: string;
  report_dir: string;
  hash_sha256: string;
  files: string[];
}

const downloadBlob = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
};

export default function Reports() {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [selectedFile, setSelectedFile] = useState("");
  const [reports, setReports] = useState<DatasetReport[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);

  const selectedMeta = useMemo(
    () => files.find((f) => f.filename === selectedFile) ?? null,
    [files, selectedFile],
  );

  const loadFiles = useCallback(async () => {
    const data = await getUploadedFiles();
    setFiles(data.files ?? []);
    if (!selectedFile && data.files.length > 0) {
      setSelectedFile(data.files[0].filename);
    }
  }, [selectedFile]);

  const loadReports = useCallback(async (filename: string) => {
    if (!filename) {
      setReports([]);
      return;
    }
    setLoading(true);
    try {
      const rows = await listDatasetReports(filename);
      setReports(
        rows.map((row) => ({
          report_id: String(row.report_id ?? ""),
          created_at: String(row.created_at ?? new Date().toISOString()),
          report_dir: String(row.report_dir ?? ""),
          hash_sha256: String(row.hash_sha256 ?? ""),
          files: Array.isArray(row.files) ? row.files.map((f) => String(f)) : [],
        })),
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadFiles();
  }, [loadFiles]);

  useEffect(() => {
    if (!selectedFile) return;
    void loadReports(selectedFile);
  }, [loadReports, selectedFile]);

  const handleGenerate = async () => {
    if (!selectedFile) return;
    setGenerating(true);
    try {
      const result = await generateDatasetReport(selectedFile);
      toast.success(`Report ${result.report_id} generated`);
      await loadReports(selectedFile);
    } catch (error) {
      console.error(error);
      toast.error("Failed to generate report bundle");
    } finally {
      setGenerating(false);
    }
  };

  const handleDownloadSingle = async (
    reportId: string,
    file: "summary.json" | "anomalies.csv" | "ai_analysis.json",
  ) => {
    if (!selectedFile) return;
    try {
      const blob = await downloadDatasetReportFile(selectedFile, reportId, file);
      downloadBlob(blob, `${selectedFile}.${reportId}.${file}`);
    } catch (error) {
      console.error(error);
      toast.error(`Failed downloading ${file}`);
    }
  };

  const handleDownloadZip = async (reportId: string) => {
    if (!selectedFile) return;
    try {
      const { blob, hash } = await downloadDatasetReportZip(selectedFile, reportId);
      downloadBlob(blob, `${selectedFile}.${reportId}.zip`);
      toast.success(`ZIP downloaded (hash: ${hash.slice(0, 12)}...)`);
    } catch (error) {
      console.error(error);
      toast.error("Failed downloading report bundle");
    }
  };

  return (
    <AppLayout title="Reports" subtitle="Dataset-scoped report bundles with secure downloads">
      <div className="space-y-4">
        <div className="cyber-card p-4 space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-end">
            <div className="md:col-span-2">
              <label className="text-xs text-muted-foreground uppercase tracking-wide block mb-2">Dataset File</label>
              <select
                value={selectedFile}
                onChange={(e) => setSelectedFile(e.target.value)}
                className="w-full bg-muted border border-border rounded-md px-3 py-2 text-sm text-foreground font-mono outline-none focus:border-cyan/40"
              >
                {files.length === 0 && <option value="">No uploaded datasets</option>}
                {files.map((f) => (
                  <option key={f.filename} value={f.filename}>
                    {f.filename}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => void loadReports(selectedFile)}
                className="px-3 py-2 rounded-md text-xs font-semibold flex items-center gap-1.5 border border-border hover:border-cyan/40"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Refresh
              </button>
              <button
                onClick={() => void handleGenerate()}
                disabled={!selectedFile || generating}
                className="px-3 py-2 rounded-md text-xs font-semibold disabled:opacity-60 min-w-[92px]"
                style={{ background: "hsl(var(--cyan))", color: "hsl(var(--background))" }}
              >
                {generating ? "Generating..." : "Generate"}
              </button>
            </div>
          </div>

          <div className="text-xs font-mono text-muted-foreground flex gap-4 flex-wrap">
            <span>Uploaded: {selectedMeta ? formatDate(selectedMeta.uploaded_at) : "-"}</span>
            <span>Records: {(selectedMeta?.record_count ?? 0).toLocaleString()}</span>
            <span>DB: {selectedMeta?.dataset_id ?? "N/A"}</span>
          </div>
        </div>

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="cyber-card overflow-hidden">
          <div className="px-4 py-3 border-b border-border flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold">Generated Reports</h3>
              <p className="text-xs text-muted-foreground">
                {loading ? "Loading..." : `${reports.length} report bundle(s) for selected dataset`}
              </p>
            </div>
            {reports.length > 0 && (
              <span className="text-[10px] font-mono text-muted-foreground/60 border border-border px-2 py-0.5 rounded">
                SHA-256 verified
              </span>
            )}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left px-4 py-2.5 text-xs font-semibold text-muted-foreground uppercase tracking-wide w-[200px]">Report ID</th>
                  <th className="text-left px-4 py-2.5 text-xs font-semibold text-muted-foreground uppercase tracking-wide w-[160px]">Created</th>
                  <th className="text-left px-4 py-2.5 text-xs font-semibold text-muted-foreground uppercase tracking-wide">Integrity Hash</th>
                  <th className="text-left px-4 py-2.5 text-xs font-semibold text-muted-foreground uppercase tracking-wide w-[220px]">Downloads</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((r) => (
                  <tr key={r.report_id} className="table-row-cyber border-b border-border/50 last:border-0">
                    {/* Report ID */}
                    <td className="px-4 py-3">
                      <div className="flex flex-col gap-0.5">
                        <span className="font-mono text-xs text-cyan font-semibold">{r.report_id}</span>
                        <span className="font-mono text-[10px] text-muted-foreground truncate max-w-[180px]" title={selectedFile}>
                          {selectedFile}
                        </span>
                      </div>
                    </td>
                    {/* Created */}
                    <td className="px-4 py-3 font-mono text-xs text-muted-foreground whitespace-nowrap">
                      {formatDate(r.created_at)}
                    </td>
                    {/* Integrity */}
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="w-3.5 h-3.5 text-low shrink-0" />
                        <span
                          className="font-mono text-xs text-cyan/70 cursor-default"
                          title={r.hash_sha256}
                        >
                          {r.hash_sha256.slice(0, 16)}…
                        </span>
                        <button
                          onClick={() => void navigator.clipboard.writeText(r.hash_sha256)}
                          title="Copy full hash"
                          className="opacity-40 hover:opacity-100 transition-opacity"
                        >
                          <Copy className="w-3 h-3 text-muted-foreground" />
                        </button>
                      </div>
                    </td>
                    {/* Downloads */}
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => void handleDownloadSingle(r.report_id, "summary.json")}
                          title="Download Summary JSON"
                          className="flex items-center gap-1 px-2 py-1 rounded text-xs border border-border hover:border-cyan/40 hover:text-cyan transition-colors"
                        >
                          <FileJson className="w-3 h-3" />
                          <span>Summary</span>
                        </button>
                        <button
                          onClick={() => void handleDownloadSingle(r.report_id, "anomalies.csv")}
                          title="Download Anomalies CSV"
                          className="flex items-center gap-1 px-2 py-1 rounded text-xs border border-border hover:border-cyan/40 hover:text-cyan transition-colors"
                        >
                          <FileSpreadsheet className="w-3 h-3" />
                          <span>CSV</span>
                        </button>
                        <button
                          onClick={() => void handleDownloadSingle(r.report_id, "ai_analysis.json")}
                          title="Download AI Analysis JSON"
                          className="flex items-center gap-1 px-2 py-1 rounded text-xs border border-border hover:border-cyan/40 hover:text-cyan transition-colors"
                        >
                          <Download className="w-3 h-3" />
                          <span>AI</span>
                        </button>
                        <button
                          onClick={() => void handleDownloadZip(r.report_id)}
                          title="Download full ZIP bundle"
                          className="flex items-center gap-1 px-2 py-1 rounded text-xs border border-cyan/30 text-cyan hover:bg-cyan/10 transition-colors"
                        >
                          <FileArchive className="w-3 h-3" />
                          <span>ZIP</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {!loading && reports.length === 0 && (
                  <tr>
                    <td className="px-4 py-8 text-center" colSpan={4}>
                      <div className="flex flex-col items-center gap-2">
                        <FileArchive className="w-6 h-6 text-muted-foreground/30" />
                        <p className="text-xs text-muted-foreground">
                          No report bundles generated for this dataset.
                        </p>
                        <p className="text-[10px] text-muted-foreground/60">
                          Select a dataset and click Generate to create one.
                        </p>
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </motion.div>
      </div>
    </AppLayout>
  );
}
