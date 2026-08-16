export interface Citation {
  chunk_id: string;
  spec_number: string;
  release: number;
  version: string;
  section_number?: string;
  section_title?: string;
  page_start?: number;
  excerpt: string;
}

export interface Claim {
  text: string;
  source_ids: string[];
}

export type Confidence = "HIGH" | "MEDIUM" | "LOW" | "ABSTAIN";

export interface ResponseMetadata {
  request_id: string;
  retrieval_ms: number;
  reranker_ms: number;
  llm_ms: number;
  total_ms: number;
  first_token_ms: number;
}

export type MessageType = 'answer' | 'fast_reply' | 'decline' | 'clarify' | 'error' | 'abstain';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  messageType?: MessageType;
  specFilter?: string | null;
  releaseFilter?: number | null;
  claims?: Claim[];
  citations?: Citation[];
  confidence?: Confidence;
  metadata?: ResponseMetadata;
  isStreaming?: boolean;
  error?: string;
  abstained?: boolean;
}

export interface ConversationHistory {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatState {
  chatId: string;
  messages: Message[];
  isStreaming: boolean;
  status: string | null;
}

export interface StreamCallbacks {
  onStatus: (stage: string, message: string) => void;
  onToken: (text: string) => void;
  onCitations: (claims: Claim[], citations: Citation[], confidence: Confidence, abstained: boolean) => void;
  onMetadata: (metadata: ResponseMetadata) => void;
  onAbstain: (reason: string, confidence: Confidence) => void;
  onError: (message: string) => void;
  onFastReply: (message: string) => void;
  onDecline: (message: string) => void;
  onClarify: (message: string) => void;
  onDone: () => void;
}
