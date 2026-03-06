import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Activity, HardDrive, MemoryStick, Play, Square, Wifi } from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import {
  getSystemMonitoringSnapshot,
  getSystemMonitoringStatus,
  startRealtimeMonitor,
  startSystemMonitoring,
  stopRealtimeMonitor,
  stopSystemMonitoring,
  type MonitoringDeviceEvent,
  type MonitoringSample,
} from "@/lib/api-functions";
import { toast } from "sonner";

const fmtRate = (v: number) => `${(v / 1024).toFixed(1)} KB/s`;

interface LiveLogEntry {
  id: string;
  timestamp: string;
  severity: string;
  source: string;
  message: string;
  score: number;
}

export default function Monitor() {
  const [running, setRunning] = useState(false);
  const [samples, setSamples] = useState<MonitoringSample[]>([]);
  const [events, setEvents] = useState<MonitoringDeviceEvent[]>([]);
  const [liveLogs, setLiveLogs] = useState<LiveLogEntry[]>([]);
  const [connecting, setConnecting] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const logStreamRef = useRef<EventSource | null>(null);
  const fallbackTimerRef = useRef<number | null>(null);
  const logRetryRef = useRef<number | null>(null);

  const latest = samples[samples.length - 1];

  const readOnlySamples = useMemo(() => samples.slice(-30).reverse(), [samples]);
  const readOnlyLogs = useMemo(() => liveLogs.slice(-80).reverse(), [liveLogs]);

  const loadSnapshot = async () => {
    const snap = await getSystemMonitoringSnapshot(120);
    setRunning(Boolean(snap.status?.running));
    setSamples(snap.samples ?? []);
    setEvents(snap.device_events ?? []);
  };

  const startPollingFallback = () => {
    if (fallbackTimerRef.current) {
      window.clearInterval(fallbackTimerRef.current);
    }
    fallbackTimerRef.current = window.setInterval(() => {
      void loadSnapshot();
    }, 1000);
  };

  const connectWs = () => {
    try {
      wsRef.current?.close();
      const base = import.meta.env.VITE_API_URL || "http://localhost:8000";
      const wsUrl = base.replace(/^http/, "ws") + "/monitor/ws";
      const ws = new WebSocket(wsUrl);
      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as {
            status?: { running?: boolean };
            samples?: MonitoringSample[];
            device_events?: MonitoringDeviceEvent[];
          };
          setRunning(Boolean(payload.status?.running));
          setSamples(payload.samples ?? []);
          setEvents(payload.device_events ?? []);
        } catch {
          // ignore malformed ws frame
        }
      };
      ws.onerror = () => {
        startPollingFallback();
      };
      ws.onclose = () => {
        startPollingFallback();
      };
      wsRef.current = ws;
    } catch {
      startPollingFallback();
    }
  };

  const connectLogStream = () => {
    try {
      logStreamRef.current?.close();
      if (logRetryRef.current) {
        window.clearTimeout(logRetryRef.current);
      }
      const base = import.meta.env.VITE_API_URL || "http://localhost:8000";
      const streamUrl = `${base}/stream/logs?min_score=0`;
      const stream = new EventSource(streamUrl);
      stream.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as {
            event?: string;
            message?: string;
            file_path?: string;
            raw_line?: string;
            parsed?: { message?: string; source?: string };
            anomaly_score?: number;
            severity?: string;
            received_at?: string;
          };
          if (payload.event === "connected") {
            return;
          }

          const sourceRaw = payload.parsed?.source || payload.file_path || "stream";
          const source =
            sourceRaw.split(/[/\\]/).pop()?.trim() ||
            sourceRaw.trim() ||
            "stream";
          const message =
            payload.parsed?.message?.trim() ||
            payload.raw_line?.trim() ||
            payload.message?.trim() ||
            "";
          if (!message) {
            return;
          }

          setLiveLogs((prev) => {
            const next = [
              ...prev,
              {
                id: `${payload.received_at ?? Date.now()}-${prev.length}`,
                timestamp: payload.received_at ?? new Date().toISOString(),
                severity: String(payload.severity ?? "INFO").toUpperCase(),
                source,
                message,
                score: Number(payload.anomaly_score ?? 0),
              },
            ];
            return next.slice(-200);
          });
        } catch {
          // ignore malformed frames
        }
      };

      stream.onerror = () => {
        stream.close();
        logRetryRef.current = window.setTimeout(() => {
          connectLogStream();
        }, 1500);
      };
      logStreamRef.current = stream;
    } catch {
      logRetryRef.current = window.setTimeout(() => {
        connectLogStream();
      }, 1500);
    }
  };

  useEffect(() => {
    const init = async () => {
      try {
        const status = await getSystemMonitoringStatus();
        setRunning(Boolean(status.running));
      } catch {
        // no-op
      }
      try {
        await loadSnapshot();
      } catch {
        // no-op
      }
      try {
        await startRealtimeMonitor();
      } catch {
        // no-op
      }
      connectWs();
      connectLogStream();
    };

    void init();
    return () => {
      wsRef.current?.close();
      logStreamRef.current?.close();
      if (fallbackTimerRef.current) {
        window.clearInterval(fallbackTimerRef.current);
      }
      if (logRetryRef.current) {
        window.clearTimeout(logRetryRef.current);
      }
    };
  }, []);

  const handleStart = async () => {
    setConnecting(true);
    try {
      await Promise.all([startSystemMonitoring(), startRealtimeMonitor()]);
      setRunning(true);
      toast.success("Monitoring started");
      await loadSnapshot();
    } catch {
      toast.error("Failed to start monitoring");
    } finally {
      setConnecting(false);
    }
  };

  const handleStop = async () => {
    setConnecting(true);
    try {
      await Promise.allSettled([stopSystemMonitoring(), stopRealtimeMonitor()]);
      setRunning(false);
      toast.success("Monitoring stopped");
      await loadSnapshot();
    } catch {
      toast.error("Failed to stop monitoring");
    } finally {
      setConnecting(false);
    }
  };

  return (
    <AppLayout title="Monitoring" subtitle="Persistent runtime system monitor">
      <div className="space-y-5">
        <div className="cyber-card p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span
              className="w-2.5 h-2.5 rounded-full"
              style={{
                background: running ? "hsl(var(--low))" : "hsl(var(--critical))",
                boxShadow: running ? "0 0 10px hsl(var(--low) / 0.7)" : "0 0 10px hsl(var(--critical) / 0.7)",
              }}
            />
            <span className="text-sm font-semibold">
              {running ? "Running" : "Stopped"}
            </span>
          </div>
          <button
            onClick={() => (running ? void handleStop() : void handleStart())}
            disabled={connecting}
            className="px-4 py-2 rounded-md text-sm font-semibold flex items-center gap-2 disabled:opacity-50"
            style={
              running
                ? {
                    background: "hsl(var(--critical) / 0.14)",
                    border: "1px solid hsl(var(--critical) / 0.3)",
                    color: "hsl(var(--critical))",
                  }
                : {
                    background: "hsl(var(--cyan) / 0.14)",
                    border: "1px solid hsl(var(--cyan) / 0.3)",
                    color: "hsl(var(--cyan))",
                  }
            }
          >
            {running ? <Square className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            {running ? "Stop Monitoring" : "Start Monitoring"}
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { icon: Activity, label: "CPU", value: `${(latest?.cpu_percent ?? 0).toFixed(1)}%` },
            { icon: MemoryStick, label: "Memory", value: `${(latest?.memory_percent ?? 0).toFixed(1)}%` },
            { icon: HardDrive, label: "Disk I/O", value: `${fmtRate((latest?.disk_read_bps ?? 0) + (latest?.disk_write_bps ?? 0))}` },
            { icon: Wifi, label: "Network", value: `${fmtRate((latest?.network_recv_bps ?? 0) + (latest?.network_send_bps ?? 0))}` },
          ].map((item) => (
            <motion.div
              key={item.label}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="cyber-card p-4"
            >
              <div className="flex items-center gap-2 text-muted-foreground text-xs uppercase tracking-wide">
                <item.icon className="w-4 h-4 text-cyan" />
                {item.label}
              </div>
              <p className="mt-2 font-mono text-xl text-foreground">{item.value}</p>
            </motion.div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="cyber-card overflow-hidden">
            <div className="px-4 py-3 border-b border-border">
              <h3 className="text-sm font-semibold">Live Samples</h3>
            </div>
            <div className="max-h-[340px] overflow-y-auto">
              <table className="w-full text-xs font-mono">
                <thead>
                  <tr className="border-b border-border">
                    <th className="px-3 py-2 text-left">Time</th>
                    <th className="px-3 py-2 text-left">CPU</th>
                    <th className="px-3 py-2 text-left">Mem</th>
                    <th className="px-3 py-2 text-left">Disk</th>
                    <th className="px-3 py-2 text-left">Net</th>
                  </tr>
                </thead>
                <tbody>
                  {readOnlySamples.map((s) => (
                    <tr key={s.timestamp} className="border-b border-border/40">
                      <td className="px-3 py-2">{new Date(s.timestamp).toLocaleTimeString()}</td>
                      <td className="px-3 py-2">{s.cpu_percent.toFixed(1)}%</td>
                      <td className="px-3 py-2">{s.memory_percent.toFixed(1)}%</td>
                      <td className="px-3 py-2">{fmtRate(s.disk_read_bps + s.disk_write_bps)}</td>
                      <td className="px-3 py-2">{fmtRate(s.network_recv_bps + s.network_send_bps)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="cyber-card overflow-hidden">
            <div className="px-4 py-3 border-b border-border">
              <h3 className="text-sm font-semibold">Device Events</h3>
            </div>
            <div className="max-h-[340px] overflow-y-auto p-3 space-y-2">
              {events.slice(-40).reverse().map((ev, idx) => (
                <div key={`${ev.timestamp}-${idx}`} className="p-2 rounded border border-border/50 bg-muted/30">
                  <p className="text-xs font-mono text-foreground">
                    {ev.event.toUpperCase()} | {ev.device_class}
                  </p>
                  <p className="text-xs text-muted-foreground">{ev.device_name}</p>
                  <p className="text-[11px] text-muted-foreground">{new Date(ev.timestamp).toLocaleString()}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="cyber-card overflow-hidden">
          <div className="px-4 py-3 border-b border-border">
            <h3 className="text-sm font-semibold">Live Logs</h3>
          </div>
          <div className="max-h-[280px] overflow-y-auto p-3">
            <div className="space-y-1 font-mono text-xs">
              {readOnlyLogs.length === 0 && (
                <p className="text-muted-foreground">Waiting for realtime log events...</p>
              )}
              {readOnlyLogs.map((log) => (
                <div key={log.id} className="text-foreground break-all leading-relaxed">
                  <span className="text-cyan">{new Date(log.timestamp).toLocaleTimeString()}</span>{" "}
                  <span
                    className={
                      log.severity === "CRITICAL"
                        ? "text-cyber-critical"
                        : log.severity === "HIGH"
                          ? "text-cyber-high"
                          : log.severity === "MEDIUM"
                            ? "text-yellow-400"
                            : "text-cyber-low"
                    }
                  >
                    [{log.severity}]
                  </span>{" "}
                  <span className="text-muted-foreground">{log.source}</span>{" "}
                  <span>{log.message}</span>{" "}
                  <span className="text-muted-foreground">({log.score.toFixed(2)})</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
