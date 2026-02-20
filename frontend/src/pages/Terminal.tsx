import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Terminal as TerminalIcon, Copy, Check, Search, Command, Play, Loader2 } from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { toast } from "sonner";
import { cliService, type CLIHelpResponse } from "@/lib/cliService";

interface CommandData {
  command: string;
  description: string;
  output: string;
  category?: string;
}

const CLI_COMMANDS = {
  system: [
    {
      command: 'quorum status',
      description: 'Display system overview and health status',
      output: `✓ Database:
  Logs: 284,913
  Anomalies: 1,847
  Sessions: 12
  Hub Nodes: 7

✓ Real-Time Monitor:
  Status: RUNNING
  Files: 4
  Lines: 15,234
  Alerts: 23

✓ Environment:
  Status: AIR-GAPPED
  Role: terminal
  OS: Windows 11

✓ System operational`
    },
    {
      command: 'quorum init',
      description: 'Initialize Quorum database and configuration',
      output: `Initializing Quorum v2.4.1...
✓ Creating database schema
✓ Setting up default configuration
✓ Registering node (NODE-001)
✓ Generating RSA-PSS keypair (4096-bit)

Initialization complete!
Run 'quorum status' to verify.`
    }
  ],
  logs: [
    {
      command: 'quorum ingest scan',
      description: 'Auto-discover system log files',
      output: `Scanning for log files...

Windows Event Logs:
  ✓ C:\\Windows\\System32\\winevt\\Logs\\Security.evtx
  ✓ C:\\Windows\\System32\\winevt\\Logs\\System.evtx
  ✓ C:\\Windows\\System32\\winevt\\Logs\\Application.evtx
  ✓ C:\\Windows\\System32\\winevt\\Logs\\PowerShell.evtx

Found 4 log sources (estimated 284,913 entries)
Run 'quorum ingest collect' to import.`
    },
    {
      command: 'quorum ingest collect',
      description: 'Collect and import discovered logs into database',
      output: `Collecting logs...
[████████████████████████████████████] 100%

Processed:
  Security.evtx      156,234 entries  (2.1s)
  System.evtx         84,521 entries  (1.3s)
  Application.evtx    38,442 entries  (0.8s)
  PowerShell.evtx      5,716 entries  (0.3s)

Total: 284,913 entries in 4.5 seconds
Parse errors: 0`
    },
    {
      command: 'quorum ingest file Security.evtx',
      description: 'Import a specific log file',
      output: `Importing Security.evtx...
Parsing Windows Event Log...
[████████████████████████████████████] 100%

Imported: 156,234 entries
Duration: 2.1 seconds
Parse errors: 0

✓ Import successful`
    }
  ],
  analysis: [
    {
      command: 'quorum analyze run --algorithm ensemble',
      description: 'Run AI anomaly detection with ensemble algorithm',
      output: `Running ensemble analysis...

Algorithm: Hybrid 4-Component Ensemble
  - Isolation Forest (35%)
  - One-Class SVM (25%)
  - Statistical Z-score (20%)
  - Keyword Engine (20%)

Threshold: 0.70
Contamination: 0.05

Analyzing 284,913 logs...
  Feature extraction: 0.71s
  AI detection: 8.28s
  Total: 8.99s

Results:
  CRITICAL: 5  (0.97+ score)
  HIGH: 12     (0.75-0.96 score)
  MEDIUM: 18   (0.55-0.74 score)
  LOW: 7       (0.35-0.54 score)

Session ID: SES-2024-001

✓ Analysis complete`
    },
    {
      command: 'quorum analyze sessions',
      description: 'List all analysis sessions',
      output: `Analysis Sessions:

SES-2024-001  ensemble         284,913 logs  342 anomalies  11.4s  just now
SES-2024-002  isolation_forest  51,847 logs  187 anomalies   8.2s  13h ago
SES-2023-092  one_class_svm     29,441 logs   94 anomalies   6.1s  2d ago

Total: 3 sessions`
    }
  ],
  monitor: [
    {
      command: 'quorum monitor watch --auto',
      description: 'Start real-time log monitoring with auto-discovery',
      output: `Auto-discovering system logs...
Found 4 log sources

Starting real-time monitor...
Watching:
  - Security.evtx
  - System.evtx
  - auth.log
  - syslog

[LIVE STREAM - Press Ctrl+C to stop]

16:47:23.441  CRITICAL  WKST-14   0.97  An account failed to log on [repeated 15x]
16:47:23.218  HIGH      SRV-02    0.84  Process created: powershell.exe -enc JAB...
16:47:22.991  LOW       SRV-01    0.42  Windows Update service entered running state
16:47:22.774  MEDIUM    WKST-07   0.68  Special privileges assigned to new logon
16:47:22.550  HIGH      WKST-22   0.81  Network share accessed: \\\\WKST-22\\C$`
    },
    {
      command: 'quorum monitor status',
      description: 'Show real-time monitor status',
      output: `Real-Time Monitor Status:

Status: RUNNING
Started: 16:45:12 (2m 31s ago)

Files watched: 4
Lines processed: 15,234
Anomalies found: 23

Watched files:
  ✓ C:\\Windows\\System32\\winevt\\Logs\\Security.evtx
  ✓ C:\\Windows\\System32\\winevt\\Logs\\System.evtx
  ✓ /var/log/auth.log
  ✓ /var/log/syslog`
    }
  ],
  devices: [
    {
      command: 'quorum devices scan',
      description: 'Scan for USB devices and LAN nodes',
      output: `Scanning devices...

USB / Physical Devices (5 found):
──────────────────────────────────────────────────────
STORAGE  SanDisk Cruzer Blade                    [HIGH] [NEW]
         Vendor: SanDisk
         VID:PID: 0781:5567
         Serial: 4C530001140516116282
         Mounted: D:\\

STORAGE  Kingston DataTraveler                   [HIGH]
         Vendor: Kingston
         VID:PID: 13fe:4200
         Mounted: E:\\

AUDIO    USB Headset                             [MEDIUM]
         Vendor: C-Media
         VID:PID: 0d8c:0014

HID      Logitech USB Keyboard                   [LOW]
         Vendor: Logitech
         VID:PID: 046d:c31c

HID      USB Mouse                               [LOW]
         Vendor: Generic
         VID:PID: 093a:2510

LAN Nodes (3 found):
──────────────────────────────────────────────────────
IP Address      Hostname        MAC                Status
192.168.1.100   DESKTOP-A1B2    aa:bb:cc:dd:ee:ff  known
192.168.1.101   LAPTOP-C3D4     11:22:33:44:55:66  NEW
192.168.1.102   SERVER-DB01     22:33:44:55:66:77  known

⚠ 2 high-risk devices detected
Run 'quorum devices scan-logs' to check USB storage for logs`
    },
    {
      command: 'quorum devices watch',
      description: 'Monitor for USB hotplug events in real-time',
      output: `Watching for device hotplug events...
[Press Ctrl+C to stop]

16:45:12  CONNECTED     STORAGE     SanDisk Cruzer Blade  [HIGH]
          VID:PID: 0781:5567
          Serial: 4C530001140516116282

16:46:33  CONNECTED     AUDIO       USB Headset           [MEDIUM]

16:47:01  DISCONNECTED  STORAGE     SanDisk Cruzer Blade  [HIGH]

16:48:15  CONNECTED     SMARTPHONE  Android Phone (MTP)   [HIGH]
          VID:PID: 18d1:4ee1`
    },
    {
      command: 'quorum devices history',
      description: 'Show device connection history',
      output: `Device Connection History (last 50 events):

TIME               EVENT         CLASS        NAME                   RISK
───────────────────────────────────────────────────────────────────────────────
Feb 20, 16:48:15   CONNECTED     SMARTPHONE   Android Phone          [HIGH]
Feb 20, 16:47:01   DISCONNECTED  STORAGE      SanDisk Cruzer         [HIGH]
Feb 20, 16:46:33   CONNECTED     AUDIO        USB Headset            [MEDIUM]
Feb 20, 16:45:12   CONNECTED     STORAGE      SanDisk Cruzer         [HIGH]
Feb 20, 14:23:41   DISCONNECTED  STORAGE      Kingston DT            [HIGH]
Feb 20, 12:15:03   CONNECTED     STORAGE      Kingston DT            [HIGH]`
    }
  ],
  hub: [
    {
      command: 'quorum hub register --role terminal',
      description: 'Register this machine as a terminal node',
      output: `Registering node...

Node ID: NODE-001-A3F2
Hostname: WORKSTATION-14
Role: terminal
OS: Windows 11 Pro
IP: 192.168.1.50

✓ Node registered successfully
✓ RSA-PSS keypair generated (4096-bit)

Run 'quorum hub export' to create sync package.`
    },
    {
      command: 'quorum hub export',
      description: 'Export sync package for USB transfer to hub',
      output: `Exporting anomalies to sync package...

Source Node: NODE-001-A3F2 (WORKSTATION-14)
Anomalies: 342
Time range: Last 24 hours

Creating package...
[████████████████████████████████████] 100%

Package: sync_node-001_20260220-164523.qsp
Size: 1.2 MB
Signature: RSA-PSS 4096-bit ✓

✓ Package created: data/sync_node-001_20260220-164523.qsp

Copy to USB and import on hub with:
  quorum hub import <package-file>`
    },
    {
      command: 'quorum hub scan-usb',
      description: 'Scan USB drives for sync packages and auto-import',
      output: `Scanning USB drives for sync packages...

Found 3 packages:

D:\\sync_node-001_20260220-164523.qsp (1.2 MB)
  Source: WORKSTATION-14
  Anomalies: 342
  Signature: ✓ Valid

D:\\sync_node-003_20260220-152341.qsp (0.8 MB)
  Source: LAPTOP-C3D4
  Anomalies: 187
  Signature: ✓ Valid

E:\\sync_node-005_20260219-183012.qsp (0.3 MB)
  Source: SERVER-DB01
  Anomalies: 94
  Signature: ✓ Valid

Importing packages...
[████████████████████████████████████] 100%

✓ Imported 3 packages (623 total anomalies)`
    },
    {
      command: 'quorum hub nodes',
      description: 'List all registered nodes',
      output: `Registered Nodes:

HUB-PRIMARY (hub)
  Node ID: NODE-000-HUB1
  Status: ONLINE
  Total Logs: 284,913
  Anomalies: 1,847
  Last Sync: just now

WORKSTATION-14 (terminal)
  Node ID: NODE-001-A3F2
  Status: ONLINE
  Total Logs: 84,312
  Anomalies: 342
  Last Sync: just now

LAPTOP-C3D4 (terminal)
  Node ID: NODE-003-B7E4
  Status: ONLINE
  Total Logs: 51,847
  Anomalies: 187
  Last Sync: 13h ago

SERVER-DB01 (terminal)
  Node ID: NODE-005-C2A9
  Status: OFFLINE
  Total Logs: 29,441
  Anomalies: 94
  Last Sync: 2d ago

Total: 4 nodes (3 online, 1 offline)`
    },
    {
      command: 'quorum hub correlate',
      description: 'Find cross-node attack correlations',
      output: `Cross-Node Correlation Analysis:

[CRITICAL] T1110.001 — Brute Force: Password Guessing
  Nodes affected: 3 (WORKSTATION-14, LAPTOP-C3D4, SERVER-DB01)
  Total hits: 847
  Avg score: 0.924
  First seen: Feb 19, 12:14:10
  Last seen: Feb 20, 16:52:00

[HIGH] T1021.001 — Remote Desktop Protocol
  Nodes affected: 2 (WORKSTATION-14, LAPTOP-C3D4)
  Total hits: 156
  Avg score: 0.812
  First seen: Feb 20, 08:23:15
  Last seen: Feb 20, 14:41:22

[HIGH] T1078 — Valid Accounts
  Nodes affected: 2 (LAPTOP-C3D4, SERVER-DB01)
  Total hits: 94
  Avg score: 0.784
  First seen: Feb 19, 18:45:33
  Last seen: Feb 20, 12:15:08

⚠ Coordinated attack detected across multiple nodes`
    }
  ],
  reports: [
    {
      command: 'quorum report generate --type pdf',
      description: 'Generate PDF threat analysis report',
      output: `Generating PDF report...

Session: SES-2024-001 (ensemble)
Anomalies: 342
Time range: Feb 19, 00:00 - Feb 20, 16:52

Creating report...
[████████████████████████████████████] 100%

Report sections:
  ✓ Executive Summary
  ✓ Severity Distribution Chart
  ✓ Anomaly Timeline Chart
  ✓ Top Sources Chart
  ✓ MITRE ATT&CK Mapping
  ✓ Detailed Anomaly Table
  ✓ Recommendations

✓ Report generated: reports/threat_analysis_20260220.pdf
Size: 1.8 MB`
    },
    {
      command: 'quorum report list',
      description: 'List all generated reports',
      output: `Available Reports:

threat_analysis_20260220.pdf
  Session: SES-2024-001
  Created: Feb 20, 20:00:00
  Size: 1.8 MB

anomaly_export_20260220.csv
  Session: SES-2024-001
  Created: Feb 20, 20:01:00
  Size: 342 KB

threat_analysis_20260219.pdf
  Session: SES-2024-002
  Created: Feb 19, 04:00:00
  Size: 1.2 MB

Total: 3 reports`
    }
  ],
  quickstart: [
    { command: 'quorum status', description: 'Check system health', category: 'System', output: '' },
    { command: 'quorum ingest collect', description: 'Import system logs', category: 'Logs', output: '' },
    { command: 'quorum analyze run --algorithm ensemble', description: 'Run AI detection', category: 'Analysis', output: '' }
  ]
};

