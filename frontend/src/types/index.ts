export interface IntermediateStep {
  tool: string;
  input: string;
  output: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  steps?: IntermediateStep[];
  error?: string;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
}

export interface ChatResponse {
  answer: string;
  session_id: string;
  intermediate_steps: IntermediateStep[];
  error?: string;
}

export interface DocumentIndexRequest {
  url: string;
  description?: string;
}

export interface DocumentIndexResponse {
  success: boolean;
  message: string;
  index_id?: string;
}

export interface AgentStatusResponse {
  agent_ready: boolean;
  index_id?: string;
  agent_id?: string;
  message: string;
}
