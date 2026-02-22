import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  TerminalSquare,
  ChevronRight,
  BookOpen,
  ChevronDown,
} from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import {
  exportSyncPackage,
  generateReport,
  getDevices,
  getHubInfo,
  getLogs,
  getNodes,
  getRootInfo,
  getSessions,
  getSystemStatus,
  runAnalysis,
} from "@/lib/api-functions";
import { cliService } from "@/lib/cliService";

interface TerminalLine {
  id: number;
  type: "input" | "output" | "error" | "system";
  text: string;
  timestamp: string;
}

const now = () =>
  new Date().toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

const initialLines: TerminalLine[] = [
  {
    id: 0,
    type: "system",
    text: "QUORUM CLI - backend connected",
    timestamp: now(),
  },
  {
    id: 1,
    type: "system",
    text: 'Type "help" for available commands.',
    timestamp: now(),
  },
];

const cmdList = [
  { cmd: "status", desc: "System status overview" },
  { cmd: "scan usb", desc: "Scan USB devices" },
  { cmd: "scan lan", desc: "Scan LAN nodes" },
  { cmd: "logs recent", desc: "Show recent log entries" },
  { cmd: "logs ingest", desc: "Ingest log files" },
  { cmd: "analyze run", desc: "Run analysis session" },
  { cmd: "analyze list", desc: "List analysis sessions" },
  { cmd: "hub nodes", desc: "Show registered nodes" },
  { cmd: "hub export", desc: "Export sync package" },
  { cmd: "report gen", desc: "Generate report" },
  { cmd: "clear", desc: "Clear terminal" },
  { cmd: "whoami", desc: "Current node info" },
  { cmd: "uptime", desc: "System uptime" },
  { cmd: "version", desc: "Quorum version" },
];