const CommandCard = ({ cmd }: { cmd: CommandData }) => {
  const [copied, setCopied] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [liveOutput, setLiveOutput] = useState<string | null>(null);

  const handleCopy = () => {
    navigator.clipboard.writeText(cmd.command);
    setCopied(true);
    toast.success("Command copied to clipboard");
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExecute = async () => {
    setExecuting(true);
    setLiveOutput(null);
    
    try {
      // Parse command and args
      const parts = cmd.command.split(' ');
      const command = parts[0];
      const args = parts.slice(1);
      
      const response = await cliService.executeCommand({ command, args });
      
      if (response.exit_code === 0) {
        setLiveOutput(response.output);
        toast.success("Command executed successfully");
      } else {
        setLiveOutput(response.error || "Command failed");
        toast.error("Command execution failed");
      }
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || "Failed to execute command";
      setLiveOutput(`Error: ${errorMsg}`);
      toast.error(errorMsg);
    } finally {
      setExecuting(false);
    }
  };

  // Syntax highlight special characters in terminal output
  const renderOutput = (text: string) => {
    return text.split('\n').map((line, i) => {
      let styledLine = line;
      
      // Color checkmarks green
      if (line.includes('✓')) {
        styledLine = line.replace(/✓/g, '<span class="text-low">✓</span>');
      }
      
      // Color warnings orange
      if (line.includes('⚠')) {
        styledLine = line.replace(/⚠/g, '<span class="text-medium">⚠</span>');
      }
      
      // Color errors red
      if (line.includes('✗')) {
        styledLine = line.replace(/✗/g, '<span class="text-critical">✗</span>');
      }
      
      // Color progress bars cyan
      if (line.includes('█')) {
        styledLine = line.replace(/\[([█\s]+)\]/g, '<span class="text-cyan">[$1]</span>');
      }

      // Color severity badges
      if (line.includes('CRITICAL')) {
        styledLine = styledLine.replace(/CRITICAL/g, '<span class="text-critical font-bold">CRITICAL</span>');
      }
      if (line.includes('HIGH')) {
        styledLine = styledLine.replace(/HIGH/g, '<span class="text-high font-bold">HIGH</span>');
      }
      if (line.includes('MEDIUM')) {
        styledLine = styledLine.replace(/MEDIUM/g, '<span class="text-medium font-bold">MEDIUM</span>');
      }
      if (line.includes('LOW')) {
        styledLine = styledLine.replace(/LOW/g, '<span class="text-low font-bold">LOW</span>');
      }
      
      return <div key={i} dangerouslySetInnerHTML={{ __html: styledLine }} />;
    });
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="cyber-card overflow-hidden"
    >
      <div className="px-5 py-4 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-3 flex-1">
          <TerminalIcon className="w-4 h-4 text-cyan shrink-0" />
          <code className="text-sm font-semibold text-cyan mono">$ {cmd.command}</code>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleExecute}
            disabled={executing}
            className="flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all shrink-0 disabled:opacity-50"
            style={{ background: "hsl(var(--low) / 0.1)", color: "hsl(var(--low))", border: "1px solid hsl(var(--low) / 0.3)" }}
          >
            {executing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
            {executing ? "Running..." : "Run"}
          </button>
          <button
            onClick={handleCopy}
            className="flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all shrink-0"
            style={{ background: "hsl(var(--cyan) / 0.1)", color: "hsl(var(--cyan))", border: "1px solid hsl(var(--cyan) / 0.3)" }}
          >
            {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
      </div>
      <div className="px-5 py-3">
        <p className="text-sm text-muted-foreground">{cmd.description}</p>
      </div>
      {(liveOutput || cmd.output) && (
        <div className="px-5 pb-5">
          {liveOutput && (
            <div className="mb-3">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-2 h-2 rounded-full bg-low animate-pulse" />
                <span className="text-xs font-semibold text-low uppercase tracking-wide">Live Output</span>
              </div>
              <div className="rounded-lg p-4 overflow-x-auto mono text-sm" style={{ background: "#000000", color: "#10b981" }}>
                {renderOutput(liveOutput)}
              </div>
            </div>
          )}
          {cmd.output && !liveOutput && (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Example Output</span>
              </div>
              <div className="rounded-lg p-4 overflow-x-auto mono text-sm" style={{ background: "#000000", color: "#10b981" }}>
                {renderOutput(cmd.output)}
              </div>
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
};

const QuickStartCard = ({ cmd }: { cmd: CommandData }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(cmd.command);
    setCopied(true);
    toast.success("Command copied to clipboard");
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ scale: 1.02 }}
      className="cyber-card-glow p-5 cursor-pointer group"
      onClick={handleCopy}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1">{cmd.category}</div>
          <code className="text-base font-bold text-cyan mono block">{cmd.command}</code>
        </div>
        <div className="shrink-0">
          {copied ? (
            <Check className="w-5 h-5 text-low" />
          ) : (
            <Command className="w-5 h-5 text-cyan group-hover:scale-110 transition-transform" />
          )}
        </div>
      </div>
      <p className="text-sm text-muted-foreground">{cmd.description}</p>
    </motion.div>
  );
};

export default function Terminal() {
  const [searchQuery, setSearchQuery] = useState("");
  const [showCommandGuide, setShowCommandGuide] = useState(false);
  const [cliHelp, setCliHelp] = useState<CLIHelpResponse | null>(null);
  const [loadingHelp, setLoadingHelp] = useState(false);

  // Fetch CLI help on component mount
  useEffect(() => {
    const fetchHelp = async () => {
      setLoadingHelp(true);
      try {
        const help = await cliService.getHelp();
        setCliHelp(help);
      } catch (error) {
        console.error("Failed to fetch CLI help:", error);
      } finally {
        setLoadingHelp(false);
      }
    };
    
    fetchHelp();
  }, []);

  // Filter commands based on search
  const filterCommands = (commands: CommandData[]) => {
    if (!searchQuery) return commands;
    return commands.filter(cmd =>
      cmd.command.toLowerCase().includes(searchQuery.toLowerCase()) ||
      cmd.description.toLowerCase().includes(searchQuery.toLowerCase())
    );
  };

  return (
    <AppLayout title="CLI Interface" subtitle="Command-line reference and usage examples">
      <div className="space-y-6">
        {/* Search and Controls */}
        <div className="flex items-center gap-4 flex-wrap">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search commands..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 rounded-md text-sm bg-card border border-border text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-cyan/50 focus:border-cyan transition-all"
            />
          </div>
          <button
            onClick={() => setShowCommandGuide(!showCommandGuide)}
            className="flex items-center gap-2 px-5 py-2.5 rounded-md text-sm font-semibold transition-all"
            style={{ background: "hsl(var(--cyan) / 0.15)", color: "hsl(var(--cyan))", border: "1px solid hsl(var(--cyan) / 0.3)" }}
          >
            <Command className="w-4 h-4" />
            {showCommandGuide ? "Hide" : "Show"} Command Guide
          </button>
        </div>

        {/* Command Guide */}
        {showCommandGuide && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="cyber-card p-5"
          >
            <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
              <TerminalIcon className="w-4 h-4 text-cyan" />
              {cliHelp ? cliHelp.title : "Getting Started with Quorum CLI"}
            </h3>
            {loadingHelp ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="w-4 h-4 animate-spin" />
                Loading CLI help...
              </div>
            ) : cliHelp ? (
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">{cliHelp.description}</p>
                <div className="space-y-2 text-sm text-muted-foreground">
                  {cliHelp.getting_started.map((tip, i) => (
                    <p key={i}>• {tip}</p>
                  ))}
                </div>
                <div className="flex items-center gap-3 pt-2 border-t border-border">
                  <div className="text-xs">
                    <span className="text-muted-foreground">Version:</span>{" "}
                    <span className="text-cyan font-mono">{cliHelp.version}</span>
                  </div>
                  <div className="text-xs">
                    <span className="text-muted-foreground">Total Commands:</span>{" "}
                    <span className="text-cyan font-mono">{cliHelp.total_commands}</span>
                  </div>
                  <div className="text-xs">
                    <span className="text-muted-foreground">Categories:</span>{" "}
                    <span className="text-cyan font-mono">{cliHelp.categories.length}</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-2 text-sm text-muted-foreground">
                <p>• All commands start with <code className="text-cyan mono px-1.5 py-0.5 rounded bg-black">quorum</code></p>
                <p>• Use <code className="text-cyan mono px-1.5 py-0.5 rounded bg-black">--help</code> flag on any command for detailed usage</p>
                <p>• Commands are organized by category: System, Logs, Analysis, Monitor, Devices, Hub, and Reports</p>
                <p>• Click "Run" to execute commands or "Copy" to copy them to your clipboard</p>
                <p>• Refer to the terminal output examples to understand expected results</p>
              </div>
            )}
          </motion.div>
        )}

        {/* Quick Start Section */}
        <div>
          <div className="mb-4">
            <h2 className="text-lg font-bold text-foreground mb-1">Quick Start</h2>
            <p className="text-sm text-muted-foreground">Most common commands to get you started</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {CLI_COMMANDS.quickstart.map((cmd, i) => (
              <QuickStartCard key={i} cmd={cmd} />
            ))}
          </div>
        </div>

        {/* Command Reference Tabs */}
        <div>
          <div className="mb-4">
            <h2 className="text-lg font-bold text-foreground mb-1">Command Reference</h2>
            <p className="text-sm text-muted-foreground">Complete documentation for all CLI commands</p>
          </div>

          <Tabs defaultValue="system" className="w-full">
            <TabsList className="w-full justify-start flex-wrap h-auto">
              <TabsTrigger value="system">System</TabsTrigger>
              <TabsTrigger value="logs">Logs & Ingestion</TabsTrigger>
              <TabsTrigger value="analysis">Analysis</TabsTrigger>
              <TabsTrigger value="monitor">Real-Time Monitor</TabsTrigger>
              <TabsTrigger value="devices">Devices</TabsTrigger>
              <TabsTrigger value="hub">Hub Operations</TabsTrigger>
              <TabsTrigger value="reports">Reports</TabsTrigger>
            </TabsList>

            <TabsContent value="system">
              <div className="space-y-4">
                {filterCommands(CLI_COMMANDS.system).map((cmd, i) => (
                  <CommandCard key={i} cmd={cmd} />
                ))}
                {filterCommands(CLI_COMMANDS.system).length === 0 && (
                  <div className="cyber-card p-8 text-center text-muted-foreground">
                    No commands found matching "{searchQuery}"
                  </div>
                )}
              </div>
            </TabsContent>

            <TabsContent value="logs">
              <div className="space-y-4">
                {filterCommands(CLI_COMMANDS.logs).map((cmd, i) => (
                  <CommandCard key={i} cmd={cmd} />
                ))}
                {filterCommands(CLI_COMMANDS.logs).length === 0 && (
                  <div className="cyber-card p-8 text-center text-muted-foreground">
                    No commands found matching "{searchQuery}"
                  </div>
                )}
              </div>
            </TabsContent>

            <TabsContent value="analysis">
              <div className="space-y-4">
                {filterCommands(CLI_COMMANDS.analysis).map((cmd, i) => (
                  <CommandCard key={i} cmd={cmd} />
                ))}
                {filterCommands(CLI_COMMANDS.analysis).length === 0 && (
                  <div className="cyber-card p-8 text-center text-muted-foreground">
                    No commands found matching "{searchQuery}"
                  </div>
                )}
              </div>
            </TabsContent>

            <TabsContent value="monitor">
              <div className="space-y-4">
                {filterCommands(CLI_COMMANDS.monitor).map((cmd, i) => (
                  <CommandCard key={i} cmd={cmd} />
                ))}
                {filterCommands(CLI_COMMANDS.monitor).length === 0 && (
                  <div className="cyber-card p-8 text-center text-muted-foreground">
                    No commands found matching "{searchQuery}"
                  </div>
                )}
              </div>
            </TabsContent>

            <TabsContent value="devices">
              <div className="space-y-4">
                {filterCommands(CLI_COMMANDS.devices).map((cmd, i) => (
                  <CommandCard key={i} cmd={cmd} />
                ))}
                {filterCommands(CLI_COMMANDS.devices).length === 0 && (
                  <div className="cyber-card p-8 text-center text-muted-foreground">
                    No commands found matching "{searchQuery}"
                  </div>
                )}
              </div>
            </TabsContent>

            <TabsContent value="hub">
              <div className="space-y-4">
                {filterCommands(CLI_COMMANDS.hub).map((cmd, i) => (
                  <CommandCard key={i} cmd={cmd} />
                ))}
                {filterCommands(CLI_COMMANDS.hub).length === 0 && (
                  <div className="cyber-card p-8 text-center text-muted-foreground">
                    No commands found matching "{searchQuery}"
                  </div>
                )}
              </div>
            </TabsContent>

            <TabsContent value="reports">
              <div className="space-y-4">
                {filterCommands(CLI_COMMANDS.reports).map((cmd, i) => (
                  <CommandCard key={i} cmd={cmd} />
                ))}
                {filterCommands(CLI_COMMANDS.reports).length === 0 && (
                  <div className="cyber-card p-8 text-center text-muted-foreground">
                    No commands found matching "{searchQuery}"
                  </div>
                )}
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </AppLayout>
  );
}
