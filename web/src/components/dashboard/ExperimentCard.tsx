import { Link } from 'react-router-dom';
import type { ExperimentListItem } from '../../api/types';

interface ExperimentCardProps {
  experiment: ExperimentListItem;
  onDelete?: () => void;
}

export function ExperimentCard({ experiment, onDelete }: ExperimentCardProps) {
  const statusColor = {
    active: 'bg-primary text-primary-foreground',
    paused: 'bg-warning text-warning-foreground',
    completed: 'bg-muted text-muted-foreground',
  }[experiment.status] || 'bg-muted text-muted-foreground';

  return (
    <div className="relative group bg-card text-card-foreground rounded-xl border border-border shadow-card hover:shadow-card-hover hover:border-primary/40 transition-all">
      <Link
        to={`/experiments/${experiment.id}`}
        className="block p-6"
      >
        <div className="flex items-start justify-between mb-4">
          <h3 className="text-base font-semibold text-foreground leading-tight pr-2">
            {experiment.name}
          </h3>
          <span className={`flex-shrink-0 px-2.5 py-0.5 rounded-full text-xs font-mono font-medium ${statusColor}`}>
            {experiment.status}
          </span>
        </div>
        <div className="space-y-2 text-sm text-muted-foreground">
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
      </Link>

      {/* Delete button (visible on hover) */}
      {onDelete && (
        <button
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onDelete();
          }}
          className="
            absolute top-3 right-3 p-1.5 rounded
            text-muted-foreground/30 hover:text-red-500
            hover:bg-red-50 dark:hover:bg-red-900/20
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
    </div>
  );
}
