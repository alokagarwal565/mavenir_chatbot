import { useCallback } from 'react';
import { ConversationHistory, StreamCallbacks } from '../types/chat';

export function useStreamingQuery() {
  const streamQuery = useCallback(async (
    query: string,
    history: ConversationHistory[],
    specFilter: string | undefined,
    releaseFilter: number,
    callbacks: StreamCallbacks,
    signal: AbortSignal,
  ) => {
    try {
      const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:7860';
      const res = await fetch(`${API_BASE_URL}/api/v1/query/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: query,
          conversation_history: history,
          spec_filter: specFilter || null,
          release_filter: releaseFilter
        }),
        signal,
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData?.detail?.message || `HTTP ${res.status}`);
      }

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        
        // Parse SSE buffer
        let newlineIndex;
        while ((newlineIndex = buffer.indexOf('\n\n')) !== -1) {
          const chunk = buffer.slice(0, newlineIndex);
          buffer = buffer.slice(newlineIndex + 2);
          
          if (!chunk.trim()) continue;
          
          const lines = chunk.split('\n');
          let eventType = 'message';
          let eventData = '';
          
          for (const line of lines) {
            if (line.startsWith('event:')) {
              eventType = line.slice(6).trim();
            } else if (line.startsWith('data:')) {
              eventData = line.slice(5).trim();
            }
          }
          
          if (eventData) {
            try {
              const data = JSON.parse(eventData);
              switch (eventType) {
                case 'status':
                  callbacks.onStatus(data.stage, data.message || '');
                  break;
                case 'token':
                  callbacks.onToken(data.text);
                  break;
                case 'citations':
                  callbacks.onCitations(data.claims || [], data.sources || [], data.confidence, data.abstained);
                  break;
                case 'metadata':
                  callbacks.onMetadata(data);
                  break;
                case 'abstain':
                  callbacks.onAbstain(data.reason, data.confidence);
                  break;
                case 'fast_path':
                  callbacks.onFastReply(data.message || '');
                  break;
                case 'decline':
                  callbacks.onDecline(data.message || '');
                  break;
                case 'clarify':
                  callbacks.onClarify(data.message || '');
                  break;
                case 'error':
                  callbacks.onError(data.message);
                  break;
                case 'done':
                  callbacks.onDone();
                  return;
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e, eventData);
            }
          }
        }
      }
      // Trigger done if stream ends naturally without done event
      callbacks.onDone();
      
    } catch (err: any) {
      if (err.name === 'AbortError') {
        console.log('Stream aborted');
        return; // Aborted streams aren't errors for the UI
      }
      callbacks.onError(err.message || 'Network error');
      callbacks.onDone();
    }
  }, []);

  return { streamQuery };
}
