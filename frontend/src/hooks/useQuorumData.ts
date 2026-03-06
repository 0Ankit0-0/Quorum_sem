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

const CACHE_TTL_MS = 180_000;

let sharedData: QuorumDataState = fallbackData;
let sharedLoading = false;
let sharedIsUsingFallback = false;
let sharedError: string | null = null;
let sharedLastFetchedAt = 0;
let sharedInFlight: Promise<void> | null = null;

export const useQuorumData = () => {
  const [data, setData] = useState<QuorumDataState>(sharedData);
  const [loading, setLoading] = useState(sharedLoading || sharedLastFetchedAt === 0);
  const [isUsingFallback, setIsUsingFallback] = useState(sharedIsUsingFallback);
  const [error, setError] = useState<string | null>(sharedError);

  const syncFromShared = useCallback(() => {
    setData(sharedData);
    setLoading(sharedLoading);
    setIsUsingFallback(sharedIsUsingFallback);
    setError(sharedError);
  }, []);

  const refresh = useCallback(async (force = true) => {
    const isFresh =
      sharedLastFetchedAt > 0 && Date.now() - sharedLastFetchedAt < CACHE_TTL_MS;

    if (!force && isFresh) {
      syncFromShared();
      return;
    }

    if (sharedInFlight) {
      await sharedInFlight;
      syncFromShared();
      return;
    }

    sharedLoading = true;
    sharedError = null;
    syncFromShared();

    sharedInFlight = (async () => {
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

      sharedData = {
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
        logs:
          results[4].status === "fulfilled" ? results[4].value : fallbackData.logs,
        devices:
          results[5].status === "fulfilled"
            ? results[5].value
            : fallbackData.devices,
        sessions:
          results[6].status === "fulfilled"
            ? results[6].value
            : fallbackData.sessions,
        nodes:
          results[7].status === "fulfilled" ? results[7].value : fallbackData.nodes,
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
      sharedIsUsingFallback = hadFailures;
      sharedError = hadFailures
        ? "One or more API requests failed. Empty fallback data is active."
        : null;
      sharedLastFetchedAt = Date.now();
      sharedLoading = false;
    })().finally(() => {
      sharedInFlight = null;
      sharedLoading = false;
    });

    await sharedInFlight;
    syncFromShared();
  }, [syncFromShared]);

  useEffect(() => {
    void refresh(false);
  }, [refresh]);

  return { ...data, loading, error, isUsingFallback, refresh };
};
