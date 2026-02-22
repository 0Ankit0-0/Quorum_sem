import { apiClient } from "./api";

export interface UploadedFile {
  filename: string;
  size_bytes: number;
  uploaded_at: string;
  path: string;
}

export interface UploadedFilesResponse {
  files: UploadedFile[];
  count: number;
}

export interface AnalysisRequest {
  algorithm: string;
  threshold: number;
  log_source?: string;
  start_time?: string;
  end_time?: string;
}

export type SeverityLevel = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export interface SystemStatusData {
  total_logs: number;
  total_anomalies: number;
  active_sessions: number;
  environment: string;
  nodes_online: number;
  uptime_hours: number;
  last_analysis: string;
}

export interface SeverityDistributionItem {
  severity: SeverityLevel;
  count: number;
  fill: string;
}

export interface TimelineDataPoint {
  time: string;
  anomalies: number;
  critical: number;
}

export interface AnomalyData {
  id: string;
  timestamp: string;
  severity: SeverityLevel;
  message: string;
  source: string;
  algorithm: string;
  score: number;
  mitre_id: string;
  mitre_tactic: string;
}

export interface LogData {
  id: string;
  timestamp: string;
  severity: SeverityLevel;
  source: string;
  message: string;
  entries: number;
}

export interface UsbDeviceData {
  id: string;
  name: string;
  vid: string;
  pid: string;
  type: string;
  risk: SeverityLevel;
  inserted_at: string;
  is_new: boolean;
}

export interface LanDeviceData {
  id: string;
  ip: string;
  hostname: string;
  mac: string;
  os: string;
  status: "ONLINE" | "OFFLINE";
  risk: SeverityLevel;
}

export interface DevicesData {
  usb: UsbDeviceData[];
  lan: LanDeviceData[];
}

export interface SessionData {
  id: string;
  algorithm: string;
  threshold: number;
  total_logs: number;
  anomalies_found: number;
  duration_seconds: number;
  created_at: string;
  status: string;
}

export interface NodeData {
  id: string;
  hostname: string;
  role: string;
  status: "ONLINE" | "OFFLINE";
  total_logs: number;
  anomalies: number;
  last_sync: string;
}

export interface CorrelationData {
  id: string;
  mitre_id: string;
  tactic: string;
  technique: string;
  affected_nodes: string[];
  node_count: number;
  total_events: number;
  severity: SeverityLevel;
}

export interface StreamLogData {
  id: number;
  time: string;
  severity: SeverityLevel;
  score: number;
  source: string;
  message: string;
}

export interface ReportData {
  id: string;
  type: "PDF" | "CSV";
  session_id: string;
  name: string;
  size_kb: number;
  created_at: string;
}

export interface MitreTechniqueData {
  id: string;
  name: string;
  tactic: string;
  detections: number;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "NONE";
}

export interface MitreSummaryData {
  tactics: string[];
  techniques: MitreTechniqueData[];
  total_detections: number;
}

export interface LogIngestResult {
  filename?: string;
  entries_inserted: number;
  parse_errors: number;
  insert_errors: number;
  duration_seconds: number;
}

export interface ReportGenerationResult {
  status: string;
  report_type: string;
  report_path: string;
  filename: string;
}

export interface HubNodeRegistration {
  node_id: string;
  hostname: string;
  role: string;
  status: string;
}

export interface RootInfo {
  name: string;
  version: string;
  status: string;
  docs: string;
}

export interface HubInfo {
  node_id: string;
  hostname: string;
  role: string;
  status: string;
}

const SEVERITY_COLORS: Record<SeverityLevel, string> = {
  CRITICAL: "#ef4444",
  HIGH: "#f97316",
  MEDIUM: "#eab308",
  LOW: "#22c55e",
};

const normalizeSeverity = (value: unknown): SeverityLevel => {
  const normalized = String(value ?? "")
    .toUpperCase()
    .trim();
  if (normalized === "CRITICAL") return "CRITICAL";
  if (normalized === "HIGH") return "HIGH";
  if (normalized === "MEDIUM") return "MEDIUM";
  return "LOW";
};

const toIsoString = (value: unknown): string => {
  if (!value) return new Date().toISOString();
  const date = new Date(String(value));
  if (Number.isNaN(date.getTime())) return new Date().toISOString();
  return date.toISOString();
};

