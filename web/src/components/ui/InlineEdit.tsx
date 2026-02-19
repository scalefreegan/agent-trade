import { useEffect, useRef, useState } from 'react';

interface InlineEditProps {
  value: string;
  onSave: (value: string) => void;
  placeholder?: string;
  emptyText?: string;
  isPending?: boolean;
  className?: string;
  inputClassName?: string;
  multiline?: boolean;
}

export function InlineEdit({
  value,
  onSave,
  placeholder = 'Click to edit',
  emptyText,
  isPending = false,
  className = '',
  inputClassName = '',
  multiline = false,
}: InlineEditProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null);

  useEffect(() => {
    setDraft(value);
  }, [value]);

  useEffect(() => {
    if (editing) {
      inputRef.current?.focus();
      if (inputRef.current instanceof HTMLInputElement) {
        inputRef.current.select();
      }
    }
  }, [editing]);

  function start() {
    setDraft(value);
    setEditing(true);
  }

  function commit() {
    const trimmed = draft.trim();
    if (trimmed !== value && trimmed.length > 0) {
      onSave(trimmed);
    } else if (trimmed.length === 0 && emptyText !== undefined) {
      // Allow clearing to empty if emptyText is provided (e.g. optional description)
      if (value !== '') onSave('');
    }
    setEditing(false);
  }

  function cancel() {
    setDraft(value);
    setEditing(false);
  }

  const baseInputClass = `
    bg-transparent border-b border-primary outline-none
    text-foreground placeholder:text-muted-foreground
    w-full resize-none
    ${inputClassName}
  `;

  if (editing) {
    if (multiline) {
      return (
        <textarea
          ref={inputRef as React.RefObject<HTMLTextAreaElement>}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === 'Escape') cancel();
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              commit();
            }
          }}
          rows={2}
          placeholder={placeholder}
          className={baseInputClass}
        />
      );
    }

    return (
      <input
        ref={inputRef as React.RefObject<HTMLInputElement>}
        type="text"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === 'Enter') commit();
          if (e.key === 'Escape') cancel();
        }}
        placeholder={placeholder}
        className={baseInputClass}
      />
    );
  }

  const displayText = value || emptyText;
  const isEmpty = !value;

  return (
    <button
      type="button"
      onClick={start}
      disabled={isPending}
      className={`group flex items-center gap-2 text-left transition-colors hover:text-primary disabled:opacity-60 ${className}`}
    >
      <span className={isEmpty ? 'text-muted-foreground italic' : undefined}>
        {displayText || placeholder}
      </span>
      <svg
        className="opacity-0 group-hover:opacity-60 transition-opacity flex-shrink-0"
        width="13"
        height="13"
        viewBox="0 0 13 13"
        fill="none"
        aria-hidden="true"
      >
        <path
          d="M9.5 1.5l2 2-7 7H2.5v-2l7-7z"
          stroke="currentColor"
          strokeWidth="1.25"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </button>
  );
}
