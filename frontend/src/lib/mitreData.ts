// MITRE ATT&CK framework data for heatmap visualization

export interface MitreTechnique {
  id: string;
  name: string;
  tactic: string;
  detections: number; // 0 = no coverage
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "NONE";
}

export const mitreTactics = [
  "Initial Access",
  "Execution",
  "Persistence",
  "Privilege Escalation",
  "Defense Evasion",
  "Credential Access",
  "Discovery",
  "Lateral Movement",
  "Collection",
  "Command and Control",
  "Exfiltration",
  "Impact",
];

export const mitreTechniques: MitreTechnique[] = [
  // Initial Access
  { id: "T1078", name: "Valid Accounts", tactic: "Initial Access", detections: 14, severity: "MEDIUM" },
  { id: "T1091", name: "Replication Via Removable Media", tactic: "Initial Access", detections: 8, severity: "MEDIUM" },
  { id: "T1200", name: "Hardware Additions", tactic: "Initial Access", detections: 3, severity: "LOW" },
  { id: "T1566", name: "Phishing", tactic: "Initial Access", detections: 0, severity: "NONE" },

  // Execution
  { id: "T1059.001", name: "PowerShell", tactic: "Execution", detections: 47, severity: "CRITICAL" },
  { id: "T1059.003", name: "Windows Command Shell", tactic: "Execution", detections: 22, severity: "HIGH" },
  { id: "T1204", name: "User Execution", tactic: "Execution", detections: 5, severity: "LOW" },
  { id: "T1053", name: "Scheduled Task/Job", tactic: "Execution", detections: 11, severity: "MEDIUM" },

  // Persistence
  { id: "T1547.001", name: "Registry Run Keys", tactic: "Persistence", detections: 31, severity: "HIGH" },
  { id: "T1543", name: "Create/Modify System Process", tactic: "Persistence", detections: 9, severity: "MEDIUM" },
  { id: "T1136", name: "Create Account", tactic: "Persistence", detections: 2, severity: "LOW" },

  // Privilege Escalation
  { id: "T1134", name: "Access Token Manipulation", tactic: "Privilege Escalation", detections: 28, severity: "HIGH" },
  { id: "T1068", name: "Exploitation for Privilege Escalation", tactic: "Privilege Escalation", detections: 4, severity: "MEDIUM" },
  { id: "T1548", name: "Abuse Elevation Control", tactic: "Privilege Escalation", detections: 15, severity: "HIGH" },

  // Defense Evasion
  { id: "T1055", name: "Process Injection", tactic: "Defense Evasion", detections: 19, severity: "HIGH" },
  { id: "T1070", name: "Indicator Removal", tactic: "Defense Evasion", detections: 7, severity: "MEDIUM" },
  { id: "T1036", name: "Masquerading", tactic: "Defense Evasion", detections: 12, severity: "MEDIUM" },
  { id: "T1027", name: "Obfuscated Files", tactic: "Defense Evasion", detections: 33, severity: "CRITICAL" },

  // Credential Access
  { id: "T1110", name: "Brute Force", tactic: "Credential Access", detections: 89, severity: "CRITICAL" },
  { id: "T1003", name: "OS Credential Dumping", tactic: "Credential Access", detections: 6, severity: "HIGH" },
  { id: "T1558", name: "Steal or Forge Kerberos Tickets", tactic: "Credential Access", detections: 0, severity: "NONE" },

  // Discovery
  { id: "T1087", name: "Account Discovery", tactic: "Discovery", detections: 18, severity: "MEDIUM" },
  { id: "T1083", name: "File and Directory Discovery", tactic: "Discovery", detections: 10, severity: "LOW" },
  { id: "T1046", name: "Network Service Discovery", tactic: "Discovery", detections: 24, severity: "HIGH" },

  // Lateral Movement
  { id: "T1021", name: "Remote Services", tactic: "Lateral Movement", detections: 42, severity: "CRITICAL" },
  { id: "T1080", name: "Taint Shared Content", tactic: "Lateral Movement", detections: 3, severity: "LOW" },
  { id: "T1570", name: "Lateral Tool Transfer", tactic: "Lateral Movement", detections: 8, severity: "MEDIUM" },

  // Collection
  { id: "T1005", name: "Data from Local System", tactic: "Collection", detections: 15, severity: "MEDIUM" },
  { id: "T1039", name: "Data from Network Shared Drive", tactic: "Collection", detections: 7, severity: "MEDIUM" },

  // Command and Control
  { id: "T1071", name: "Application Layer Protocol", tactic: "Command and Control", detections: 21, severity: "HIGH" },
  { id: "T1105", name: "Ingress Tool Transfer", tactic: "Command and Control", detections: 4, severity: "MEDIUM" },
  { id: "T1572", name: "Protocol Tunneling", tactic: "Command and Control", detections: 0, severity: "NONE" },

  // Exfiltration
  { id: "T1041", name: "Exfiltration Over C2 Channel", tactic: "Exfiltration", detections: 2, severity: "LOW" },
  { id: "T1052", name: "Exfiltration Over Physical Medium", tactic: "Exfiltration", detections: 11, severity: "HIGH" },

  // Impact
  { id: "T1486", name: "Data Encrypted for Impact", tactic: "Impact", detections: 0, severity: "NONE" },
  { id: "T1489", name: "Service Stop", tactic: "Impact", detections: 5, severity: "MEDIUM" },
  { id: "T1529", name: "System Shutdown/Reboot", tactic: "Impact", detections: 3, severity: "LOW" },
];