const shortSource = (source: string): string => {
  const upper = source.toUpperCase();
  if (upper.includes("WORKSTATION")) return "WKST";
  if (upper.includes("SERVER")) return "SRV";
  return source.slice(0, 4).toUpperCase();
};

interface BackendSystemStatus {
  total_logs?: number;
  total_anomalies?: number;
  environment_type?: string;
  uptime_seconds?: number;
}

interface BackendSession {
  id?: string;
  session_id?: string;
  algorithm?: string;
  threshold?: number;
  total_logs?: number;
  logs_analyzed?: number;
  anomalies_found?: number;
  anomalies_detected?: number;
  duration_seconds?: number;
  created_at?: string;
  start_time?: string;
  status?: string;
}

interface BackendAnomaly {
  id?: number | string;
  anomaly_score?: number;
  severity?: string;
  explanation?: string;
  message?: string;
  source?: string;
  algorithm?: string;
  mitre_technique_id?: string;
  mitre_tactic?: string;
  detected_at?: string;
  timestamp?: string;
}

interface BackendLog {
  id?: number | string;
  timestamp?: string;
  severity?: string;
  source?: string;
  message?: string;
  entries?: number;
  anomaly_score?: number;
}

const mapTimelineFromAnomalies = (
  anomalies: BackendAnomaly[],
): TimelineDataPoint[] => {
  const now = new Date();
  const points: TimelineDataPoint[] = [];

  for (let hoursAgo = 22; hoursAgo >= 0; hoursAgo -= 2) {
    const start = new Date(now);
    start.setMinutes(0, 0, 0);
    start.setHours(start.getHours() - hoursAgo);
    const end = new Date(start);
    end.setHours(end.getHours() + 2);

    const windowAnomalies = anomalies.filter((item) => {
      const ts = new Date(toIsoString(item.detected_at ?? item.timestamp));
      return ts >= start && ts < end;
    });

    points.push({
      time: `${String(start.getHours()).padStart(2, "0")}:00`,
      anomalies: windowAnomalies.length,
      critical: windowAnomalies.filter(
        (item) => normalizeSeverity(item.severity) === "CRITICAL",
      ).length,
    });
  }

  return points;
};

export const getUploadedFiles = async (): Promise<UploadedFilesResponse> => {
  const response = await apiClient.get<UploadedFilesResponse>("/logs/uploaded-files");
  return response.data;
};

export const runAnalysis = async (request: AnalysisRequest) => {
  const response = await apiClient.post("/analysis/run", request);
  return response.data;
};

export const uploadLogFile = async (
  file: File,
  sourceType?: string,
  onProgress?: (pct: number) => void,
): Promise<LogIngestResult> => {
  const form = new FormData();
  form.append("file", file);
  if (sourceType) {
    form.append("source_type", sourceType);
  }

  const response = await apiClient.post("/logs/ingest", form, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (event) => {
      if (!event.total || !onProgress) return;
      onProgress(Math.round((event.loaded / event.total) * 100));
    },
  });

  return response.data;
};

export const getSystemStatus = async (): Promise<SystemStatusData> => {
  const [statusRes, sessionsRes, nodesRes] = await Promise.allSettled([
    apiClient.get<BackendSystemStatus>("/system/status"),
    apiClient.get<{ sessions: BackendSession[] }>("/analysis/sessions", {
      params: { limit: 100 },
    }),
    apiClient.get<{ nodes: Array<{ status?: string }> }>("/hub/nodes"),
  ]);

  const statusData =
    statusRes.status === "fulfilled" ? statusRes.value.data : {};
  const sessions =
    sessionsRes.status === "fulfilled"
      ? sessionsRes.value.data.sessions ?? []
      : [];
  const nodes =
    nodesRes.status === "fulfilled" ? nodesRes.value.data.nodes ?? [] : [];

  const latestSession = sessions[0];
  const nodesOnline = nodes.filter((n) =>
    String(n.status ?? "").toLowerCase().includes("active"),
  ).length;

  return {
    total_logs: Number(statusData.total_logs ?? 0),
    total_anomalies: Number(statusData.total_anomalies ?? 0),
    active_sessions: sessions.length,
    environment: String(statusData.environment_type ?? "AIR-GAPPED")
      .replaceAll("_", "-")
      .toUpperCase(),
    nodes_online: nodesOnline,
    uptime_hours: Math.floor(Number(statusData.uptime_seconds ?? 0) / 3600),
    last_analysis: toIsoString(
      latestSession?.created_at ??
        latestSession?.start_time ??
        new Date().toISOString(),
    ),
  };
};

