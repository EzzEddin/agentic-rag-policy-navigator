import axios from "axios";
import type {
  ChatRequest,
  ChatResponse,
  DocumentIndexRequest,
  DocumentIndexResponse,
  AgentStatusResponse,
} from "../types";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const api = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 120_000, // Agent calls can take up to 2 minutes
});

export const sendMessage = async (req: ChatRequest): Promise<ChatResponse> => {
  const { data } = await api.post<ChatResponse>("/api/chat", req);
  return data;
};

export const indexUrl = async (
  req: DocumentIndexRequest
): Promise<DocumentIndexResponse> => {
  const { data } = await api.post<DocumentIndexResponse>(
    "/api/documents/index-url",
    req
  );
  return data;
};

export const uploadDocument = async (
  file: File,
  description?: string
): Promise<DocumentIndexResponse> => {
  const form = new FormData();
  form.append("file", file);
  if (description) form.append("description", description);
  const { data } = await api.post<DocumentIndexResponse>(
    "/api/documents/upload",
    form,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return data;
};

export const getAgentStatus = async (): Promise<AgentStatusResponse> => {
  const { data } = await api.get<AgentStatusResponse>("/api/status");
  return data;
};

export interface SearchResult {
  id: string;
  text: string;
  score: number;
  metadata: Record<string, unknown>;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
}

export const searchIndex = async (
  query: string,
  top_k = 5
): Promise<SearchResponse> => {
  const { data } = await api.post<SearchResponse>("/api/documents/search", {
    query,
    top_k,
  });
  return data;
};
