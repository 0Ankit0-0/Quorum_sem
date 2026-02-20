// Mock data for Quorum frontend demo
export const mockSystemStatus = {
  total_logs: 284_913,
  total_anomalies: 1_847,
  active_sessions: 12,
  environment: "AIR-GAPPED",
  nodes_online: 7,
  uptime_hours: 2304,
  last_analysis: "2026-02-20T14:22:11Z",
};

export const mockSeverityDistribution = [
  { severity: "CRITICAL", count: 89, fill: "#ef4444" },
  { severity: "HIGH", count: 342, fill: "#f97316" },
  { severity: "MEDIUM", count: 758, fill: "#eab308" },
  { severity: "LOW", count: 658, fill: "#22c55e" },
];

export const mockTimelineData = [
  { time: "02:00", anomalies: 12, critical: 1 },
  { time: "04:00", anomalies: 8, critical: 0 },
  { time: "06:00", anomalies: 24, critical: 3 },
  { time: "08:00", anomalies: 67, critical: 8 },
  { time: "10:00", anomalies: 142, critical: 12 },
  { time: "12:00", anomalies: 98, critical: 6 },
  { time: "14:00", anomalies: 187, critical: 19 },
  { time: "16:00", anomalies: 203, critical: 22 },
  { time: "18:00", anomalies: 156, critical: 14 },
  { time: "20:00", anomalies: 88, critical: 7 },
  { time: "22:00", anomalies: 44, critical: 3 },
  { time: "00:00", anomalies: 31, critical: 2 },
];

export const mockAnomalies = [
  {
    id: "ANM-001",
    timestamp: "2026-02-20T16:47:23Z",
    severity: "CRITICAL",
    message: "Multiple failed authentication attempts detected - brute force pattern",
    source: "WORKSTATION-14",
    algorithm: "ensemble",
    score: 0.97,
    mitre_id: "T1110",
    mitre_tactic: "Credential Access",
  },
  {
    id: "ANM-002",
    timestamp: "2026-02-20T16:31:07Z",
    severity: "CRITICAL",
    message: "Suspicious PowerShell execution with encoded command",
    source: "SERVER-02",
    algorithm: "isolation_forest",
    score: 0.95,
    mitre_id: "T1059.001",
    mitre_tactic: "Execution",
  },
  {
    id: "ANM-003",
    timestamp: "2026-02-20T16:18:45Z",
    severity: "HIGH",
    message: "Privilege escalation attempt via token impersonation",
    source: "WORKSTATION-07",
    algorithm: "ensemble",
    score: 0.88,
    mitre_id: "T1134",
    mitre_tactic: "Privilege Escalation",
  },
  {
    id: "ANM-004",
    timestamp: "2026-02-20T15:52:12Z",
    severity: "HIGH",
    message: "Lateral movement detected via SMB protocol",
    source: "WORKSTATION-22",
    algorithm: "statistical",
    score: 0.82,
    mitre_id: "T1021",
    mitre_tactic: "Lateral Movement",
  },
  {
    id: "ANM-005",
    timestamp: "2026-02-20T15:41:33Z",
    severity: "HIGH",
    message: "Unusual outbound connection to internal subnet",
    source: "SERVER-05",
    algorithm: "one_class_svm",
    score: 0.79,
    mitre_id: "T1071",
    mitre_tactic: "Command and Control",
  },
  {
    id: "ANM-006",
    timestamp: "2026-02-20T15:28:18Z",
    severity: "MEDIUM",
    message: "After-hours login from administrator account",
    source: "WORKSTATION-03",
    algorithm: "statistical",
    score: 0.71,
    mitre_id: "T1078",
    mitre_tactic: "Initial Access",
  },
  {
    id: "ANM-007",
    timestamp: "2026-02-20T15:11:04Z",
    severity: "MEDIUM",
    message: "Registry modification in HKLM\\Software\\Microsoft\\Windows\\Run",
    source: "WORKSTATION-11",
    algorithm: "ensemble",
    score: 0.68,
    mitre_id: "T1547.001",
    mitre_tactic: "Persistence",
  },
  {
    id: "ANM-008",
    timestamp: "2026-02-20T14:58:39Z",
    severity: "MEDIUM",
    message: "Large file copy to USB storage device",
    source: "WORKSTATION-18",
    algorithm: "isolation_forest",
    score: 0.64,
    mitre_id: "T1091",
    mitre_tactic: "Initial Access",
  },
  {
    id: "ANM-009",
    timestamp: "2026-02-20T14:37:22Z",
    severity: "LOW",
    message: "Repeated failed login from service account",
    source: "SERVER-01",
    algorithm: "statistical",
    score: 0.58,
    mitre_id: "T1110",
    mitre_tactic: "Credential Access",
  },
  {
    id: "ANM-010",
    timestamp: "2026-02-20T14:22:11Z",
    severity: "LOW",
    message: "New process created by non-standard parent",
    source: "WORKSTATION-09",
    algorithm: "one_class_svm",
    score: 0.54,
    mitre_id: "T1055",
    mitre_tactic: "Defense Evasion",
  },
];

