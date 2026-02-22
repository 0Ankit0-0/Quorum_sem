import { useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Play, Square, ChevronDown } from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import { useQuorumData } from "@/hooks/useQuorumData";
import {
  type SeverityLevel,
  type StreamLogData,
  startRealtimeMonitor,
  stopRealtimeMonitor,
} from "@/lib/api-functions";
import { toast } from "sonner";

const severityColor: Record<string, string> = {
  CRITICAL: "hsl(var(--critical))",
  HIGH: "hsl(var(--high))",
  MEDIUM: "hsl(var(--medium))",
  LOW: "hsl(var(--low))",
};

const severityBg: Record<string, string> = {
  CRITICAL: "hsl(var(--critical) / 0.08)",
  HIGH: "hsl(var(--high) / 0.06)",
  MEDIUM: "hsl(var(--medium) / 0.04)",
  LOW: "",
};

const normalizeSeverity = (value: unknown): SeverityLevel => {
  const sev = String(value ?? "").toUpperCase();
  if (sev === "CRITICAL") return "CRITICAL";
  if (sev === "HIGH") return "HIGH";
  if (sev === "MEDIUM") return "MEDIUM";
  return "LOW";
};

const formatTime = (iso?: string) => {
  const d = iso ? new Date(iso) : new Date();
  return d.toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    fractionalSecondDigits: 3,
  });
};

