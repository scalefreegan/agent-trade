import { useEffect, useRef, useState } from 'react';
import { Card } from '../ui/Card';

interface GuidanceSectionProps {
  guidance: string | null;
  onSave: (guidance: string | null) => Promise<void>;
  isPending: boolean;
  error?: string | null;
}

export function GuidanceSection({ guidance, onSave, isPending, error }: GuidanceSectionProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(guidance ?? '');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (editing) {
      setDraft(guidance ?? '');
      setTimeout(() => textareaRef.current?.focus(), 50);
    }
  }, [editing, guidance]);

  const handleSave = async () => {
    const value = draft.trim() || null;
    try {
      await onSave(value);
      setEditing(false);
    } catch {
      // error is surfaced via the `error` prop from the parent
    }
  };

  const handleClear = async () => {
    try {
      await onSave(null);
      setEditing(false);
    } catch {
      // error is surfaced via the `error` prop from the parent
    }
  };

  const handleCancel = () => {
    setDraft(guidance ?? '');
    setEditing(false);
  };

  const inputClass =
    'w-full px-3 py-2.5 text-sm font-mono bg-muted border border-border rounded transition-colors outline-none text-foreground placeholder-muted-foreground focus:ring-2 focus:ring-primary focus:border-primary resize-y';

  return (
    <div className="mt-8">
      <div className="flex items-center justify-between mb-4">
        <div className="text-xs font-bold tracking-widest uppercase text-primary pb-3 border-b-2 border-primary flex-1">
          Agent Guidance
        </div>
        {!editing && (
          <button
            onClick={() => setEditing(true)}
            className="ml-4 mb-3 px-3 py-1 text-xs font-mono font-semibold rounded border border-border text-muted-foreground hover:text-foreground hover:border-foreground transition-colors"
          >
            {guidance ? 'Edit' : 'Add'}
          </button>
        )}
      </div>

      {editing ? (
        <Card>
          <p className="text-xs text-muted-foreground font-mono mb-3">
            Guidance is injected into the agent's prompt on every trading day.
          </p>
          {error && (
            <div className="mb-3 rounded border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 px-3 py-2">
              <p className="text-xs text-red-700 dark:text-red-400 font-mono">{error}</p>
            </div>
          )}
          <textarea
            ref={textareaRef}
            rows={4}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="e.g. Focus on dividend-paying stocks. Avoid speculative positions."
            className={inputClass}
          />
          <div className="flex items-center justify-end gap-2 mt-3">
            <button
              type="button"
              onClick={handleCancel}
              disabled={isPending}
              className="px-3 py-1.5 text-xs font-mono text-muted-foreground hover:text-foreground disabled:opacity-50 transition-colors"
            >
              Cancel
            </button>
            {guidance && (
              <button
                type="button"
                onClick={handleClear}
                disabled={isPending}
                className="px-3 py-1.5 text-xs font-mono rounded border border-red-300 dark:border-red-700 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-50 transition-colors"
              >
                Clear
              </button>
            )}
            <button
              type="button"
              onClick={handleSave}
              disabled={isPending}
              className="px-4 py-1.5 text-xs font-mono font-semibold rounded bg-primary hover:bg-primary/90 text-primary-foreground disabled:opacity-60 disabled:cursor-not-allowed transition-colors flex items-center gap-1.5"
            >
              {isPending && (
                <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              )}
              {isPending ? 'Saving…' : 'Save'}
            </button>
          </div>
        </Card>
      ) : guidance ? (
        <Card>
          <p className="text-sm text-foreground leading-relaxed whitespace-pre-wrap">{guidance}</p>
        </Card>
      ) : (
        <div
          className="text-center py-6 text-muted-foreground text-sm cursor-pointer hover:text-foreground transition-colors"
          onClick={() => setEditing(true)}
        >
          No guidance set — click Add to set guidance for this agent
        </div>
      )}
    </div>
  );
}