export default function Terminal() {
  const [lines, setLines] = useState<TerminalLine[]>(initialLines);
  const [input, setInput] = useState("");
  const [history, setHistory] = useState<string[]>([]);
  const [historyIdx, setHistoryIdx] = useState(-1);
  const [showCmds, setShowCmds] = useState(false);
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const nextId = useRef(initialLines.length);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  const addLine = useCallback((type: TerminalLine["type"], text: string) => {
    const id = nextId.current++;
    setLines((prev) => [...prev, { id, type, text, timestamp: now() }]);
  }, []);

  const executeCommand = async (rawCmd: string): Promise<string> => {
    const cmd = rawCmd.toLowerCase().trim();

    if (cmd === "help") {
      return [
        "Available commands:",
        ...cmdList.map((c) => `  ${c.cmd.padEnd(13)} - ${c.desc}`),
      ].join("\n");
    }

    if (cmd === "status") {
      const s = await getSystemStatus();
      return [
        "QUORUM SYSTEM STATUS",
        `Environment: ${s.environment}`,
        `Total Logs: ${s.total_logs.toLocaleString()}`,
        `Anomalies: ${s.total_anomalies.toLocaleString()}`,
        `Sessions: ${s.active_sessions}`,
        `Nodes Online: ${s.nodes_online}`,
        `Uptime: ${s.uptime_hours} hours`,
      ].join("\n");
    }

    if (cmd === "scan usb") {
      const d = await getDevices();
      if (d.usb.length === 0) return "No USB devices detected.";
      return [
        "USB Devices:",
        ...d.usb.map(
          (u) =>
            `  [${u.id}] ${u.name} - ${u.type} - Risk: ${u.risk} (${u.vid}:${u.pid})`,
        ),
      ].join("\n");
    }

    if (cmd === "scan lan") {
      const d = await getDevices();
      if (d.lan.length === 0) return "No LAN nodes detected.";
      return [
        "LAN Nodes:",
        ...d.lan.map(
          (n) =>
            `  ${n.ip.padEnd(15)} ${n.hostname.padEnd(18)} ${n.status.padEnd(7)} ${n.risk}`,
        ),
      ].join("\n");
    }

    if (cmd === "logs recent") {
      const logs = await getLogs(5);
      if (logs.length === 0) return "No logs available.";
      return [
        "Last 5 log entries:",
        ...logs.map(
          (l) =>
            `  [${l.severity}] ${new Date(l.timestamp).toLocaleTimeString("en-US", {
              hour12: false,
            })} ${l.source} ${l.message}`,
        ),
      ].join("\n");
    }

    if (cmd === "analyze run") {
      const result = await runAnalysis({
        algorithm: "ensemble",
        threshold: 0.65,
        log_source: "latest",
      });
      return [
        `Session: ${result.session_id ?? "N/A"}`,
        `Status: ${result.status ?? "completed"}`,
        `Logs analyzed: ${(result.logs_analyzed ?? 0).toLocaleString()}`,
        `Anomalies: ${(result.anomalies_detected ?? 0).toLocaleString()}`,
        `Duration: ${result.duration_seconds ?? 0}s`,
      ].join("\n");
    }

    if (cmd === "analyze list") {
      const sessions = await getSessions(5);
      if (sessions.length === 0) return "No analysis sessions found.";
      return [
        "Analysis Sessions:",
        ...sessions.map(
          (s) =>
            `  ${s.id} ${s.algorithm.padEnd(15)} ${s.total_logs
              .toLocaleString()
              .padStart(8)} logs  ${s.anomalies_found.toString().padStart(5)} anomalies`,
        ),
      ].join("\n");
    }

    if (cmd === "hub nodes") {
      const nodes = await getNodes();
      if (nodes.length === 0) return "No nodes registered.";
      return [
        "Registered Nodes:",
        ...nodes.map(
          (n) =>
            `  ${n.id} ${n.hostname.padEnd(18)} ${n.role.padEnd(8)} ${n.status} ${n.total_logs.toLocaleString()} logs`,
        ),
      ].join("\n");
    }

    if (cmd === "hub export") {
      const { filename, blob } = await exportSyncPackage("hub", true);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      return `Sync package exported: ${filename}`;
    }

    if (cmd === "report gen") {
      const sessions = await getSessions(1);
      const sessionId = sessions[0]?.id;
      const r = await generateReport("PDF", sessionId);
      return `Report generated: ${r.filename}`;
    }

    if (cmd === "whoami") {
      const hub = await getHubInfo();
      return `${hub.hostname} (${hub.role}) - status: ${hub.status}`;
    }

    if (cmd === "uptime") {
      const s = await getSystemStatus();
      return `System uptime: ${s.uptime_hours} hours`;
    }

    if (cmd === "version") {
      const root = await getRootInfo();
      return `${root.name} v${root.version} - ${root.status}`;
    }

    if (cmd === "logs ingest") {
      return "Use the Logs page upload zone to ingest files into backend.";
    }

    try {
      const response = await cliService.executeCommand({
        command: `quorum ${cmd}`,
      });
      if (response.exit_code !== 0) {
        throw new Error(response.error || "Command failed");
      }
      return response.output || "Command completed.";
    } catch {
      throw new Error(`Command not found: \"${rawCmd}\". Type \"help\" for available commands.`);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cmd = input.trim();
    if (!cmd || busy) return;

    setHistory((prev) => [cmd, ...prev]);
    setHistoryIdx(-1);
    addLine("input", cmd);

    if (cmd.toLowerCase() === "clear") {
      setLines([]);
      setInput("");
      return;
    }

    setBusy(true);
    try {
      const output = await executeCommand(cmd);
      addLine("output", output);
    } catch (error) {
      addLine("error", error instanceof Error ? error.message : "Command failed");
    } finally {
      setBusy(false);
      setInput("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowUp") {
      e.preventDefault();
      const next = Math.min(historyIdx + 1, history.length - 1);
      setHistoryIdx(next);
      if (history[next]) setInput(history[next]);
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      const next = historyIdx - 1;
      setHistoryIdx(next);
      setInput(next < 0 ? "" : history[next] || "");
    }
  };

  const lineColor = (type: TerminalLine["type"]) => {
    switch (type) {
      case "input":
        return "hsl(var(--cyan))";
      case "error":
        return "hsl(var(--critical))";
      case "system":
        return "hsl(var(--medium))";
      default:
        return "hsl(var(--foreground))";
    }
  };

  return (
    <AppLayout title="Terminal" subtitle="Execute backend-connected Quorum commands">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="h-[calc(100vh-140px)] flex flex-col gap-3"
      >
        <div className="cyber-card overflow-hidden shrink-0">
          <button
            onClick={() => setShowCmds((prev) => !prev)}
            className="w-full flex items-center justify-between px-4 py-3 text-left transition-colors hover:bg-muted/50"
          >
            <div className="flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-cyan" />
              <span className="text-sm font-semibold text-foreground">
                Available Commands
              </span>
              <span className="text-xs text-muted-foreground">
                ({cmdList.length} commands)
              </span>
            </div>
            <motion.div
              animate={{ rotate: showCmds ? 180 : 0 }}
              transition={{ duration: 0.2 }}
            >
              <ChevronDown className="w-4 h-4 text-muted-foreground" />
            </motion.div>
          </button>
          <AnimatePresence>
            {showCmds && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <div className="px-4 pb-4 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-1.5 border-t border-border pt-3">
                  {cmdList.map((c) => (
                    <button
                      key={c.cmd}
                      onClick={(e) => {
                        e.stopPropagation();
                        setInput(c.cmd);
                        inputRef.current?.focus();
                      }}
                      className="flex items-start gap-2 p-2 rounded-md text-left transition-all hover:bg-muted"
                      style={{ border: "1px solid hsl(var(--border))" }}
                    >
                      <code className="text-xs font-mono text-cyan shrink-0">
                        {c.cmd}
                      </code>
                      <span className="text-[10px] text-muted-foreground leading-tight">
                        {c.desc}
                      </span>
                    </button>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div
          className="flex-1 terminal p-0 flex flex-col cursor-text min-h-0"
          onClick={() => inputRef.current?.focus()}
        >
          <div
            className="flex items-center gap-2 px-4 py-2 border-b border-border"
            style={{ background: "hsl(220 30% 6%)" }}
          >
            <TerminalSquare className="w-3.5 h-3.5 text-cyan" />
            <span className="text-xs font-mono text-muted-foreground">
              quorum@hub-primary: ~
            </span>
            <div className="flex-1" />
            <div className="flex gap-1.5">
              <div
                className="w-2.5 h-2.5 rounded-full"
                style={{ background: "hsl(var(--critical) / 0.7)" }}
              />
              <div
                className="w-2.5 h-2.5 rounded-full"
                style={{ background: "hsl(var(--medium) / 0.7)" }}
              />
              <div
                className="w-2.5 h-2.5 rounded-full"
                style={{ background: "hsl(var(--low) / 0.7)" }}
              />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-0.5">
            {lines.map((line) => (
              <div
                key={line.id}
                className="flex gap-2 font-mono text-[13px] leading-relaxed"
              >
                {line.type === "input" && (
                  <span
                    className="select-none shrink-0"
                    style={{ color: "hsl(var(--cyan))" }}
                  >
                    <ChevronRight className="w-3.5 h-3.5 inline -mt-0.5" /> $
                  </span>
                )}
                <pre
                  className="whitespace-pre-wrap break-all flex-1"
                  style={{ color: lineColor(line.type) }}
                >
                  {line.text}
                </pre>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          <form
            onSubmit={handleSubmit}
            className="flex items-center gap-2 px-4 py-3 border-t border-border"
            style={{ background: "hsl(220 30% 4%)" }}
          >
            <span className="text-cyan font-mono text-sm select-none">
              <ChevronRight className="w-3.5 h-3.5 inline -mt-0.5" /> $
            </span>
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              autoFocus
              spellCheck={false}
              className="flex-1 bg-transparent outline-none font-mono text-sm text-foreground placeholder:text-muted-foreground caret-cyan-400"
              placeholder={busy ? "Running command..." : "Enter command..."}
              disabled={busy}
            />
            <span className="animate-blink text-cyan font-mono">|</span>
          </form>
        </div>
      </motion.div>
    </AppLayout>
  );
}
