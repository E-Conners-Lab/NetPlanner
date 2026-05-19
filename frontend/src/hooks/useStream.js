import { useState, useCallback, useRef, useEffect } from 'react';

/**
 * useStream — manages an SSE-style streaming conversation with the Advisor endpoint.
 *
 * Endpoint: POST /api/projects/{projectId}/advisor
 * Request:  { message: string, conversation_id: string | null }
 * Events:   { type: "token", content: string }
 *           { type: "done",  conversation_id: string | null }
 *           { type: "error", content: string }
 *
 * @param {string|undefined} projectId
 * @returns {{ messages, streaming, error, sendMessage, reset }}
 */
export default function useStream(projectId) {
  const [messages, setMessages] = useState([]);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState(null);

  // Persisted across turns; null until the first done event sets it.
  const conversationIdRef = useRef(null);
  const abortRef = useRef(null);

  /** Cancel any in-flight stream. */
  const cancel = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setStreaming(false);
  }, []);

  /**
   * Send a user message and stream the assistant response.
   * @param {string} text
   */
  const sendMessage = useCallback(
    async (text) => {
      const trimmed = (text ?? '').trim();
      if (!trimmed || !projectId) return;

      // If a stream is already running, abort it first.
      if (abortRef.current) {
        abortRef.current.abort();
        abortRef.current = null;
      }

      setError(null);
      setStreaming(true);

      // Append the user turn + an empty assistant placeholder (immutably).
      setMessages((prev) => [
        ...prev,
        { role: 'user', content: trimmed },
        { role: 'assistant', content: '' },
      ]);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const apiBase = import.meta.env.VITE_API_URL || '/api';
        const url = `${apiBase}/projects/${projectId}/advisor`;

        const response = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: trimmed,
            conversation_id: conversationIdRef.current,
          }),
          signal: controller.signal,
        });

        if (!response.ok) {
          // Try to read a detail message from the body before throwing.
          let detail = `Request failed: ${response.status}`;
          try {
            const body = await response.json();
            if (body?.detail) detail = body.detail;
            else if (body?.message) detail = body.message;
          } catch {
            // body not JSON — use the status-based message
          }
          throw new Error(detail);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // SSE events are separated by double newline.
          const parts = buffer.split('\n\n');
          // Keep the last (possibly incomplete) chunk in the buffer.
          buffer = parts.pop() ?? '';

          for (const part of parts) {
            // Each event block may have multiple lines; find the data line.
            const dataLine = part
              .split('\n')
              .find((l) => l.startsWith('data:'));

            if (!dataLine) continue;

            const raw = dataLine.slice('data:'.length).trim();
            if (!raw) continue;

            let event;
            try {
              event = JSON.parse(raw);
            } catch {
              // Malformed JSON — skip this chunk.
              continue;
            }

            if (event.type === 'token') {
              // Immutably append token content to the last assistant message.
              setMessages((prev) => {
                const updated = [...prev];
                const last = { ...updated[updated.length - 1] };
                last.content = last.content + event.content;
                updated[updated.length - 1] = last;
                return updated;
              });
            } else if (event.type === 'done') {
              conversationIdRef.current = event.conversation_id ?? null;
            } else if (event.type === 'error') {
              setError(event.content || 'The advisor returned an error.');
            }
          }
        }
      } catch (err) {
        if (err.name === 'AbortError') return;
        setError(err.message || 'Connection failed. Please try again.');
        // Remove the empty assistant placeholder that was added optimistically.
        setMessages((prev) => {
          if (
            prev.length >= 1 &&
            prev[prev.length - 1].role === 'assistant' &&
            prev[prev.length - 1].content === ''
          ) {
            return prev.slice(0, -1);
          }
          return prev;
        });
      } finally {
        if (abortRef.current === controller) {
          abortRef.current = null;
        }
        setStreaming(false);
      }
    },
    [projectId]
  );

  /** Clear messages and reset conversation state. */
  const reset = useCallback(() => {
    cancel();
    conversationIdRef.current = null;
    setMessages([]);
    setError(null);
  }, [cancel]);

  /** Dismiss the current error message. */
  const clearError = useCallback(() => setError(null), []);

  // Abort any in-flight stream on unmount.
  useEffect(() => {
    return () => {
      if (abortRef.current) abortRef.current.abort();
    };
  }, []);

  return { messages, streaming, error, sendMessage, reset, clearError };
}
