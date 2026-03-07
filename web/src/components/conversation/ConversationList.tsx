import { useConversations, useDeleteConversation } from '../../api/conversation';
import type { ConversationSummary } from '../../api/types';

interface ConversationListProps {
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete?: (id: string) => void;
}

export function ConversationList({ activeId, onSelect, onNew, onDelete }: ConversationListProps) {
  const { data, isLoading } = useConversations();
  const deleteMutation = useDeleteConversation();

  const conversations = data?.conversations ?? [];

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <h2 className="text-sm font-semibold text-foreground">Conversations</h2>
        <button
          onClick={onNew}
          className="rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          + New
        </button>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {isLoading && (
          <div className="p-4 text-sm text-muted-foreground">Loading...</div>
        )}

        {!isLoading && conversations.length === 0 && (
          <div className="p-4 text-center">
            <p className="text-sm text-muted-foreground">No conversations yet</p>
            <button
              onClick={onNew}
              className="mt-2 text-xs text-primary hover:underline"
            >
              Start your first conversation
            </button>
          </div>
        )}

        {conversations.map((conv) => (
          <ConversationItem
            key={conv.id}
            conversation={conv}
            isActive={conv.id === activeId}
            onSelect={() => onSelect(conv.id)}
            onDelete={() => {
              deleteMutation.mutate(conv.id, {
                onSuccess: () => onDelete?.(conv.id),
              });
            }}
          />
        ))}
      </div>
    </div>
  );
}

function ConversationItem({
  conversation,
  isActive,
  onSelect,
  onDelete,
}: {
  conversation: ConversationSummary;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
}) {
  const timeAgo = formatRelativeTime(conversation.updated_at);

  return (
    <div
      onClick={onSelect}
      className={`group flex items-start gap-2 px-4 py-3 cursor-pointer border-b border-border/50 transition-colors ${
        isActive ? 'bg-primary/10' : 'hover:bg-muted/50'
      }`}
    >
      <div className="flex-1 min-w-0">
        <p className={`text-sm font-medium truncate ${isActive ? 'text-primary' : 'text-foreground'}`}>
          {conversation.title}
        </p>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-xs text-muted-foreground">{timeAgo}</span>
          <span className="text-xs text-muted-foreground">
            {conversation.message_count} msg{conversation.message_count !== 1 ? 's' : ''}
          </span>
          {conversation.status === 'responding' && (
            <span className="text-xs text-primary font-medium">typing...</span>
          )}
        </div>
      </div>

      {/* Delete button */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        className="opacity-0 group-hover:opacity-100 p-1 rounded text-muted-foreground hover:text-loss hover:bg-loss/10 transition-all"
        aria-label="Delete conversation"
      >
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
          <path
            d="M2 4h12M5.33 4V2.67a1.33 1.33 0 011.34-1.34h2.66a1.33 1.33 0 011.34 1.34V4M12.67 4v9.33a1.33 1.33 0 01-1.34 1.34H4.67a1.33 1.33 0 01-1.34-1.34V4"
            stroke="currentColor"
            strokeWidth="1.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>
    </div>
  );
}

function formatRelativeTime(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHr = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHr / 24);

  if (diffSec < 60) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHr < 24) return `${diffHr}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;
  return date.toLocaleDateString();
}