export default function Monitor() {
  const { streamLogs } = useQuorumData();
  const [streaming, setStreaming] = useState(false);
  const [logs, setLogs] = useState<StreamLogData[]>(streamLogs);
  const [filter, setFilter] = useState("ALL");
  const [autoScroll, setAutoScroll] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const consoleRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!streaming && streamLogs.length > 0) {
      setLogs(streamLogs);
    }
  }, [streamLogs, streaming]);

  useEffect(() => {
    if (autoScroll && consoleRef.current) {
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  useEffect(() => {
    return () => {
      eventSourceRef.current?.close();
      eventSourceRef.current = null;
    };
  }, []);

  const start = async () => {
    setConnecting(true);
    try {
      await startRealtimeMonitor();
      const base = import.meta.env.VITE_API_URL || "http://localhost:8000";
      const es = new EventSource(`${base}/stream/logs`);

      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as {
            event?: string;
            message?: string;
            parsed?: Record<string, unknown>;
            anomaly_score?: number;
            severity?: string;
            received_at?: string;
            raw_line?: string;
          };

          if (data.event === "connected") {
            return;
          }

          const next: StreamLogData = {
            id: Date.now(),
            time: formatTime(data.received_at),
            severity: normalizeSeverity(data.severity),
            score: Number(data.anomaly_score ?? 0.4),
            source: String(
              data.parsed?.source ?? data.parsed?.source_file ?? "STREAM",
            ).toUpperCase(),
            message: String(data.parsed?.message ?? data.raw_line ?? ""),
          };

          setLogs((prev) => [...prev.slice(-199), next]);
        } catch {
          // Ignore malformed stream messages
        }
      };

      es.onerror = () => {
        toast.error("Stream disconnected");
        setStreaming(false);
        es.close();
        eventSourceRef.current = null;
      };

      eventSourceRef.current = es;
      setStreaming(true);
      toast.success("Live stream started");
    } catch (error) {
      console.error("Failed to start stream", error);
      toast.error("Failed to start stream");
    } finally {
      setConnecting(false);
    }
  };

  const stop = async () => {
    try {
      eventSourceRef.current?.close();
      eventSourceRef.current = null;
      await stopRealtimeMonitor();
      setStreaming(false);
      toast.success("Live stream stopped");
    } catch (error) {
      console.error("Failed to stop stream", error);
      toast.error("Failed to stop stream");
    }
  };

  const filtered = useMemo(
    () => (filter === "ALL" ? logs : logs.filter((l) => l.severity === filter)),
    [filter, logs],
  );

  return (
    <AppLayout title="Real-Time Monitor" subtitle="Live log stream with AI scoring">
      <div className="space-y-4">
        <div className="cyber-card p-4 flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <button
              onClick={() => (streaming ? void stop() : void start())}
              disabled={connecting}
              className="flex items-center gap-2 px-4 py-2 rounded-md text-sm font-semibold transition-all duration-200 disabled:opacity-50"
              style={
                streaming
                  ? {
                      background: "hsl(var(--critical) / 0.15)",
                      color: "hsl(var(--critical))",
                      border: "1px solid hsl(var(--critical) / 0.3)",
                    }
                  : {
                      background: "hsl(var(--cyan) / 0.15)",
                      color: "hsl(var(--cyan))",
                      border: "1px solid hsl(var(--cyan) / 0.3)",
                    }
              }
            >
              {streaming ? (
                <>
                  <Square className="w-3.5 h-3.5" />Stop Stream
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5" />
                  {connecting ? "Connecting..." : "Start Stream"}
                </>
              )}
            </button>

            {streaming && (
              <div className="flex items-center gap-2 text-xs font-mono text-cyber-low">
                <div className="w-2 h-2 rounded-full bg-cyber-low animate-pulse" />
                LIVE
              </div>
            )}
          </div>

          <div className="flex items-center gap-2 ml-auto">
            <span className="text-xs text-muted-foreground">Filter:</span>
            {["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className="px-2.5 py-1 rounded text-xs font-mono font-semibold transition-colors"
                style={
                  filter === f
                    ? {
                        background: "hsl(var(--cyan) / 0.15)",
                        color: "hsl(var(--cyan))",
                        border: "1px solid hsl(var(--cyan) / 0.3)",
                      }
                    : {
                        color: "hsl(var(--muted-foreground))",
                        border: "1px solid transparent",
                      }
                }
              >
                {f}
              </button>
            ))}
          </div>

          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <ChevronDown className="w-3.5 h-3.5" />
            {autoScroll ? "Auto-scroll ON" : "Auto-scroll OFF"}
          </button>
        </div>

        <div className="terminal" style={{ height: "calc(100vh - 280px)" }}>
          <div
            className="flex items-center gap-2 px-4 py-2.5 border-b border-border/30"
            style={{ background: "hsl(0 0% 6%)" }}
          >
            <div className="w-2.5 h-2.5 rounded-full bg-cyber-critical" />
            <div className="w-2.5 h-2.5 rounded-full bg-cyber-medium" />
            <div className="w-2.5 h-2.5 rounded-full bg-cyber-low" />
            <span className="ml-2 text-xs text-muted-foreground font-mono">
              quorum://stream/logs - {filtered.length} events
            </span>
          </div>

          <div ref={consoleRef} className="overflow-y-auto h-full p-3 space-y-0.5">
            <AnimatePresence initial={false}>
              {filtered.map((log) => (
                <motion.div
                  key={log.id}
                  initial={{ opacity: 0, x: -4 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="flex items-start gap-3 px-2 py-1 rounded text-xs font-mono group"
                  style={{ background: severityBg[log.severity] || "transparent" }}
                >
                  <span className="text-muted-foreground shrink-0 select-none">
                    {log.time}
                  </span>
                  <span
                    className="shrink-0 w-16 text-center rounded px-1"
                    style={{
                      color: severityColor[log.severity],
                      background: `${severityColor[log.severity]}20`,
                    }}
                  >
                    {log.severity}
                  </span>
                  <span className="shrink-0 w-20 text-cyan truncate">{log.source}</span>
                  <span
                    className="shrink-0 w-12 text-right"
                    style={{
                      color:
                        log.score > 0.9
                          ? "hsl(var(--critical))"
                          : log.score > 0.75
                            ? "hsl(var(--high))"
                            : log.score > 0.55
                              ? "hsl(var(--medium))"
                              : "hsl(var(--low))",
                    }}
                  >
                    {log.score.toFixed(2)}
                  </span>
                  <span className="text-foreground/80 flex-1">{log.message}</span>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
