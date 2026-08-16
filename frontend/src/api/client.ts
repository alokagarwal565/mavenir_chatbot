import { QueryRequest, QueryResponse, DocumentItem, HealthResponse } from '../types/api';

const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:7860';

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function checkHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE_URL}/health`);
  if (!res.ok) {
    throw new ApiError(res.status, 'HEALTH_CHECK_FAILED', 'Health check failed');
  }
  return res.json();
}

export async function submitQuery(req: QueryRequest): Promise<QueryResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Request-ID': typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `req-${Date.now()}`
    },
    body: JSON.stringify(req)
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new ApiError(
      res.status,
      errorData.error_code || 'QUERY_FAILED',
      errorData.message || 'Failed to process query'
    );
  }

  return res.json();
}

export async function getDocuments(): Promise<DocumentItem[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/documents`);
  if (!res.ok) {
    throw new ApiError(res.status, 'DOCUMENTS_FAILED', 'Failed to fetch documents');
  }
  return res.json();
}
