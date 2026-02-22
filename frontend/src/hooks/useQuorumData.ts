import { useCallback, useEffect, useState } from "react";
import {
  getAnomalies,
  getCorrelations,
  getDevices,
  getLogs,
  getNodes,
  getReports,
  getSessions,
  getSeverityDistribution,
  getStreamLogs,
  getSystemStatus,
  getTimelineData,
  type AnomalyData,
  type CorrelationData,
  type DevicesData,
  type LogData,
  type NodeData,
  type ReportData,
  type SessionData,
  type SeverityDistributionItem,
  type StreamLogData,
  type SystemStatusData,
  type TimelineDataPoint,
} from "@/lib/api-functions";

export interface QuorumDataState {
  systemStatus: SystemStatusData;
  severityDistribution: SeverityDistributionItem[];
  timelineData: TimelineDataPoint[];
  anomalies: AnomalyData[];
  logs: LogData[];
  devices: DevicesData;
  sessions: SessionData[];
  nodes: NodeData[];
  correlations: CorrelationData[];
  streamLogs: StreamLogData[];
  reports: ReportData[];
}

const fallbackData: QuorumDataState = {
  systemStatus: {
    total_logs: 0,
    total_anomalies: 0,
    active_sessions: 0,
    environment: "AIR-GAPPED",
    nodes_online: 0,
    uptime_hours: 0,
    last_analysis: new Date().toISOString(),
  } as SystemStatusData,
  severityDistribution: [] as SeverityDistributionItem[],
  timelineData: [] as TimelineDataPoint[],
  anomalies: [] as AnomalyData[],
  logs: [] as LogData[],
  devices: { usb: [], lan: [] } as DevicesData,
  sessions: [] as SessionData[],
  nodes: [] as NodeData[],
  correlations: [] as CorrelationData[],
  streamLogs: [] as StreamLogData[],
  reports: [] as ReportData[],
};

export const useQuorumData = () => {
  const [data, setData] = useState<QuorumDataState>(fallbackData);
  const [loading, setLoading] = useState(true);
  const [isUsingFallback, setIsUsingFallback] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);

    const results = await Promise.allSettled([
      getSystemStatus(),
      getSeverityDistribution(),
      getTimelineData(),
      getAnomalies(10),
      getLogs(50),
      getDevices(),
      getSessions(20),
      getNodes(),
      getCorrelations(),
      getStreamLogs(8),
      getReports(),
    ]);

    const nextData: QuorumDataState = {
      systemStatus:
        results[0].status === "fulfilled"
          ? results[0].value
          : fallbackData.systemStatus,
      severityDistribution:
        results[1].status === "fulfilled"
          ? results[1].value
          : fallbackData.severityDistribution,
      timelineData:
        results[2].status === "fulfilled"
          ? results[2].value
          : fallbackData.timelineData,
      anomalies:
        results[3].status === "fulfilled"
          ? results[3].value
          : fallbackData.anomalies,
      logs: results[4].status === "fulfilled" ? results[4].value : fallbackData.logs,
      devices:
        results[5].status === "fulfilled"
          ? results[5].value
          : fallbackData.devices,
      sessions:
        results[6].status === "fulfilled"
          ? results[6].value
          : fallbackData.sessions,
      nodes: results[7].status === "fulfilled" ? results[7].value : fallbackData.nodes,
      correlations:
        results[8].status === "fulfilled"
          ? results[8].value
          : fallbackData.correlations,
      streamLogs:
        results[9].status === "fulfilled"
          ? results[9].value
          : fallbackData.streamLogs,
      reports:
        results[10].status === "fulfilled"
          ? results[10].value
          : fallbackData.reports,
    };

    const hadFailures = results.some((result) => result.status === "rejected");
    setData(nextData);
    setIsUsingFallback(hadFailures);
    if (hadFailures) {
      setError("One or more API requests failed. Empty fallback data is active.");
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { ...data, loading, error, isUsingFallback, refresh };
};
