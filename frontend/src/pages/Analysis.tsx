import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Play, FlaskConical, CheckCircle, Database, FileText } from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import { mockSessions, formatDate, formatTimeAgo, formatNumber } from "@/lib/mockData";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue, SelectSeparator, SelectLabel } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { getUploadedFiles, type UploadedFile } from "@/lib/api-functions";
import { toast } from "sonner";

const algorithms = [
  { id: "ensemble", label: "Ensemble (Recommended)", desc: "4-component weighted hybrid — best accuracy" },
  { id: "isolation_forest", label: "Isolation Forest", desc: "Outlier-based anomaly detection" },
  { id: "one_class_svm", label: "One-Class SVM", desc: "Boundary-based classification" },
  { id: "statistical", label: "Statistical Z-Score", desc: "Distribution-based anomaly detection" },
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
  const [selectedAlgo, setSelectedAlgo] = useState("ensemble");
  const [threshold, setThreshold] = useState([0.65]);
  const [logSource, setLogSource] = useState("latest");
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [sessions, setSessions] = useState(mockSessions);
  const [loadingFiles, setLoadingFiles] = useState(true);

  useEffect(() => {
    // Fetch uploaded files on component mount
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

    fetchFiles();
  }, []);

  const handleRun = () => {
    setRunning(true);
    setProgress(0);
    const iv = setInterval(() => {
      setProgress(p => {
        if (p >= 100) {
          clearInterval(iv);
          setRunning(false);
          
          // Determine log count based on source
          let logCount = 47_284;
          if (logSource === "all") {
            logCount = uploadedFiles.reduce((sum) => sum + Math.floor(Math.random() * 50000 + 10000), 0);
          } else if (logSource !== "latest") {
            logCount = Math.floor(Math.random() * 100000 + 20000);
          }
          
          setSessions(prev => [{
            id: `SES-2024-00${prev.length + 1}`,
            algorithm: selectedAlgo,
            threshold: threshold[0],
            total_logs: logCount,
            anomalies_found: Math.floor(Math.random() * 200 + 50),
            duration_seconds: +(Math.random() * 8 + 6).toFixed(1),
            created_at: new Date().toISOString(),
            status: "COMPLETED",
          }, ...prev]);
          
          toast.success("Analysis completed successfully");
          return 100;
        }
        return p + Math.random() * 12;
      });
    }, 200);
  };

  const getLogSourceDisplay = () => {
    if (logSource === "all") return `All files (${uploadedFiles.length})`;
    if (logSource === "latest") return uploadedFiles.length > 0 ? `Latest: ${uploadedFiles[0]?.filename}` : "Latest";
    const file = uploadedFiles.find(f => f.filename === logSource);
    return file ? file.filename : logSource;
  };

  return (
    <AppLayout title="Analysis Engine" subtitle="Run AI anomaly detection on ingested logs">
      <div className="space-y-6">
        {/* Config Form */}
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="cyber-card p-6">
          <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
            <FlaskConical className="w-4 h-4 text-cyan" /> Analysis Configuration
          </h3>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Algorithm Selection */}
            <div className="space-y-2">
              <label className="text-xs text-muted-foreground uppercase tracking-wide">Algorithm</label>
              <div className="space-y-2">
                {algorithms.map(a => (
                  <button
                    key={a.id}
                    onClick={() => setSelectedAlgo(a.id)}
                    className="w-full text-left p-3 rounded-md border transition-all"
                    style={
                      selectedAlgo === a.id
                        ? { background: "hsl(var(--cyan) / 0.08)", borderColor: "hsl(var(--cyan) / 0.4)" }
                        : { background: "hsl(var(--muted))", borderColor: "hsl(var(--border))" }
                    }
                  >
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full border-2 flex items-center justify-center" style={{ borderColor: selectedAlgo === a.id ? "hsl(var(--cyan))" : "hsl(var(--muted-foreground))" }}>
                        {selectedAlgo === a.id && <div className="w-1.5 h-1.5 rounded-full bg-cyber-cyan" />}
                      </div>
                      <span className="text-sm font-medium text-foreground">{a.label}</span>
                    </div>
                    <p className="text-xs text-muted-foreground ml-5 mt-0.5">{a.desc}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Log Source, Threshold + Run */}
            <div className="space-y-6">
              {/* Log Source Selector */}
              <div>
                <label className="text-xs text-muted-foreground uppercase tracking-wide block mb-2">
                  Log Source
                </label>
                <Select value={logSource} onValueChange={setLogSource} disabled={loadingFiles}>
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
                        {uploadedFiles.map(file => (
                          <SelectItem key={file.filename} value={file.filename}>
                            <div className="flex flex-col gap-0.5">
                              <span className="text-sm font-medium">{file.filename}</span>
                              <span className="text-xs text-muted-foreground">
                                {(file.size_bytes / 1024 / 1024).toFixed(2)} MB • {new Date(file.uploaded_at).toLocaleDateString()}
                              </span>
                            </div>
                          </SelectItem>
                        ))}
                      </>
                    )}
                    {uploadedFiles.length === 0 && (
                      <>
                        <SelectSeparator />
                        <div className="px-2 py-3 text-xs text-center text-muted-foreground">
                          No uploaded files found. Upload logs first.
                        </div>
                      </>
                    )}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground mt-1.5">
                  {logSource === "all" && "Process all uploaded log files"}
                  {logSource === "latest" && "Analyze the most recently uploaded file"}
                  {logSource !== "all" && logSource !== "latest" && "Analyze selected file only"}
                </p>
              </div>

              {/* Threshold Slider */}
              <div>
                <div className="flex justify-between items-center mb-3">
                  <label className="text-xs text-muted-foreground uppercase tracking-wide">Detection Sensitivity</label>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-semibold ${getThresholdColor(threshold[0])}`}>
                      {getThresholdLabel(threshold[0])}
                    </span>
                    <span className="font-mono text-sm text-cyan">{threshold[0].toFixed(2)}</span>
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

              <div className="p-4 rounded-md" style={{ background: "hsl(var(--muted))" }}>
                <div className="space-y-2 text-xs font-mono">
                  <div className="flex justify-between"><span className="text-muted-foreground">Algorithm</span><span className="text-foreground">{selectedAlgo}</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">Threshold</span><span className="text-cyan">{threshold[0].toFixed(2)}</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">Log Source</span><span className="text-foreground truncate ml-2">{logSource === "all" ? "All files" : logSource === "latest" ? "Latest" : logSource}</span></div>
                </div>
              </div>

              {running && (
                <div>
                  <div className="flex justify-between text-xs font-mono mb-1 text-muted-foreground">
                    <span>Analyzing logs...</span><span>{Math.round(progress)}%</span>
                  </div>
                  <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                    <motion.div className="h-full rounded-full bg-cyan-400" animate={{ width: `${progress}%` }} transition={{ duration: 0.1 }} style={{ background: "hsl(var(--cyan))" }} />
                  </div>
                </div>
              )}

              <button
                onClick={handleRun}
                disabled={running || (uploadedFiles.length === 0 && logSource !== "all")}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-md text-sm font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                style={{ background: running ? "hsl(var(--muted))" : "hsl(var(--cyan))", color: running ? "hsl(var(--muted-foreground))" : "hsl(var(--background))" }}
              >
                <Play className="w-4 h-4" />
                {running ? "Analyzing..." : "Run Analysis"}
              </button>
            </div>
          </div>
        </motion.div>

        {/* Sessions List */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }} className="cyber-card overflow-hidden">
          <div className="px-5 py-4 border-b border-border">
            <h3 className="text-sm font-semibold">Analysis Sessions</h3>
            <p className="text-xs text-muted-foreground">{sessions.length} sessions completed</p>
          </div>
          <div className="p-4 grid gap-3">
            {sessions.map((s, i) => (
              <motion.div key={s.id} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
                className="flex items-center gap-4 p-4 rounded-md border border-border/60 hover:border-cyan/30 transition-colors cursor-pointer"
                style={{ background: "hsl(var(--muted))" }}
              >
                <CheckCircle className="w-5 h-5 text-cyber-low shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-sm text-cyan">{s.id}</span>
                    <span className="text-xs font-mono text-muted-foreground">{s.algorithm}</span>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <span>{formatNumber(s.total_logs)} logs</span>
                    <span className="text-cyber-critical font-semibold">{s.anomalies_found} anomalies</span>
                    <span>{s.duration_seconds}s</span>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-xs text-muted-foreground">{formatTimeAgo(s.created_at)}</p>
                  <p className="text-xs font-mono text-foreground">threshold: {s.threshold.toFixed(2)}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </AppLayout>
  );
}