export const getSeverityDistribution = async (): Promise<
  SeverityDistributionItem[]
> => {
  try {
    const response = await apiClient.get<{ distribution: Record<string, number> }>(
      "/analysis/severity-distribution",
    );
    const distribution = response.data.distribution ?? {};
    return (["CRITICAL", "HIGH", "MEDIUM", "LOW"] as SeverityLevel[]).map(
      (severity) => ({
        severity,
        count: Number(distribution[severity] ?? 0),
        fill: SEVERITY_COLORS[severity],
      }),
    );
  } catch {
    const anomalies = await getAnomalies(500);
    const counts: Record<SeverityLevel, number> = {
      CRITICAL: 0,
      HIGH: 0,
      MEDIUM: 0,
      LOW: 0,
    };
    for (const anomaly of anomalies) {
      counts[anomaly.severity] += 1;
    }
    return (["CRITICAL", "HIGH", "MEDIUM", "LOW"] as SeverityLevel[]).map(
      (severity) => ({
        severity,
        count: counts[severity],
        fill: SEVERITY_COLORS[severity],
      }),
    );
  }
};

export const getTimelineData = async (): Promise<TimelineDataPoint[]> => {
  try {
    const response = await apiClient.get<{ timeline: TimelineDataPoint[] }>(
      "/analysis/timeline",
    );
    return (response.data.timeline ?? []).map((point) => ({
      time: String(point.time),
      anomalies: Number(point.anomalies ?? 0),
      critical: Number(point.critical ?? 0),
    }));
  } catch {
    const response = await apiClient.get<{ anomalies: BackendAnomaly[] }>(
      "/analysis/anomalies",
      { params: { limit: 500 } },
    );
    return mapTimelineFromAnomalies(response.data.anomalies ?? []);
  }
};

export const getAnomalies = async (limit = 10): Promise<AnomalyData[]> => {
  const response = await apiClient.get<{ anomalies: BackendAnomaly[] }>(
    "/analysis/anomalies",
    { params: { limit } },
  );
  return (response.data.anomalies ?? []).map((item, index) => ({
    id: `ANM-${String(item.id ?? index + 1).padStart(3, "0")}`,
    timestamp: toIsoString(item.detected_at ?? item.timestamp),
    severity: normalizeSeverity(item.severity),
    message: String(item.explanation ?? item.message ?? "No details provided"),
    source: String(item.source ?? "UNKNOWN"),
    algorithm: String(item.algorithm ?? "statistical"),
    score: Number(item.anomaly_score ?? 0),
    mitre_id: String(item.mitre_technique_id ?? "T0000"),
    mitre_tactic: String(item.mitre_tactic ?? "Unknown"),
  }));
};

export const getLogs = async (limit = 50): Promise<LogData[]> => {
  const response = await apiClient.get<BackendLog[]>("/logs/recent", {
    params: { limit },
  });
  return (response.data ?? []).map((item, index) => ({
    id: `LOG-${String(item.id ?? index + 1).padStart(4, "0")}`,
    timestamp: toIsoString(item.timestamp),
    severity: normalizeSeverity(item.severity),
    source: String(item.source ?? "unknown.log"),
    message: String(item.message ?? ""),
    entries: Number(item.entries ?? 1),
  }));
};

export const getSessions = async (limit = 20): Promise<SessionData[]> => {
  const response = await apiClient.get<{ sessions: BackendSession[] }>(
    "/analysis/sessions",
    { params: { limit } },
  );
  return (response.data.sessions ?? []).map((item, index) => ({
    id: String(item.id ?? item.session_id ?? `SES-${index + 1}`),
    algorithm: String(item.algorithm ?? "statistical"),
    threshold: Number(item.threshold ?? 0.7),
    total_logs: Number(item.total_logs ?? item.logs_analyzed ?? 0),
    anomalies_found: Number(item.anomalies_found ?? item.anomalies_detected ?? 0),
    duration_seconds: Number(item.duration_seconds ?? 0),
    created_at: toIsoString(item.created_at ?? item.start_time),
    status: String(item.status ?? "COMPLETED").toUpperCase(),
  }));
};

