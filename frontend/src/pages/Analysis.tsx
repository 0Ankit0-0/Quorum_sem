import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  Play,
  FlaskConical,
  CheckCircle,
  Database,
  FileText,
} from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import { formatTimeAgo, formatNumber } from "@/lib/formatters";
import {
  getUploadedFiles,
  runAnalysis,
  type UploadedFile,
} from "@/lib/api-functions";
import { useQuorumData } from "@/hooks/useQuorumData";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  SelectSeparator,
  SelectLabel,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { toast } from "sonner";
import MitreHeatmap from "@/components/analysis/MitreHeatmap";

const algorithms = [
  {
    id: "ensemble",
    label: "Ensemble (Recommended)",
    desc: "4-component weighted hybrid - best accuracy",
  },
  {
    id: "isolation_forest",
    label: "Isolation Forest",
    desc: "Outlier-based anomaly detection",
  },
  {
    id: "one_class_svm",
    label: "One-Class SVM",
    desc: "Boundary-based classification",
  },
  {
    id: "statistical",
    label: "Statistical Z-Score",
    desc: "Distribution-based anomaly detection",
  },
];

const getThresholdLabel = (value: number) => {
  if (value < 0.3) return "Very Sensitive";
  if (value < 0.5) return "Sensitive";
  if (value < 0.7) return "Balanced";
  if (value < 0.85) return "Strict";
  return "Very Strict";
};

const getThresholdColor = (value: number) => {
  if (value < 0.5) return "text-high";
  if (value < 0.7) return "text-medium";
  return "text-low";
};

