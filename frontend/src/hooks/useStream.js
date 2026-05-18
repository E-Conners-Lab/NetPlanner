import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Stub hook for Server-Sent Events (SSE) streaming from the AI Advisor endpoint.
 *
 * Architecture notes (to be wired in Phase-1):
 *   - The backend exposes a streaming endpoint at POST /api/advisor/{projectId}/stream
 *   - The frontend uses fetch() with a ReadableStream reader rather than EventSource
 *     because EventSource only supports GET and cannot carry a request body.
 *   - Each SSE chunk is a JSON line:  {"type":"token","content":"..."}
 *                                     {"type":"done","content":""}
 *                                     {"type":"error","content":"message"}
 *
 * Usage (future):
 *   const { messages, streaming, start, stop } = useStream(projectId);
 *   start({ prompt: 'What is the best vendor for a 10GbE spine?' });
 *
 * @param {string|undefined} projectId
 */
export default function useStream(projectId) {
  const [messages, setMessages] = useState([]);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState(null);

  // Holds a reference to the AbortController so we can cancel mid-stream
  const abortRef = useRef(null);

  /** Cancel an in-progress stream */
  const stop = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setStreaming(false);
  }, []);

  /**
   * Start a streaming request to the Advisor endpoint.
   * @param {{ prompt: string }} payload
   */
  const start = useCallback(
    async (payload) => {
      if (!projectId) return;
      if (streaming) stop();

      setError(null);
      setStreaming(true);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const apiBase = import.meta.env.VITE_API_URL || '/api';
        const response = await fetch(
          `${apiBase}/advisor/${projectId}/stream`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            signal: controller.signal,
          }
        );

        if (!response.ok) {
          throw new Error(`Stream request failed: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        // Append assistant message placeholder
        setMessages((prev) => [
          ...prev,
          { role: 'user', content: payload.prompt },
          { role: 'assistant', content: '' },
        ]);

        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop(); // keep incomplete last line in buffer

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || !trimmed.startsWith('data:')) continue;

            const raw = trimmed.slice(5).trim();
            if (raw === '[DONE]') break;

            try {
              const chunk = JSON.parse(raw);
              if (chunk.type === 'token') {
                setMessages((prev) => {
                  const updated = [...prev];
                  const last = { ...updated[updated.length - 1] };
                  last.content += chunk.content;
                  updated[updated.length - 1] = last;
                  return updated;
                });
              }
            } catch {
              // Malformed chunk — skip silently
            }
          }
        }
      } catch (err) {
        if (err.name !== 'AbortError') {
          setError(err.message || 'Stream error');
        }
      } finally {
        setStreaming(false);
        abortRef.current = null;
      }
    },
    [projectId, streaming, stop]
  );

  /** Clear message history */
  const clear = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (abortRef.current) abortRef.current.abort();
    };
  }, []);

  return { messages, streaming, error, start, stop, clear };
}
