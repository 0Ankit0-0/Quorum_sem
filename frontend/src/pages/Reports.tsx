import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Download, FileArchive, FileJson, FileSpreadsheet, RefreshCw } from "lucide-react";
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

  const loadFiles = async () => {
    const data = await getUploadedFiles();
    setFiles(data.files ?? []);
    if (!selectedFile && data.files.length > 0) {
      setSelectedFile(data.files[0].filename);
    }
  };

  const loadReports = async (filename: string) => {
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
  };

  useEffect(() => {
    void loadFiles();
  }, []);

  useEffect(() => {
    if (!selectedFile) return;
    void loadReports(selectedFile);
  }, [selectedFile]);

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
      <div className="space-y-6">
        <div className="cyber-card p-5 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
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
            <div className="flex gap-2">
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
                className="px-3 py-2 rounded-md text-xs font-semibold disabled:opacity-60"
                style={{ background: "hsl(var(--cyan))", color: "hsl(var(--background))" }}
              >
                {generating ? "Generating..." : "Generate"}
              </button>
            </div>
          </div>

          <div className="text-xs font-mono text-muted-foreground flex gap-5 flex-wrap">
            <span>Uploaded: {selectedMeta ? formatDate(selectedMeta.uploaded_at) : "-"}</span>
            <span>Records: {(selectedMeta?.record_count ?? 0).toLocaleString()}</span>
            <span>DB: {selectedMeta?.dataset_id ?? "N/A"}</span>
          </div>
        </div>

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="cyber-card overflow-hidden">
          <div className="px-5 py-4 border-b border-border">
            <h3 className="text-sm font-semibold">Generated Reports</h3>
            <p className="text-xs text-muted-foreground">
              {loading ? "Loading..." : `${reports.length} report bundle(s) for selected dataset`}
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  {["Dataset (report_id)", "Created", "Integrity", "Actions"].map((h) => (
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
                {reports.map((r) => (
                  <tr key={r.report_id} className="table-row-cyber border-b border-border/50 last:border-0">
                    <td className="px-4 py-3 font-mono text-xs text-foreground">
                      {selectedFile} ({r.report_id})
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                      {formatDate(r.created_at)}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-cyan">{r.hash_sha256}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2 flex-wrap">
                        <button
                          onClick={() => void handleDownloadSingle(r.report_id, "summary.json")}
                          className="text-xs flex items-center gap-1.5 px-2 py-1 rounded border border-border hover:border-cyan/40"
                        >
                          <FileJson className="w-3.5 h-3.5" />
                          Summary
                        </button>
                        <button
                          onClick={() => void handleDownloadSingle(r.report_id, "anomalies.csv")}
                          className="text-xs flex items-center gap-1.5 px-2 py-1 rounded border border-border hover:border-cyan/40"
                        >
                          <FileSpreadsheet className="w-3.5 h-3.5" />
                          Anomalies
                        </button>
                        <button
                          onClick={() => void handleDownloadSingle(r.report_id, "ai_analysis.json")}
                          className="text-xs flex items-center gap-1.5 px-2 py-1 rounded border border-border hover:border-cyan/40"
                        >
                          <Download className="w-3.5 h-3.5" />
                          AI
                        </button>
                        <button
                          onClick={() => void handleDownloadZip(r.report_id)}
                          className="text-xs flex items-center gap-1.5 px-2 py-1 rounded border border-cyan/40 text-cyan"
                        >
                          <FileArchive className="w-3.5 h-3.5" />
                          ZIP
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {!loading && reports.length === 0 && (
                  <tr>
                    <td className="px-4 py-4 text-xs text-muted-foreground" colSpan={4}>
                      No report bundles generated for this dataset.
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