export default function Analysis() {
  const { sessions, refresh } = useQuorumData();
  const [selectedAlgo, setSelectedAlgo] = useState("ensemble");
  const [threshold, setThreshold] = useState([0.65]);
  const [logSource, setLogSource] = useState("latest");
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [running, setRunning] = useState(false);
  const [loadingFiles, setLoadingFiles] = useState(true);

  useEffect(() => {
    const fetchFiles = async () => {
      try {
        const data = await getUploadedFiles();
        setUploadedFiles(data.files);
      } catch (error) {
        console.error("Failed to fetch uploaded files:", error);
        toast.error("Failed to load uploaded files");
      } finally {
        setLoadingFiles(false);
      }
    };

    void fetchFiles();
  }, []);

  const handleRun = async () => {
    setRunning(true);
    try {
      const payload = {
        algorithm: selectedAlgo,
        threshold: threshold[0],
        log_source: logSource,
      };
      const result = await runAnalysis(payload);
      await refresh();
      toast.success(
        `Analysis complete: ${formatNumber(result.anomalies_detected ?? 0)} anomalies`,
      );
    } catch (error) {
      console.error("Analysis failed", error);
      toast.error("Analysis failed");
    } finally {
      setRunning(false);
    }
  };

  const canRun = useMemo(() => {
    if (running) return false;
    if (logSource === "all") return true;
    if (logSource === "latest") return uploadedFiles.length > 0;
    return uploadedFiles.some((file) => file.filename === logSource);
  }, [logSource, running, uploadedFiles]);

  const getLogSourceDisplay = () => {
    if (logSource === "all") return `All files (${uploadedFiles.length})`;
    if (logSource === "latest") {
      return uploadedFiles.length > 0
        ? `Latest: ${uploadedFiles[0]?.filename}`
        : "Latest";
    }
    const file = uploadedFiles.find((f) => f.filename === logSource);
    return file ? file.filename : logSource;
  };

  return (
    <AppLayout
      title="Analysis Engine"
      subtitle="Run AI anomaly detection on ingested logs"
    >
      <div className="space-y-6">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="cyber-card p-6"
        >
          <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
            <FlaskConical className="w-4 h-4 text-cyan" /> Analysis
            Configuration
          </h3>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-xs text-muted-foreground uppercase tracking-wide">
                Algorithm
              </label>
              <div className="space-y-2">
                {algorithms.map((a) => (
                  <button
                    key={a.id}
                    onClick={() => setSelectedAlgo(a.id)}
                    className="w-full text-left p-3 rounded-md border transition-all"
                    style={
                      selectedAlgo === a.id
                        ? {
                            background: "hsl(var(--cyan) / 0.08)",
                            borderColor: "hsl(var(--cyan) / 0.4)",
                          }
                        : {
                            background: "hsl(var(--muted))",
                            borderColor: "hsl(var(--border))",
                          }
                    }
                  >
                    <div className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-full border-2 flex items-center justify-center"
                        style={{
                          borderColor:
                            selectedAlgo === a.id
                              ? "hsl(var(--cyan))"
                              : "hsl(var(--muted-foreground))",
                        }}
                      >
                        {selectedAlgo === a.id && (
                          <div className="w-1.5 h-1.5 rounded-full bg-cyber-cyan" />
                        )}
                      </div>
                      <span className="text-sm font-medium text-foreground">
                        {a.label}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground ml-5 mt-0.5">
                      {a.desc}
                    </p>
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-6">
              <div>
                <label className="text-xs text-muted-foreground uppercase tracking-wide block mb-2">
                  Log Source
                </label>
                <Select
                  value={logSource}
                  onValueChange={setLogSource}
                  disabled={loadingFiles}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue>
                      <div className="flex items-center gap-2">
                        <Database className="w-4 h-4 text-cyan" />
                        <span>{getLogSourceDisplay()}</span>
                      </div>
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">
                      <div className="flex items-center gap-2">
                        <Database className="w-4 h-4" />
                        <span>All Files ({uploadedFiles.length})</span>
                      </div>
                    </SelectItem>
                    <SelectItem value="latest">
                      <div className="flex items-center gap-2">
                        <FileText className="w-4 h-4" />
                        <span>Latest File</span>
                      </div>
                    </SelectItem>
                    {uploadedFiles.length > 0 && (
                      <>
                        <SelectSeparator />
                        <SelectLabel>Specific Files</SelectLabel>
                        {uploadedFiles.map((file) => (
                          <SelectItem key={file.filename} value={file.filename}>
                            <div className="flex flex-col gap-0.5">
                              <span className="text-sm font-medium">
                                {file.filename}
                              </span>
                              <span className="text-xs text-muted-foreground">
                                {(file.size_bytes / 1024 / 1024).toFixed(2)} MB -{" "}
                                {new Date(file.uploaded_at).toLocaleDateString()}
                              </span>
                            </div>
                          </SelectItem>
                        ))}
                      </>
                    )}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <div className="flex justify-between items-center mb-3">
                  <label className="text-xs text-muted-foreground uppercase tracking-wide">
                    Detection Sensitivity
                  </label>
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-xs font-semibold ${getThresholdColor(threshold[0])}`}
                    >
                      {getThresholdLabel(threshold[0])}
                    </span>
                    <span className="font-mono text-sm text-cyan">
                      {threshold[0].toFixed(2)}
                    </span>
                  </div>
                </div>
                <Slider
                  min={0}
                  max={1}
                  step={0.01}
                  value={threshold}
                  onValueChange={setThreshold}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-muted-foreground mt-2">
                  <span>0.00 (More Alerts)</span>
                  <span>1.00 (Fewer Alerts)</span>
                </div>
              </div>

              <button
                onClick={handleRun}
                disabled={!canRun}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-md text-sm font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                style={{
                  background: running ? "hsl(var(--muted))" : "hsl(var(--cyan))",
                  color: running
                    ? "hsl(var(--muted-foreground))"
                    : "hsl(var(--background))",
                }}
              >
                <Play className="w-4 h-4" />
                {running ? "Analyzing..." : "Run Analysis"}
              </button>
            </div>
          </div>
        </motion.div>

        <MitreHeatmap />

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="cyber-card overflow-hidden"
        >
          <div className="px-5 py-4 border-b border-border">
            <h3 className="text-sm font-semibold">Analysis Sessions</h3>
            <p className="text-xs text-muted-foreground">
              {sessions.length} sessions completed
            </p>
          </div>
          <div className="p-4 grid gap-3">
            {sessions.map((s, i) => (
              <motion.div
                key={s.id}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className="flex items-center gap-4 p-4 rounded-md border border-border/60 hover:border-cyan/30 transition-colors cursor-pointer"
                style={{ background: "hsl(var(--muted))" }}
              >
                <CheckCircle className="w-5 h-5 text-cyber-low shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-sm text-cyan">{s.id}</span>
                    <span className="text-xs font-mono text-muted-foreground">
                      {s.algorithm}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <span>{formatNumber(s.total_logs)} logs</span>
                    <span className="text-cyber-critical font-semibold">
                      {s.anomalies_found} anomalies
                    </span>
                    <span>{s.duration_seconds}s</span>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-xs text-muted-foreground">
                    {formatTimeAgo(s.created_at)}
                  </p>
                  <p className="text-xs font-mono text-foreground">
                    threshold: {s.threshold.toFixed(2)}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </AppLayout>
  );
}

