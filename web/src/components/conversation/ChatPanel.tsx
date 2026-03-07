import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { useConversation, useSendMessage } from '../../api/conversation';
import type { ConversationMessage } from '../../api/types';

interface ChatPanelProps {
  conversationId: string;
}

export function ChatPanel({ conversationId }: ChatPanelProps) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const { data: conversation, isLoading } = useConversation(conversationId);
  const sendMessage = useSendMessage(conversationId);

  const isResponding = conversation?.status === 'responding';

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversation?.messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, [conversationId]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isResponding || sendMessage.isPending) return;

    sendMessage.mutate(trimmed);
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        Loading conversation...
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {conversation?.messages.length === 0 && (
          <div className="flex-1 flex flex-col items-center justify-center text-center py-16">
            <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="text-primary">
                <path
                  d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2v10z"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-foreground mb-1">Start a conversation</h3>
            <p className="text-sm text-muted-foreground max-w-sm">
              Ask about stocks, market analysis, trading strategies, or anything else.
              Claude has access to real-time stock data and news via MCP tools.
            </p>
          </div>
        )}

        {conversation?.messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isResponding && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-primary/15 flex items-center justify-center flex-shrink-0">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="text-primary">
                <path
                  d="M8 1v2M8 13v2M3.05 3.05l1.41 1.41M11.54 11.54l1.41 1.41M1 8h2M13 8h2M3.05 12.95l1.41-1.41M11.54 4.46l1.41-1.41"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
              </svg>
            </div>
            <div className="bg-muted rounded-2xl rounded-tl-sm px-4 py-3 max-w-[80%]">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-border p-4">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isResponding ? 'Waiting for response...' : 'Type a message... (Enter to send, Shift+Enter for new line)'}
            disabled={isResponding}
            rows={1}
            className="flex-1 resize-none rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50 min-h-[40px] max-h-[120px]"
            style={{ height: 'auto', overflow: 'auto' }}
            onInput={(e) => {
              const target = e.target as HTMLTextAreaElement;
              target.style.height = 'auto';
              target.style.height = Math.min(target.scrollHeight, 120) + 'px';
            }}
          />
          <button
            type="submit"
            disabled={!input.trim() || isResponding || sendMessage.isPending}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex-shrink-0"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path
                d="M14 2L7 9M14 2l-4.5 12-2-5.5L2 6.5 14 2z"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </form>
        {sendMessage.isError && (
          <p className="text-xs text-loss mt-2">{sendMessage.error?.message}</p>
        )}
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: ConversationMessage }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
          isUser ? 'bg-primary text-primary-foreground' : 'bg-primary/15 text-primary'
        }`}
      >
        {isUser ? (
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <path
              d="M8 8a3 3 0 100-6 3 3 0 000 6zM2 14a6 6 0 0112 0"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
          </svg>
        ) : (
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <path
              d="M8 1v2M8 13v2M3.05 3.05l1.41 1.41M11.54 11.54l1.41 1.41M1 8h2M13 8h2M3.05 12.95l1.41-1.41M11.54 4.46l1.41-1.41"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
          </svg>
        )}
      </div>

      {/* Message content */}
      <div
        className={`rounded-2xl px-4 py-3 max-w-[80%] text-sm leading-relaxed ${
          isUser
            ? 'bg-primary text-primary-foreground rounded-tr-sm whitespace-pre-wrap'
            : 'bg-muted text-foreground rounded-tl-sm'
        }`}
      >
        {isUser ? message.content : (
          <div className="
            prose prose-sm max-w-none dark:prose-invert
            prose-headings:text-foreground prose-headings:font-semibold
            prose-h2:text-base prose-h2:mt-4 prose-h2:mb-2
            prose-h3:text-sm
            prose-p:text-foreground prose-p:my-1.5
            prose-strong:text-foreground
            prose-li:text-foreground prose-li:my-0.5
            prose-code:bg-white/10 prose-code:text-foreground prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-xs
            prose-pre:bg-white/10 prose-pre:border prose-pre:border-border prose-pre:rounded-md
            prose-table:border-collapse
            prose-th:border prose-th:border-border prose-th:bg-white/5 prose-th:px-2 prose-th:py-1.5 prose-th:text-xs
            prose-td:border prose-td:border-border prose-td:px-2 prose-td:py-1.5 prose-td:text-xs
            prose-a:text-primary hover:prose-a:text-primary/80
            prose-blockquote:border-l-4 prose-blockquote:border-primary/50 prose-blockquote:text-muted-foreground prose-blockquote:not-italic
          ">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}
