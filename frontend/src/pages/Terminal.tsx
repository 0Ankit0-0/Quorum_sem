import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  TerminalSquare,
  ChevronRight,
  BookOpen,
  ChevronDown,
} from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";

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

const mockResponses: Record<string, string | string[]> = {
  help: [
    "Available commands:",
    "  status          — System status overview",
    "  scan usb        — Scan USB devices",
    "  scan lan        — Scan LAN nodes",
    "  logs recent     — Show recent log entries",
    "  logs ingest     — Ingest log files",
    "  analyze run     — Run analysis session",
    "  analyze list    — List analysis sessions",
    "  hub nodes       — Show registered nodes",
    "  hub export      — Export sync package",
    "  report gen      — Generate report",
    "  clear           — Clear terminal",
    "  whoami          — Current user info",
    "  uptime          — System uptime",
    "  version         — Quorum version",
  ].join("\n"),
  status: [
    "┌─────────────────────────────────┐",
    "│  QUORUM SYSTEM STATUS           │",
    "├─────────────────────────────────┤",
    "│  Environment:  AIR-GAPPED       │",
    "│  Total Logs:   284,913          │",
    "│  Anomalies:    1,847            │",
    "│  Sessions:     12               │",
    "│  Nodes Online: 7/8              │",
    "│  Uptime:       2,304 hours      │",
    "│  Status:       ● OPERATIONAL    │",
    "└─────────────────────────────────┘",
  ].join("\n"),
  whoami: "root@quorum-hub [AIR-GAPPED] — Role: Administrator",
  uptime:
    "System uptime: 2304 hours (96 days) — Last reboot: 2025-11-17T08:00:00Z",
  version: "Quorum v2.4.1 — Build 20260220 — Engine: Ensemble ML v3.1",
  "scan usb": [
    "Scanning USB devices...",
    "",
    "  [USB-001] SanDisk Ultra 64GB      — Mass Storage   — Risk: LOW",
    "  [USB-002] Unknown Device           — UNKNOWN        — Risk: HIGH ⚠",
    "  [USB-003] USB Network Adapter      — Network        — Risk: CRITICAL ⚠⚠",
    "  [USB-004] Logitech Keyboard        — HID            — Risk: LOW",
    "",
    "4 devices found. 2 flagged for review.",
  ].join("\n"),
  "scan lan": [
    "Scanning local network (192.168.1.0/24)...",
    "",
    "  192.168.1.10   WORKSTATION-14   Windows 11          ONLINE   MEDIUM",
    "  192.168.1.20   SERVER-02        Windows Server 2022 ONLINE   LOW",
    "  192.168.1.45   UNKNOWN          UNKNOWN             ONLINE   CRITICAL ⚠",
    "  192.168.1.100  SERVER-05        Ubuntu 22.04        ONLINE   LOW",
    "",
    "4 nodes discovered. 1 unidentified host.",
  ].join("\n"),
  "logs recent": [
    "Last 5 log entries:",
    "",
    "  [CRITICAL] 16:47:23 WKST-14  4625 - An account failed to log on",
    "  [HIGH]     16:47:19 SRV-02   The Windows Firewall service started",
    "  [MEDIUM]   16:47:15 auth.log sudo: USER=root ; COMMAND=/bin/bash",
    "  [LOW]      16:47:11 syslog   kernel: usb 1-1: new USB device",
    "  [CRITICAL] 16:47:08 PS.evtx  ScriptBlock: [Convert]::FromBase64String",
  ].join("\n"),
  "analyze run":
    "Starting analysis... Algorithm: ensemble | Threshold: 0.65\nProcessing 284,913 logs...\n████████████████████████████████ 100%\nComplete: 342 anomalies detected in 11.4s",
  "analyze list": [
    "Analysis Sessions:",
    "",
    "  SES-2024-001  ensemble         84,312 logs  342 anomalies  11.4s",
    "  SES-2024-002  isolation_forest  51,847 logs  187 anomalies   8.2s",
    "  SES-2024-003  one_class_svm    29,441 logs   94 anomalies  14.7s",
    "  SES-2024-004  statistical     119,313 logs 1224 anomalies   9.8s",
  ].join("\n"),
  "hub nodes": [
    "Registered Nodes:",
    "",
    "  NODE-001  HUB-PRIMARY   hub       ONLINE   284,913 logs",
    "  NODE-002  TERMINAL-A1   terminal  ONLINE    84,312 logs",
    "  NODE-003  TERMINAL-A2   terminal  ONLINE    51,847 logs",
    "  NODE-004  TERMINAL-B1   terminal  OFFLINE   29,441 logs",
    "  NODE-005  TERMINAL-B2   terminal  ONLINE   119,313 logs",
  ].join("\n"),
  "hub export":
    "Generating sync package...\nPackage: quorum_sync_20260220_164723.qsp (2.4 MB)\nRSA-PSS signature: VALID ✓\nReady for physical transfer.",
  "report gen":
    "Generating PDF report for SES-2024-001...\nReport: threat_analysis_feb20.pdf (1.8 MB)\nDownload ready.",
  "logs ingest":
    "Awaiting file input... (In production, use: quorum ingest <filepath>)\nExample: quorum ingest /var/log/auth.log",
};