export const getDevices = async (): Promise<DevicesData> => {
  const response = await apiClient.get<{
    usb_devices?: Array<{
      device_id?: string;
      name?: string;
      vendor_id?: string;
      product_id?: string;
      device_class?: string;
      risk_level?: string;
      connected_at?: string;
      is_new?: boolean;
    }>;
    lan_nodes?: Array<{
      device_id?: string;
      ip_address?: string;
      hostname?: string;
      mac_address?: string;
      os_info?: string;
      status?: string;
      risk_level?: string;
    }>;
  }>("/devices/scan", { params: { include_lan: true } });

  return {
    usb: (response.data.usb_devices ?? []).map((item, index) => ({
      id: String(item.device_id ?? `USB-${String(index + 1).padStart(3, "0")}`),
      name: String(item.name ?? "Unknown Device"),
      vid: String(item.vendor_id ?? "0000"),
      pid: String(item.product_id ?? "0000"),
      type: String(item.device_class ?? "UNKNOWN").replaceAll("_", " "),
      risk: normalizeSeverity(item.risk_level),
      inserted_at: toIsoString(item.connected_at),
      is_new: Boolean(item.is_new),
    })),
    lan: (response.data.lan_nodes ?? []).map((item, index) => ({
      id: String(item.device_id ?? `LAN-${String(index + 1).padStart(3, "0")}`),
      ip: String(item.ip_address ?? "0.0.0.0"),
      hostname: String(item.hostname ?? "UNKNOWN"),
      mac: String(item.mac_address ?? "unknown"),
      os: String(item.os_info ?? "UNKNOWN"),
      status: String(item.status ?? "").toLowerCase().includes("active")
        ? "ONLINE"
        : "OFFLINE",
      risk: normalizeSeverity(item.risk_level),
    })),
  };
};

export const getNodes = async (): Promise<NodeData[]> => {
  const response = await apiClient.get<{
    nodes: Array<{
      node_id?: string;
      hostname?: string;
      role?: string;
      status?: string;
      total_logs?: number;
      total_anomalies?: number;
      last_sync?: string;
      last_seen?: string;
    }>;
  }>("/hub/nodes");

  return (response.data.nodes ?? []).map((node) => ({
    id: String(node.node_id ?? "NODE-UNKNOWN"),
    hostname: String(node.hostname ?? "UNKNOWN"),
    role: String(node.role ?? "terminal"),
    status: String(node.status ?? "").toLowerCase().includes("active")
      ? "ONLINE"
      : "OFFLINE",
    total_logs: Number(node.total_logs ?? 0),
    anomalies: Number(node.total_anomalies ?? 0),
    last_sync: toIsoString(node.last_sync ?? node.last_seen),
  }));
};

export const getCorrelations = async (): Promise<CorrelationData[]> => {
  const response = await apiClient.get<{
    correlations: Array<{
      mitre_technique_id?: string;
      mitre_tactic?: string;
      node_count?: number;
      total_hits?: number;
      affected_nodes?: string;
      threat_level?: string;
    }>;
  }>("/hub/correlations");

  return (response.data.correlations ?? []).map((item, index) => ({
    id: `COR-${String(index + 1).padStart(3, "0")}`,
    mitre_id: String(item.mitre_technique_id ?? "T0000"),
    tactic: String(item.mitre_tactic ?? "Unknown"),
    technique: String(item.mitre_technique_id ?? "Unknown Technique"),
    affected_nodes: String(item.affected_nodes ?? "")
      .split(",")
      .filter(Boolean),
    node_count: Number(item.node_count ?? 0),
    total_events: Number(item.total_hits ?? 0),
    severity: normalizeSeverity(item.threat_level),
  }));
};

export const getStreamLogs = async (limit = 8): Promise<StreamLogData[]> => {
  const response = await apiClient.get<BackendLog[]>("/logs/recent", {
    params: { limit },
  });

  return (response.data ?? []).map((item, index) => {
    const timestamp = new Date(toIsoString(item.timestamp));
    const severity = normalizeSeverity(item.severity);
    const inferredScore =
      severity === "CRITICAL"
        ? 0.95
        : severity === "HIGH"
          ? 0.82
          : severity === "MEDIUM"
            ? 0.66
            : 0.42;

    return {
      id: index + 1,
      time: timestamp.toLocaleTimeString("en-US", {
        hour12: false,
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        fractionalSecondDigits: 3,
      }),
      severity,
      score: Number(item.anomaly_score ?? inferredScore),
      source: shortSource(String(item.source ?? "SRC")) + "-01",
      message: String(item.message ?? ""),
    };
  });
};

