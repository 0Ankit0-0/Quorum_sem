import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { CheckCircle, RefreshCw, Upload } from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import { formatDate } from "@/lib/formatters";
import {
  getLogs,
  getUploadedFiles,
  type LogData,
  type UploadedFile,
  uploadLogFile,
} from "@/lib/api-functions";
import { toast } from "sonner";

const fmtBytes = (bytes: number) => {
  if (bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let size = bytes;
  let idx = 0;
  while (size >= 1024 && idx < units.length - 1) {
    size /= 1024;
    idx += 1;
  }
  return `${size.toFixed(size >= 10 || idx === 0 ? 0 : 1)} ${units[idx]}`;
};

export default function Logs() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadResult, setUploadResult] = useState<null | {
    entries: number;
    errors: number;
    duration: number;
  }>(null);

  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<string>("");
  const [logs, setLogs] = useState<LogData[]>([]);
  const [query, setQuery] = useState("");
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [loading, setLoading] = useState(false);

  const selectedFileMeta = useMemo(
    () => files.find((f) => f.filename === selectedFile) ?? null,
    [files, selectedFile],
  );

  const loadFiles = async () => {
    const result = await getUploadedFiles();
    setFiles(result.files ?? []);
    if (!selectedFile && result.files.length > 0) {
      setSelectedFile(result.files[0].filename);
    }
  };

  const loadLogs = async () => {
    if (!selectedFile) {
      setLogs([]);
      return;
    }
    setLoading(true);
    try {
      const rows = await getLogs(200, selectedFile, query.trim() || undefined);
      setLogs(rows);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadFiles();
  }, []);

  useEffect(() => {
    void loadLogs();
  }, [selectedFile, query]);

  useEffect(() => {
    if (!autoRefresh || !selectedFile) return;
    const timer = window.setInterval(() => {
      void loadLogs();
    }, 4000);
    return () => window.clearInterval(timer);
  }, [autoRefresh, selectedFile, query]);

  const ingestFile = async (file: File) => {
    setUploading(true);
    setUploadProgress(0);
    setUploadResult(null);
    try {
      const result = await uploadLogFile(file, undefined, setUploadProgress);
      setUploadResult({
        entries: result.entries_inserted,
        errors: result.parse_errors + result.insert_errors,
        duration: result.duration_seconds,
      });
      await loadFiles();
      setSelectedFile(file.name);
      await loadLogs();
      toast.success(`Ingested ${result.entries_inserted.toLocaleString()} records`);
    } catch (error) {
      console.error("Log upload failed", error);
      toast.error("Failed to upload and ingest logs");
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (!file) return;
    await ingestFile(file);
  };

  const handleFilePick = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    await ingestFile(file);
    e.target.value = "";
  };

  return (
    <AppLayout title="Log Management" subtitle="Dataset-isolated log ingestion and viewer">
      <div className="space-y-6">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className={`relative rounded-lg border-2 border-dashed transition-all duration-200 p-10 text-center cursor-pointer ${
            dragOver ? "border-cyan bg-cyan/5" : "border-border hover:border-muted-foreground"
          }`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
        >
          <input
            ref={inputRef}
            type="file"
            className="hidden"
            onChange={handleFilePick}
            accept=".evtx,.log,.syslog,.csv,.txt,.json,.jsonl,.ndjson"
          />

          <Upload className="w-9 h-9 text-muted-foreground mx-auto mb-3" />
          <p className="text-base font-medium text-foreground mb-1">Drop a log file or click to upload</p>
          <p className="text-sm text-muted-foreground">Viewer is read-only. Uploads create isolated per-file database.</p>

          {uploading && (
            <div className="mt-5">
              <div className="flex justify-between text-xs font-mono text-muted-foreground mb-1">
                <span>Uploading and ingesting...</span>
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

        {uploadResult && (
          <div className="cyber-card p-4 flex items-center gap-6" style={{ borderColor: "hsl(var(--low) / 0.4)" }}>
            <CheckCircle className="w-6 h-6 text-cyber-low shrink-0" />
            <div className="flex gap-6 text-sm">
              <div>
                <p className="text-muted-foreground text-xs">Entries Inserted</p>
                <p className="font-mono font-semibold text-foreground">{uploadResult.entries.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">Errors</p>
                <p className="font-mono font-semibold text-cyber-critical">{uploadResult.errors}</p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">Duration</p>
                <p className="font-mono font-semibold text-cyan">{uploadResult.duration}s</p>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="cyber-card p-4 space-y-3">
            <p className="text-sm font-semibold">Dataset Selection</p>
            <select
              value={selectedFile}
              onChange={(e) => setSelectedFile(e.target.value)}
              className="w-full bg-muted border border-border rounded-md px-3 py-2 text-sm text-foreground font-mono outline-none focus:border-cyan/40"
            >
              {files.length === 0 && <option value="">No uploads found</option>}
              {files.map((f) => (
                <option key={f.filename} value={f.filename}>
                  {f.filename}
                </option>
              ))}
            </select>

            <div className="space-y-1 text-xs font-mono">
              <p className="text-muted-foreground">Size: <span className="text-foreground">{fmtBytes(selectedFileMeta?.size_bytes ?? 0)}</span></p>
              <p className="text-muted-foreground">Uploaded: <span className="text-foreground">{selectedFileMeta ? formatDate(selectedFileMeta.uploaded_at) : "-"}</span></p>
              <p className="text-muted-foreground">Records: <span className="text-foreground">{(selectedFileMeta?.record_count ?? 0).toLocaleString()}</span></p>
              <p className="text-muted-foreground">DB: <span className="text-foreground break-all">{selectedFileMeta?.db_path ?? "Not created"}</span></p>
            </div>
          </div>

          <div className="cyber-card p-4 lg:col-span-2">
            <div className="flex items-center justify-between gap-3 mb-3">
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search in selected dataset logs..."
                className="flex-1 text-xs bg-muted border border-border rounded-md px-3 py-2 text-foreground placeholder:text-muted-foreground font-mono outline-none focus:border-cyan/50"
              />
              <button
                onClick={() => void loadLogs()}
                className="px-3 py-2 rounded-md text-xs font-semibold flex items-center gap-1.5 border border-border hover:border-cyan/40"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Refresh
              </button>
              <label className="text-xs font-mono text-muted-foreground flex items-center gap-1.5">
                <input
                  type="checkbox"
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                />
                Auto refresh
              </label>
            </div>
            <p className="text-[11px] text-muted-foreground mb-2">Read-only terminal viewer ({logs.length} rows)</p>
            <div className="rounded-md border border-border bg-black/60 max-h-[420px] overflow-y-auto p-3">
              <div className="space-y-1 font-mono text-xs">
                {loading && <p className="text-cyan">Loading...</p>}
                {!loading && logs.length === 0 && <p className="text-muted-foreground">No logs for selected dataset.</p>}
                {logs.map((log) => (
                  <div key={log.id} className="text-foreground break-all leading-relaxed">
                    <span className="text-cyan">{new Date(log.timestamp).toLocaleTimeString()}</span>{" "}
                    <span className="text-cyber-high">[{log.severity}]</span>{" "}
                    <span className="text-muted-foreground">{log.source}</span>{" "}
                    <span>{log.message}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