const initialLines: TerminalLine[] = [
  {
    id: 0,
    type: "system",
    text: "╔══════════════════════════════════════════════════════════╗",
    timestamp: now(),
  },
  {
    id: 1,
    type: "system",
    text: "║  QUORUM CLI v2.4.1 — AI-Powered Threat Detection        ║",
    timestamp: now(),
  },
  {
    id: 2,
    type: "system",
    text: "║  Environment: AIR-GAPPED · Node: HUB-PRIMARY            ║",
    timestamp: now(),
  },
  {
    id: 3,
    type: "system",
    text: "╚══════════════════════════════════════════════════════════╝",
    timestamp: now(),
  },
  {
    id: 4,
    type: "system",
    text: 'Type "help" for available commands.',
    timestamp: now(),
  },
];

export default function Terminal() {
  const [lines, setLines] = useState<TerminalLine[]>(initialLines);
  const [input, setInput] = useState("");
  const [history, setHistory] = useState<string[]>([]);
  const [historyIdx, setHistoryIdx] = useState(-1);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  let nextId = useRef(initialLines.length);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  const addLine = useCallback((type: TerminalLine["type"], text: string) => {
    const id = nextId.current++;
    setLines((prev) => [...prev, { id, type, text, timestamp: now() }]);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const cmd = input.trim();
    if (!cmd) return;

    setHistory((prev) => [cmd, ...prev]);
    setHistoryIdx(-1);
    addLine("input", cmd);

    if (cmd === "clear") {
      setLines([]);
      setInput("");
      return;
    }

    const response = mockResponses[cmd];
    if (response) {
      setTimeout(
        () =>
          addLine(
            "output",
            typeof response === "string" ? response : response.join("\n"),
          ),
        150,
      );
    } else {
      setTimeout(
        () =>
          addLine(
            "error",
            `Command not found: "${cmd}". Type "help" for available commands.`,
          ),
        100,
      );
    }

    setInput("");
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

  const [showCmds, setShowCmds] = useState(false);

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
    { cmd: "whoami", desc: "Current user info" },
    { cmd: "uptime", desc: "System uptime" },
    { cmd: "version", desc: "Quorum version" },
  ];

  return (
    <AppLayout title="Terminal" subtitle="Execute Quorum CLI commands">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="h-[calc(100vh-140px)] flex flex-col gap-3"
      >
        {/* Collapsible Instructions */}
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
          {/* Terminal header bar */}
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

          {/* Output */}
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

          {/* Input */}
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
              placeholder="Enter command..."
            />
            <span className="animate-blink text-cyan font-mono">▌</span>
          </form>
        </div>
      </motion.div>
    </AppLayout>
  );
}
