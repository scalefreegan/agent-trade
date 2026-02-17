import { useState } from 'react';
import Markdown from 'react-markdown';
import type { DecisionLogEntry } from '../../api/types';
import { useAgentDecision } from '../../api/agents';
import { Badge } from '../ui/Badge';
import { Card } from '../ui/Card';

interface DecisionLogProps {
  experimentId: string;
  agentId: string;
  decisions: DecisionLogEntry[];
}

export function DecisionLog({ experimentId, agentId, decisions }: DecisionLogProps) {
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const { data: decisionDetail } = useAgentDecision(
    experimentId,
    agentId,
    selectedDate || ''
  );

  return (
    <div>
      {decisions.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">No decisions recorded yet</div>
      ) : (
        <div className="grid gap-3 mb-6">
          {decisions.map((decision) => {
            const isSelected = selectedDate === decision.date;
            return (
              <Card
                key={decision.date}
                padding={false}
                className={`
                  px-5 py-4 cursor-pointer transition-all
                  grid items-center gap-4
                  ${isSelected
                    ? 'border-primary bg-primary/5'
                    : 'hover:border-brand-800 hover:shadow-card-hover'
                  }
                `}
                style={{ gridTemplateColumns: 'auto 1fr auto' }}
                onClick={() => setSelectedDate(decision.date)}
              >
                <div className="flex flex-col gap-1">
                  <div className="font-mono text-[0.9375rem] font-bold text-foreground">{decision.date}</div>
                  <div className="text-xs text-muted-foreground uppercase tracking-wide">Day {decision.trading_day}</div>
                </div>

                <div className="flex items-center gap-3">
                  <Badge
                    variant={decision.has_orders ? 'success' : 'neutral'}
                    className="text-[0.6875rem] font-semibold"
                  >
                    {decision.has_orders ? (
                      <>✓ {decision.order_count} order{decision.order_count !== 1 ? 's' : ''}</>
                    ) : (
                      'No orders'
                    )}
                  </Badge>
                </div>

                <svg
                  className={`w-5 h-5 transition-all duration-200 ${isSelected ? 'text-primary translate-x-1' : 'text-muted-foreground'}`}
                  fill="none" viewBox="0 0 24 24" stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </Card>
            );
          })}
        </div>
      )}

      {/* Decision Detail Modal */}
      {selectedDate && decisionDetail && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 animate-fade-in"
          onClick={() => setSelectedDate(null)}
        >
          <div
            className="bg-card rounded-xl max-w-[900px] w-full max-h-[90vh] flex flex-col animate-slide-up"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-center px-6 py-5 border-b border-border">
              <div className="text-lg font-bold text-foreground">Decision for {selectedDate}</div>
              <button
                className="w-8 h-8 rounded-md border-none bg-muted text-muted-foreground cursor-pointer flex items-center justify-center transition-colors hover:bg-border hover:text-foreground"
                onClick={() => setSelectedDate(null)}
                aria-label="Close"
              >
                <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="overflow-y-auto px-6 py-6">
              <div className="
                prose prose-sm max-w-none dark:prose-invert
                prose-headings:text-foreground prose-headings:font-semibold
                prose-h1:text-2xl prose-h1:border-b prose-h1:border-border prose-h1:pb-2
                prose-h2:text-xl prose-h2:border-b prose-h2:border-border/50 prose-h2:pb-1.5
                prose-h3:text-base
                prose-p:text-foreground prose-p:leading-relaxed
                prose-a:text-brand-800 hover:prose-a:text-primary
                prose-strong:text-foreground
                prose-code:bg-muted prose-code:text-foreground prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-code:font-mono
                prose-pre:bg-muted prose-pre:border prose-pre:border-border prose-pre:rounded-md
                prose-blockquote:border-l-4 prose-blockquote:border-brand-800 prose-blockquote:text-muted-foreground prose-blockquote:not-italic
                prose-table:border-collapse
                prose-th:border prose-th:border-border prose-th:bg-muted prose-th:px-2 prose-th:py-2
                prose-td:border prose-td:border-border prose-td:px-2 prose-td:py-2
                prose-hr:border-border
                prose-li:text-foreground
              ">
                <Markdown>{decisionDetail.markdown}</Markdown>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
