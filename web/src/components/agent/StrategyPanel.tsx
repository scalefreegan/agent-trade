import type { AgentStrategy } from '../../api/types';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { GuidanceSection } from './GuidanceSection';

interface StrategyPanelProps {
  strategy: AgentStrategy;
  guidance: string | null;
  onEditStrategy: () => void;
  onSaveGuidance: (guidance: string | null) => Promise<void>;
  isGuidancePending: boolean;
  guidanceError: string | null;
}

export function StrategyPanel({
  strategy,
  guidance,
  onEditStrategy,
  onSaveGuidance,
  isGuidancePending,
  guidanceError,
}: StrategyPanelProps) {
  return (
    <div>
      {/* Investment Thesis Card */}
      <Card className="mb-8">
        <div className="flex items-start justify-between mb-4">
          <div className="flex gap-3">
            <Badge variant="info" className="uppercase tracking-wide text-xs px-3 py-1">
              {strategy.thesis.risk_tolerance}
            </Badge>
            <Badge variant="neutral" className="text-xs px-3 py-1">
              {strategy.thesis.time_horizon}
            </Badge>
          </div>
          <button
            onClick={onEditStrategy}
            className="px-3 py-1 text-xs font-mono font-semibold rounded border border-border text-muted-foreground hover:text-foreground hover:border-foreground transition-colors flex-shrink-0"
          >
            Edit
          </button>
        </div>

        <p className="text-foreground leading-relaxed mb-4">
          <strong>Philosophy:</strong> {strategy.thesis.philosophy}
        </p>

        {strategy.thesis.preferred_sectors.length > 0 && (
          <p className="text-foreground leading-relaxed mt-4 mb-4">
            <strong>Preferred Sectors:</strong> {strategy.thesis.preferred_sectors.join(', ')}
          </p>
        )}

        {strategy.thesis.key_metrics.length > 0 && (
          <div className="mt-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
              Key Metrics
            </div>
            <ul className="grid gap-2 list-none p-0 m-0">
              {strategy.thesis.key_metrics.map((metric, idx) => (
                <li key={idx} className="flex items-start gap-2 text-foreground text-sm">
                  <span className="text-brand-800 font-bold flex-shrink-0">•</span>
                  <span>{metric}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="mt-4 pt-4 border-t border-border text-foreground leading-relaxed">
          <strong>Rationale:</strong> {strategy.rationale}
        </div>
      </Card>

      {/* Learnings Timeline */}
      <div>
        <div className="text-xs font-bold tracking-widest uppercase text-primary mb-4 pb-3 border-b-2 border-primary">
          Strategy Learnings ({strategy.learnings.length})
        </div>

        {strategy.learnings.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground text-sm">No learnings recorded yet</div>
        ) : (
          <div className="flex flex-col gap-4">
            {strategy.learnings.map((learning, idx) => {
              const outcome = learning.outcome.toLowerCase();
              const badgeVariant =
                outcome === 'positive' ? 'success' :
                outcome === 'negative' ? 'error' :
                'warning';

              return (
                <Card key={idx} className="relative pl-12">
                  <div className="absolute left-4 top-5 font-mono text-[0.6875rem] text-muted-foreground -rotate-90 origin-top-left whitespace-nowrap">
                    {learning.date}
                  </div>
                  <Badge variant={badgeVariant} className="mb-3 uppercase tracking-wide text-[0.6875rem]">
                    {learning.outcome}
                  </Badge>
                  <p className="text-foreground text-sm leading-relaxed mb-2">{learning.observation}</p>
                  <p className="text-muted-foreground text-[0.8125rem] leading-relaxed italic pl-4 border-l-[3px] border-brand-800">
                    {learning.lesson}
                  </p>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* Guidance Section */}
      <GuidanceSection
        guidance={guidance}
        onSave={onSaveGuidance}
        isPending={isGuidancePending}
        error={guidanceError}
      />
    </div>
  );
}
