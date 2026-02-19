import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import type { ExperimentListItem } from '../../api/types';
import { Badge, statusVariant } from '../ui/Badge';
import { Card } from '../ui/Card';

interface ExperimentCardProps {
  experiment: ExperimentListItem;
  onDelete?: () => void;
  onRename?: (newName: string) => void;
}

export function ExperimentCard({ experiment, onDelete, onRename }: ExperimentCardProps) {
  const [renaming, setRenaming] = useState(false);
  const [draft, setDraft] = useState(experiment.name);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (renaming) {
      setDraft(experiment.name);
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [renaming, experiment.name]);

  function handleRenameClick(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    setRenaming(true);
  }

  function handleRenameCommit() {
    const trimmed = draft.trim();
    if (trimmed && trimmed !== experiment.name && onRename) {
      onRename(trimmed);
    }
    setRenaming(false);
  }

  const meta = (
    <div className="space-y-2 text-sm text-muted-foreground mt-4">
      <div className="flex justify-between items-center">
        <span className="font-mono text-xs uppercase tracking-wide">Created</span>
        <span className="font-mono text-foreground text-xs">
          {new Date(experiment.created_at).toLocaleDateString()}
        </span>
      </div>
      <div className="flex justify-between items-center">
        <span className="font-mono text-xs uppercase tracking-wide">Agents</span>
        <span className="font-mono text-foreground text-xs">{experiment.num_agents}</span>
      </div>
      {experiment.current_day !== null && (
        <div className="flex justify-between items-center">
          <span className="font-mono text-xs uppercase tracking-wide">Trading Day</span>
          <span className="font-mono text-foreground text-xs">{experiment.current_day}</span>
        </div>
      )}
    </div>
  );

  return (
    <Card className="relative group hover:shadow-card-hover hover:border-primary/40 transition-all" padding={false}>
      {renaming ? (
        <div className="p-6">
          <div className="flex items-start justify-between mb-1">
            <input
              ref={inputRef}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onBlur={handleRenameCommit}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleRenameCommit();
                if (e.key === 'Escape') setRenaming(false);
              }}
              className="flex-1 bg-transparent border-b border-primary outline-none text-base font-semibold text-foreground pr-2"
            />
            <Badge variant={statusVariant(experiment.status)} className="flex-shrink-0 font-mono">
              {experiment.status}
            </Badge>
          </div>
          {meta}
        </div>
      ) : (
        <Link to={`/experiments/${experiment.id}`} className="block p-6">
          <div className="flex items-start justify-between mb-4">
            <h3 className="text-base font-semibold text-foreground leading-tight pr-2">
              {experiment.name}
            </h3>
            <Badge variant={statusVariant(experiment.status)} className="flex-shrink-0 font-mono">
              {experiment.status}
            </Badge>
          </div>
          {meta}
        </Link>
      )}

      {/* Rename button */}
      {onRename && !renaming && (
        <button
          type="button"
          onClick={handleRenameClick}
          className="
            absolute top-3 right-9 p-1.5 rounded
            text-muted-foreground/30 hover:text-primary
            hover:bg-primary/10
            opacity-0 group-hover:opacity-100
            transition-all focus:opacity-100
          "
          aria-label="Rename experiment"
          title="Rename experiment"
        >
          <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
            <path
              d="M9.5 1.5l2 2-7 7H2.5v-2l7-7z"
              stroke="currentColor"
              strokeWidth="1.25"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      )}

      {/* Delete button */}
      {onDelete && (
        <button
          type="button"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onDelete();
          }}
          className="
            absolute top-3 right-3 p-1.5 rounded
            text-muted-foreground/30 hover:text-loss
            hover:bg-loss/10
            opacity-0 group-hover:opacity-100
            transition-all focus:opacity-100
          "
          aria-label="Delete experiment"
          title="Delete experiment"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path
              d="M1 3h12M5 3V2a1 1 0 011-1h2a1 1 0 011 1v1M2 3l.8 9a1 1 0 001 .9h6.4a1 1 0 001-.9L12 3"
              stroke="currentColor"
              strokeWidth="1.25"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      )}
    </Card>
  );
}
