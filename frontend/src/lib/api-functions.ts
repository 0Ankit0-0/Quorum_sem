import { apiClient } from "./api";

// Types
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

// API Functions
export const getUploadedFiles = async (): Promise<UploadedFilesResponse> => {
  const response = await apiClient.get<UploadedFilesResponse>("/logs/uploaded-files");
  return response.data;
};

export const runAnalysis = async (request: AnalysisRequest) => {
  const response = await apiClient.post("/analysis/run", request);
  return response.data;
};