export const getReports = async (): Promise<ReportData[]> => {
  const response = await apiClient.get<{
    reports: Array<{
      filename?: string;
      path?: string;
      size_mb?: number;
      created?: number | string;
    }>;
  }>("/reports/list");

  return (response.data.reports ?? []).map((item, index) => {
    const filename = String(item.filename ?? `report_${index + 1}.pdf`);
    const ext = filename.split(".").pop()?.toUpperCase();
    const reportType: "PDF" | "CSV" = ext === "CSV" ? "CSV" : "PDF";
    const sessionMatch = String(item.path ?? "").match(/[0-9a-fA-F-]{16,36}/);
    const createdRaw =
      typeof item.created === "number"
        ? new Date(item.created * 1000).toISOString()
        : item.created;

    return {
      id: `RPT-${String(index + 1).padStart(3, "0")}`,
      type: reportType,
      session_id: sessionMatch?.[0] ?? "N/A",
      name: filename,
      size_kb: Math.round(Number(item.size_mb ?? 0) * 1024),
      created_at: toIsoString(createdRaw),
    };
  });
};

export const generateReport = async (
  reportType: "PDF" | "CSV",
  sessionId?: string,
): Promise<ReportGenerationResult> => {
  const response = await apiClient.post<ReportGenerationResult>(
    "/reports/generate",
    {
      report_type: reportType.toLowerCase(),
      session_id: sessionId || null,
      include_graphs: reportType === "PDF",
    },
  );
  return response.data;
};

export const downloadReport = async (filename: string): Promise<Blob> => {
  const response = await apiClient.get(`/reports/${encodeURIComponent(filename)}`, {
    responseType: "blob",
  });
  return response.data;
};

export const scanDevices = async (): Promise<DevicesData> => getDevices();

export const registerNode = async (role = "terminal"): Promise<HubNodeRegistration> => {
  const response = await apiClient.post<HubNodeRegistration>(
    "/hub/nodes/register",
    null,
    { params: { role } },
  );
  return response.data;
};

export const exportSyncPackage = async (
  targetNode = "hub",
  sign = true,
): Promise<{ filename: string; blob: Blob }> => {
  const response = await apiClient.post("/hub/export", null, {
    params: { target_node: targetNode, sign },
    responseType: "blob",
  });

  const disposition = String(response.headers["content-disposition"] ?? "");
  const match = disposition.match(/filename="?([^"]+)"?/i);
  const filename = match?.[1] ?? `sync_${Date.now()}.qsp`;
  return { filename, blob: response.data };
};

export const getRootInfo = async (): Promise<RootInfo> => {
  const response = await apiClient.get<RootInfo>("/");
  return response.data;
};

export const getHubInfo = async (): Promise<HubInfo> => {
  const response = await apiClient.get<HubInfo>("/hub/info");
  return response.data;
};

export const startRealtimeMonitor = async (): Promise<{ status: string }> => {
  const response = await apiClient.post<{ status: string }>("/stream/start");
  return response.data;
};

export const stopRealtimeMonitor = async (): Promise<{ status: string }> => {
  const response = await apiClient.post<{ status: string }>("/stream/stop");
  return response.data;
};

export const getMitreTechniques = async (): Promise<MitreSummaryData> => {
  const response = await apiClient.get<{
    tactics?: string[];
    techniques?: Array<{
      id?: string;
      name?: string;
      tactic?: string;
      detections?: number;
      severity?: string;
    }>;
    total_detections?: number;
  }>("/analysis/mitre-techniques");

  const techniques: MitreTechniqueData[] = (response.data.techniques ?? []).map(
    (t) => ({
      id: String(t.id ?? ""),
      name: String(t.name ?? "Unknown"),
      tactic: String(t.tactic ?? "Unknown"),
      detections: Number(t.detections ?? 0),
      severity:
        t.severity === "CRITICAL" ||
        t.severity === "HIGH" ||
        t.severity === "MEDIUM" ||
        t.severity === "LOW"
          ? t.severity
          : "NONE",
    }),
  );

  return {
    tactics: response.data.tactics ?? [],
    techniques,
    total_detections:
      Number(response.data.total_detections ?? 0) ||
      techniques.reduce((sum, t) => sum + t.detections, 0),
  };
};
