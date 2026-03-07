import { useState } from 'react';
import { ConversationList } from '../components/conversation/ConversationList';
import { ChatPanel } from '../components/conversation/ChatPanel';
import { useCreateConversation } from '../api/conversation';

export function ConversationPage() {
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [showList, setShowList] = useState(true);
  const createConversation = useCreateConversation();

  const handleNew = () => {
    createConversation.mutate(undefined, {
      onSuccess: (conv) => {
        setActiveConversationId(conv.id);
        setShowList(false);
      },
    });
  };

  const handleSelect = (id: string) => {
    setActiveConversationId(id);
    setShowList(false);
  };

  const handleDelete = (id: string) => {
    if (id === activeConversationId) {
      setActiveConversationId(null);
      setShowList(true);
    }
  };

  return (
    <div className="h-[calc(100vh-theme(spacing.20))]">
      <div className="flex h-full rounded-xl border border-border overflow-hidden bg-card shadow-card">
        {/* Conversation list sidebar */}
        <div
          className={`
            ${showList ? 'flex' : 'hidden'}
            md:flex flex-col w-full md:w-72 lg:w-80 border-r border-border flex-shrink-0
          `}
        >
          <ConversationList
            activeId={activeConversationId}
            onSelect={handleSelect}
            onNew={handleNew}
            onDelete={handleDelete}
          />
        </div>

        {/* Chat panel */}
        <div className={`flex-1 flex flex-col min-w-0 ${!showList ? 'flex' : 'hidden md:flex'}`}>
          {/* Mobile back button */}
          {activeConversationId && (
            <div className="md:hidden flex items-center gap-2 px-4 py-2 border-b border-border">
              <button
                onClick={() => setShowList(true)}
                className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                aria-label="Back to conversations"
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
              <span className="text-sm font-medium text-foreground">Back</span>
            </div>
          )}

          {activeConversationId ? (
            <ChatPanel conversationId={activeConversationId} />
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
              <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" className="text-primary">
                  <path
                    d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2v10z"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>
              <h2 className="text-xl font-bold text-foreground mb-2">Chat with Claude</h2>
              <p className="text-sm text-muted-foreground max-w-md mb-6">
                Start a conversation with Claude, powered by MCP tools for stock research,
                market analysis, and financial data. Your conversations are saved and can be continued later.
              </p>
              <button
                onClick={handleNew}
                disabled={createConversation.isPending}
                className="rounded-lg bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
              >
                {createConversation.isPending ? 'Creating...' : 'New Conversation'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
