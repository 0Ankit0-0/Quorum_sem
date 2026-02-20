import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Play, Square, ChevronDown } from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import { mockStreamLogs } from "@/lib/mockData";

type LogLine = typeof mockStreamLogs[0];

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

export default function Monitor() {
  const [streaming, setStreaming] = useState(false);
  const [logs, setLogs] = useState<LogLine[]>(mockStreamLogs);
  const [filter, setFilter] = useState("ALL");
  const [autoScroll, setAutoScroll] = useState(true);
  const consoleRef = useRef<HTMLDivElement>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval>>();

  const addRandomLog = () => {
    const templates = [
      { severity: "CRITICAL", score: 0.97, source: "WKST-14", message: "4625 - Failed logon attempt [SYSTEM]" },
      { severity: "HIGH", score: 0.83, source: "SRV-02", message: "4688 - New process: cmd.exe via winlogon" },
      { severity: "MEDIUM", score: 0.67, source: "WKST-07", message: "4672 - Special privileges assigned" },
      { severity: "LOW", score: 0.41, source: "SRV-01", message: "7036 - Service state change event" },
      { severity: "HIGH", score: 0.81, source: "WKST-22", message: "5140 - Network share object accessed" },
    ];
    const t = templates[Math.floor(Math.random() * templates.length)];
    const now = new Date();
    const time = `${now.getHours().toString().padStart(2,"0")}:${now.getMinutes().toString().padStart(2,"0")}:${now.getSeconds().toString().padStart(2,"0")}.${now.getMilliseconds().toString().padStart(3,"0")}`;
    setLogs(prev => [...prev.slice(-199), { id: prev.length + 1, time, ...t }]);
  };

  useEffect(() => {
    if (streaming) {
      intervalRef.current = setInterval(addRandomLog, 600);
    } else {
      clearInterval(intervalRef.current);
    }
    return () => clearInterval(intervalRef.current);
  }, [streaming]);

  useEffect(() => {
    if (autoScroll && consoleRef.current) {
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const filtered = filter === "ALL" ? logs : logs.filter(l => l.severity === filter);

  return (
    <AppLayout title="Real-Time Monitor" subtitle="Live log stream with AI scoring">
      <div className="space-y-4">
        {/* Controls */}
        <div className="cyber-card p-4 flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setStreaming(!streaming)}
              className="flex items-center gap-2 px-4 py-2 rounded-md text-sm font-semibold transition-all duration-200"
              style={
                streaming
                  ? { background: "hsl(var(--critical) / 0.15)", color: "hsl(var(--critical))", border: "1px solid hsl(var(--critical) / 0.3)" }
                  : { background: "hsl(var(--cyan) / 0.15)", color: "hsl(var(--cyan))", border: "1px solid hsl(var(--cyan) / 0.3)" }
              }
            >
              {streaming ? <><Square className="w-3.5 h-3.5" />Stop Stream</> : <><Play className="w-3.5 h-3.5" />Start Stream</>}
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
            {["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className="px-2.5 py-1 rounded text-xs font-mono font-semibold transition-colors"
                style={
                  filter === f
                    ? { background: "hsl(var(--cyan) / 0.15)", color: "hsl(var(--cyan))", border: "1px solid hsl(var(--cyan) / 0.3)" }
                    : { color: "hsl(var(--muted-foreground))", border: "1px solid transparent" }
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

        {/* Terminal Console */}
        <div className="terminal" style={{ height: "calc(100vh - 280px)" }}>
          <div className="flex items-center gap-2 px-4 py-2.5 border-b border-border/30" style={{ background: "hsl(0 0% 6%)" }}>
            <div className="w-2.5 h-2.5 rounded-full bg-cyber-critical" />
            <div className="w-2.5 h-2.5 rounded-full bg-cyber-medium" />
            <div className="w-2.5 h-2.5 rounded-full bg-cyber-low" />
            <span className="ml-2 text-xs text-muted-foreground font-mono">quorum://stream/logs — {filtered.length} events</span>
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
                  <span className="text-muted-foreground shrink-0 select-none">{log.time}</span>
                  <span className="shrink-0 w-16 text-center rounded px-1" style={{ color: severityColor[log.severity], background: `${severityColor[log.severity]}20` }}>
                    {log.severity}
                  </span>
                  <span className="shrink-0 w-14 text-cyan">{log.source}</span>
                  <span className="shrink-0 w-12 text-right" style={{ color: log.score > 0.9 ? "hsl(var(--critical))" : log.score > 0.75 ? "hsl(var(--high))" : log.score > 0.55 ? "hsl(var(--medium))" : "hsl(var(--low))" }}>
                    {log.score.toFixed(2)}
                  </span>
                  <span className="text-foreground/80 flex-1">{log.message}</span>
                </motion.div>
              ))}
            </AnimatePresence>
            {streaming && (
              <div className="flex items-center gap-2 px-2 py-1 text-xs font-mono text-muted-foreground">
                <span className="animate-blink">█</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