export const mockLogs = [
  { id: "LOG-8821", timestamp: "2026-02-20T16:47:23Z", severity: "CRITICAL", source: "Security.evtx", message: "An account failed to log on. Logon Type: 10 (RemoteInteractive)", entries: 1 },
  { id: "LOG-8820", timestamp: "2026-02-20T16:47:19Z", severity: "HIGH", source: "System.evtx", message: "The Windows Firewall service has started", entries: 1 },
  { id: "LOG-8819", timestamp: "2026-02-20T16:47:15Z", severity: "MEDIUM", source: "auth.log", message: "sudo: USER=root ; COMMAND=/bin/bash", entries: 1 },
  { id: "LOG-8818", timestamp: "2026-02-20T16:47:11Z", severity: "LOW", source: "syslog", message: "kernel: usb 1-1: new high-speed USB device number 4 using xhci_hcd", entries: 1 },
  { id: "LOG-8817", timestamp: "2026-02-20T16:47:08Z", severity: "CRITICAL", source: "PowerShell.evtx", message: "ScriptBlock Text: [Convert]::FromBase64String", entries: 1 },
  { id: "LOG-8816", timestamp: "2026-02-20T16:47:02Z", severity: "HIGH", source: "Security.evtx", message: "A new process has been created. Process Name: cmd.exe Parent: winlogon.exe", entries: 1 },
  { id: "LOG-8815", timestamp: "2026-02-20T16:46:58Z", severity: "MEDIUM", source: "nginx.log", message: "POST /api/v1/auth 401 - from 192.168.1.45 repeated 47 times", entries: 47 },
];

export const mockDevices = {
  usb: [
    { id: "USB-001", name: "SanDisk Ultra 64GB", vid: "0781", pid: "5591", type: "Mass Storage", risk: "LOW", inserted_at: "2026-02-20T14:30:00Z", is_new: false },
    { id: "USB-002", name: "Unknown Device", vid: "1234", pid: "5678", type: "UNKNOWN", risk: "HIGH", inserted_at: "2026-02-20T15:52:00Z", is_new: true },
    { id: "USB-003", name: "USB Network Adapter", vid: "0bda", pid: "8153", type: "Network Adapter", risk: "CRITICAL", inserted_at: "2026-02-20T16:01:00Z", is_new: true },
    { id: "USB-004", name: "Logitech Keyboard", vid: "046d", pid: "c31d", type: "HID", risk: "LOW", inserted_at: "2026-02-18T09:00:00Z", is_new: false },
  ],
  lan: [
    { id: "LAN-001", ip: "192.168.1.10", hostname: "WORKSTATION-14", mac: "aa:bb:cc:dd:ee:01", os: "Windows 11", status: "ONLINE", risk: "MEDIUM" },
    { id: "LAN-002", ip: "192.168.1.20", hostname: "SERVER-02", mac: "aa:bb:cc:dd:ee:02", os: "Windows Server 2022", status: "ONLINE", risk: "LOW" },
    { id: "LAN-003", ip: "192.168.1.45", hostname: "UNKNOWN", mac: "ff:aa:bb:cc:dd:ee", os: "UNKNOWN", status: "ONLINE", risk: "CRITICAL" },
    { id: "LAN-004", ip: "192.168.1.100", hostname: "SERVER-05", mac: "aa:bb:cc:dd:ee:04", os: "Ubuntu 22.04", status: "ONLINE", risk: "LOW" },
  ],
};

export const mockSessions = [
  {
    id: "SES-2024-001",
    algorithm: "ensemble",
    threshold: 0.65,
    total_logs: 84_312,
    anomalies_found: 342,
    duration_seconds: 11.4,
    created_at: "2026-02-20T14:00:00Z",
    status: "COMPLETED",
  },
  {
    id: "SES-2024-002",
    algorithm: "isolation_forest",
    threshold: 0.70,
    total_logs: 51_847,
    anomalies_found: 187,
    duration_seconds: 8.2,
    created_at: "2026-02-19T22:00:00Z",
    status: "COMPLETED",
  },
  {
    id: "SES-2024-003",
    algorithm: "one_class_svm",
    threshold: 0.75,
    total_logs: 29_441,
    anomalies_found: 94,
    duration_seconds: 14.7,
    created_at: "2026-02-19T10:30:00Z",
    status: "COMPLETED",
  },
  {
    id: "SES-2024-004",
    algorithm: "statistical",
    threshold: 0.60,
    total_logs: 119_313,
    anomalies_found: 1_224,
    duration_seconds: 9.8,
    created_at: "2026-02-18T18:00:00Z",
    status: "COMPLETED",
  },
];

