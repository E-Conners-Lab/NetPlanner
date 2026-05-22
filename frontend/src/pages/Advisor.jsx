import { useState, useRef, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import useProject from '../hooks/useProject.js';
import useStream from '../hooks/useStream.js';
import Button from '../components/ui/Button.jsx';
import {
  listConversations,
  getConversationMessages,
} from '../api/reports.js';

/* ── Sub-components ─────────────────────────────────────────── */

/**
 * A single chat bubble.
 * @param {{ message: { role: 'user'|'assistant', content: string } }} props
 */
function MessageBubble({ message }) {
  const isUser = message.role === 'user';

  return (
    <div className={['flex w-full', isUser ? 'justify-end' : 'justify-start'].join(' ')}>
      <div
        className={[
          'max-w-[78%] rounded-2xl px-4 py-3 text-sm leading-relaxed',
          isUser
            ? 'bg-accent/15 text-text border border-accent/20 rounded-br-sm whitespace-pre-wrap'
            : 'bg-surface text-text border border-[var(--border)] rounded-bl-sm',
        ].join(' ')}
      >
        {isUser ? (
          message.content
        ) : message.content ? (
          /* Assistant replies in markdown — render it. react-markdown does not
             execute raw HTML (no rehype-raw), so web-search-derived content
             cannot inject script (AI-1). */
          <div className="advisor-md">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
          </div>
        ) : (
          /* Streaming indicator — shown while the assistant message is still empty */
          <span className="flex items-center gap-1.5 text-textMuted">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-textMuted/60 animate-bounce [animation-delay:0ms]" />
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-textMuted/60 animate-bounce [animation-delay:150ms]" />
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-textMuted/60 animate-bounce [animation-delay:300ms]" />
          </span>
        )}
      </div>
    </div>
  );
}

/**
 * A clickable suggestion chip. Calls `onSelect(text)` when clicked.
 * @param {{ text: string, onSelect: (text: string) => void }} props
 */
function SuggestionChip({ text, onSelect }) {
  return (
    <button
      type="button"
      onClick={() => onSelect(text)}
      className="text-left px-3 py-2.5 rounded-lg bg-surface border border-[var(--border)] hover:border-textMuted/30 hover:bg-surface/80 transition-colors text-xs text-textMuted leading-snug"
    >
      {text}
    </button>
  );
}

/**
 * Empty state shown before the first message is sent.
 * @param {{ onSuggest: (text: string) => void }} props
 */
function EmptyState({ onSuggest }) {
  const prompts = [
    'What is the projected 3-year TCO for this design?',
    'How should I justify this vendor choice to leadership?',
    'What budget trade-offs should I consider?',
    'Are there alternative architectures within my budget?',
  ];

  return (
    <div className="flex flex-col items-center justify-center flex-1 gap-6 py-12 px-4">
      <div className="flex flex-col items-center gap-3 text-center">
        <div className="w-12 h-12 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center">
          <svg
            width="22"
            height="22"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-accent"
            aria-hidden="true"
          >
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        </div>
        <div>
          <h3 className="text-base font-semibold text-text">AI Network Advisor</h3>
          <p className="mt-1 text-sm text-textMuted max-w-sm">
            Ask about TCO, vendor justification, budget framing, or architectural trade-offs.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-xl">
        {prompts.map((prompt) => (
          <SuggestionChip key={prompt} text={prompt} onSelect={onSuggest} />
        ))}
      </div>
    </div>
  );
}

/**
 * Error banner with a dismiss button.
 * @param {{ message: string, onDismiss: () => void }} props
 */
function ErrorBanner({ message, onDismiss }) {
  return (
    <div className="flex items-start gap-3 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/25 text-sm text-red-400">
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="flex-shrink-0 mt-0.5"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>
      <span className="flex-1">{message}</span>
      <button
        type="button"
        onClick={onDismiss}
        aria-label="Dismiss error"
        className="flex-shrink-0 text-red-400/60 hover:text-red-400 transition-colors"
      >
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </div>
  );
}

/* ── Main page ──────────────────────────────────────────────── */

export default function Advisor() {
  const { id: projectId } = useParams();
  const { project, loading: projectLoading } = useProject(projectId);

  const {
    messages,
    streaming,
    error,
    sendMessage,
    reset,
    clearError,
    loadConversation,
  } = useStream(projectId);

  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef(null);

  // Past conversations for this project — surfaced as compact chips so the
  // user can continue a previous session rather than always starting fresh.
  const [pastConversations, setPastConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);

  const refreshPastConversations = useCallback(async () => {
    if (!projectId) return;
    try {
      const response = await listConversations(projectId);
      setPastConversations(response.data ?? []);
    } catch {
      // Soft fail — the picker just won't render. The Advisor still works
      // for new conversations.
    }
  }, [projectId]);

  useEffect(() => {
    refreshPastConversations();
  }, [refreshPastConversations]);

  const handleLoadConversation = useCallback(
    async (conversationId) => {
      if (!projectId || streaming) return;
      try {
        const response = await getConversationMessages(projectId, conversationId);
        loadConversation(conversationId, response.data ?? []);
        setActiveConversationId(conversationId);
        setInputValue('');
      } catch {
        // Soft fail — user can start a new one.
      }
    },
    [projectId, streaming, loadConversation],
  );

  // Auto-scroll to the bottom whenever messages change or a token arrives.
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = useCallback(() => {
    const trimmed = inputValue.trim();
    if (!trimmed || streaming) return;
    setInputValue('');
    sendMessage(trimmed);
  }, [inputValue, streaming, sendMessage]);

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  const handleReset = useCallback(() => {
    reset();
    setInputValue('');
    setActiveConversationId(null);
    // A new send creates a new conversation row; refresh the chip list
    // afterwards so it surfaces in the picker.
    refreshPastConversations();
  }, [reset, refreshPastConversations]);

  const hasMessages = messages.length > 0;
  const canSend = inputValue.trim().length > 0 && !streaming;

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto gap-0">
      {/* ── Header ───────────────────────────────────────────── */}
      <div className="flex items-center justify-between pb-4 flex-shrink-0">
        <div>
          <h1 className="text-2xl font-semibold text-text">AI Advisor</h1>
          <p className="mt-0.5 text-sm text-textMuted">
            {projectLoading
              ? 'Loading project…'
              : project
                ? project.name
                : `Project ${projectId}`}
          </p>
        </div>

        {hasMessages && (
          <Button variant="secondary" onClick={handleReset} className="text-xs px-3 py-1.5">
            New conversation
          </Button>
        )}
      </div>

      {/* Past conversations — compact chips. Only shown when there's
          something to load and the chat panel is empty (avoids a busy
          header during an active session). */}
      {!hasMessages && pastConversations.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap pb-3 -mt-2">
          <span className="text-xs text-textMuted/70 shrink-0">Continue:</span>
          {pastConversations.slice(0, 4).map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => handleLoadConversation(c.id)}
              disabled={streaming}
              title={`Continue "${c.title}"`}
              aria-pressed={c.id === activeConversationId || undefined}
              className={[
                'inline-flex items-center max-w-[220px] gap-1.5 px-2.5 py-1.5 rounded-md',
                'text-xs text-textMuted hover:text-text',
                'bg-surface border border-[var(--border)] hover:border-textMuted/30',
                'transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent',
                'disabled:opacity-40 disabled:cursor-not-allowed',
              ].join(' ')}
            >
              <svg
                width="11"
                height="11"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="shrink-0"
                aria-hidden="true"
              >
                <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
              </svg>
              <span className="truncate">{c.title}</span>
            </button>
          ))}
        </div>
      )}

      {/* ── Chat panel ───────────────────────────────────────── */}
      <div className="flex flex-col flex-1 min-h-0 rounded-xl border border-[var(--border)] bg-surface overflow-hidden">
        {/* Message list */}
        <div className="flex flex-col flex-1 overflow-y-auto px-5 py-4 gap-4 min-h-0">
          {hasMessages ? (
            messages.map((msg, idx) => (
              <MessageBubble key={idx} message={msg} />
            ))
          ) : (
            <EmptyState onSuggest={setInputValue} />
          )}
          {/* Sentinel for auto-scroll */}
          <div ref={messagesEndRef} />
        </div>

        {/* Error banner */}
        {error && (
          <div className="px-5 pb-2">
            <ErrorBanner message={error} onDismiss={clearError} />
          </div>
        )}

        {/* Streaming indicator bar */}
        {streaming && (
          <div className="px-5 pb-1">
            <p className="text-xs text-textMuted animate-pulse">Advisor is responding…</p>
          </div>
        )}

        {/* Input area */}
        <div className="border-t border-[var(--border)] px-5 py-4 flex-shrink-0">
          <div className="flex items-end gap-3">
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about TCO, vendor justification, or budget framing…"
              disabled={streaming}
              rows={1}
              aria-label="Message input"
              className={[
                'flex-1 resize-none rounded-lg px-3 py-2.5 text-sm bg-bg text-text',
                'border border-[var(--border)] hover:border-textMuted/30',
                'placeholder:text-textMuted/50 leading-relaxed',
                'focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-surface',
                'disabled:opacity-40 disabled:cursor-not-allowed',
                'min-h-[44px] max-h-[160px] overflow-y-auto',
                'transition-colors duration-150',
              ].join(' ')}
            />

            <Button
              variant="primary"
              onClick={handleSend}
              disabled={!canSend}
              aria-label="Send message"
              className="flex-shrink-0 h-[44px] px-4"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
              Send
            </Button>
          </div>

          {/* Disclaimer */}
          <p className="mt-2 text-[11px] text-textMuted/50 text-center">
            Advisor output is for planning guidance only — verify recommendations with qualified engineers before deployment.
          </p>
        </div>
      </div>
    </div>
  );
}