export const mockNodes = [
  { id: "NODE-001", hostname: "HUB-PRIMARY", role: "hub", status: "ONLINE", total_logs: 284_913, anomalies: 1_847, last_sync: "2026-02-20T16:00:00Z" },
  { id: "NODE-002", hostname: "TERMINAL-A1", role: "terminal", status: "ONLINE", total_logs: 84_312, anomalies: 342, last_sync: "2026-02-20T15:45:00Z" },
  { id: "NODE-003", hostname: "TERMINAL-A2", role: "terminal", status: "ONLINE", total_logs: 51_847, anomalies: 187, last_sync: "2026-02-20T15:30:00Z" },
  { id: "NODE-004", hostname: "TERMINAL-B1", role: "terminal", status: "OFFLINE", total_logs: 29_441, anomalies: 94, last_sync: "2026-02-19T22:00:00Z" },
  { id: "NODE-005", hostname: "TERMINAL-B2", role: "terminal", status: "ONLINE", total_logs: 119_313, anomalies: 1_224, last_sync: "2026-02-20T16:15:00Z" },
];

export const mockCorrelations = [
  {
    id: "COR-001",
    mitre_id: "T1110",
    tactic: "Credential Access",
    technique: "Brute Force",
    affected_nodes: ["TERMINAL-A1", "TERMINAL-A2", "TERMINAL-B2"],
    node_count: 3,
    total_events: 847,
    severity: "CRITICAL",
  },
  {
    id: "COR-002",
    mitre_id: "T1021",
    tactic: "Lateral Movement",
    technique: "Remote Services",
    affected_nodes: ["TERMINAL-A1", "TERMINAL-B2"],
    node_count: 2,
    total_events: 234,
    severity: "HIGH",
  },
];

export const mockStreamLogs = [
  { id: 1, time: "16:47:23.441", severity: "CRITICAL", score: 0.97, source: "WKST-14", message: "4625 - An account failed to log on [repeated 15x]" },
  { id: 2, time: "16:47:23.218", severity: "HIGH", score: 0.84, source: "SRV-02", message: "4688 - Process created: powershell.exe -enc JAB..." },
  { id: 3, time: "16:47:22.991", severity: "LOW", score: 0.42, source: "SRV-01", message: "7036 - Windows Update service entered running state" },
  { id: 4, time: "16:47:22.774", severity: "MEDIUM", score: 0.68, source: "WKST-07", message: "4672 - Special privileges assigned to new logon" },
  { id: 5, time: "16:47:22.550", severity: "HIGH", score: 0.81, source: "WKST-22", message: "5140 - Network share accessed: \\WKST-22\\C$" },
  { id: 6, time: "16:47:22.327", severity: "LOW", score: 0.38, source: "SRV-05", message: "6013 - System uptime: 2304 hours" },
  { id: 7, time: "16:47:22.104", severity: "CRITICAL", score: 0.96, source: "WKST-11", message: "Registry modification: HKLM\\SOFTWARE\\Microsoft\\Windows\\Run" },
  { id: 8, time: "16:47:21.881", severity: "MEDIUM", score: 0.63, source: "WKST-18", message: "USB storage device inserted - unknown VID:PID" },
];

export const mockReports = [
  { id: "RPT-001", type: "PDF", session_id: "SES-2024-001", name: "Threat Analysis Report - Feb 20", size_kb: 1847, created_at: "2026-02-20T14:30:00Z" },
  { id: "RPT-002", type: "CSV", session_id: "SES-2024-001", name: "Anomaly Export - Feb 20", size_kb: 342, created_at: "2026-02-20T14:31:00Z" },
  { id: "RPT-003", type: "PDF", session_id: "SES-2024-002", name: "Threat Analysis Report - Feb 19", size_kb: 1204, created_at: "2026-02-19T22:30:00Z" },
];

export const formatDate = (iso: string) => {
  const d = new Date(iso);
  return d.toLocaleString("en-US", { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
};

export const formatTimeAgo = (iso: string) => {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
};

export const formatNumber = (n: number) => n.toLocaleString();
