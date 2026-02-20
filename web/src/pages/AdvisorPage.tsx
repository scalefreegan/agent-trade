import { useState } from 'react';
import { Card } from '../components/ui/Card';
import { AgentSelector } from '../components/advisor/AgentSelector';
import { RecommendationCard } from '../components/advisor/RecommendationCard';
import { ConsensusSummary } from '../components/advisor/ConsensusSummary';
import { useStartRecommendation, useAdvisorJobStatus } from '../api/advisor';
import type { AdvisorAgentConfig } from '../api/types';

export function AdvisorPage() {
  const [symbol, setSymbol] = useState('');
  const [portfolioValue, setPortfolioValue] = useState('100000');
  const [selectedAgents, setSelectedAgents] = useState<AdvisorAgentConfig[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);

  const startMutation = useStartRecommendation();
  const { data: job, isError: jobPollingError, error: jobError } = useAdvisorJobStatus(jobId);

  const isRunning = job?.status === 'running' || job?.status === 'pending';
  const isComplete = job?.status === 'completed';
  const showResults = jobId != null;

  const handleSubmit = () => {
    const trimmedSymbol = symbol.trim().toUpperCase();
    if (!trimmedSymbol || selectedAgents.length === 0) return;

    startMutation.mutate(
      {
        symbol: trimmedSymbol,
        agents: selectedAgents,
        portfolio_value: parseFloat(portfolioValue) || 100_000,
      },
      {
        onSuccess: (data) => setJobId(data.job_id),
      }
    );
  };

  const handleReset = () => {
    setJobId(null);
    setSymbol('');
    setSelectedAgents([]);
    startMutation.reset();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Advisor</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Get stock recommendations from multiple AI advisors with different investment philosophies.
        </p>
      </div>

      {!showResults ? (
        /* ─── Setup View ─────────────────────────────────────────── */
        <div className="space-y-6">
          {/* Symbol + Portfolio value */}
          <Card>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="symbol-input" className="block text-sm font-medium text-foreground mb-1">
                  Stock Symbol
                </label>
                <input
                  id="symbol-input"
                  type="text"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                  placeholder="e.g. AAPL"
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div>
                <label htmlFor="portfolio-value" className="block text-sm font-medium text-foreground mb-1">
                  Portfolio Value ($)
                </label>
                <input
                  id="portfolio-value"
                  type="number"
                  value={portfolioValue}
                  onChange={(e) => setPortfolioValue(e.target.value)}
                  placeholder="100000"
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>
          </Card>

          {/* Agent selector */}
          <AgentSelector selected={selectedAgents} onSelectionChange={setSelectedAgents} />

          {/* Submit */}
          <div className="flex items-center gap-3">
            <button
              onClick={handleSubmit}
              disabled={!symbol.trim() || selectedAgents.length === 0 || startMutation.isPending}
              className="rounded-lg bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {startMutation.isPending ? 'Starting...' : 'Get Recommendations'}
            </button>
            {startMutation.isError && (
              <p className="text-sm text-loss">{startMutation.error?.message}</p>
            )}
          </div>
        </div>
      ) : (
        /* ─── Results View ───────────────────────────────────────── */
        <div className="space-y-6">
          {/* Progress header */}
          <Card>
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-medium text-foreground">
                  Recommendations for <span className="text-primary">{job?.symbol ?? symbol}</span>
                </h2>
                <p className="text-sm text-muted-foreground mt-0.5">
                  {isRunning
                    ? `Analyzing... ${job?.completed_agents ?? 0} of ${job?.total_agents ?? selectedAgents.length} advisors complete`
                    : isComplete
                      ? `${job?.recommendations.length ?? 0} recommendations received`
                      : job?.error ?? 'Processing...'}
                </p>
              </div>
              <div className="flex items-center gap-3">
                {isRunning && <Spinner />}
                {isComplete && (
                  <button
                    onClick={handleReset}
                    className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted transition-colors"
                  >
                    New Search
                  </button>
                )}
              </div>
            </div>

            {/* Progress bar */}
            {isRunning && job && (
              <div className="mt-3">
                <div className="w-full h-2 rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary transition-all duration-500"
                    style={{
                      width: `${job.total_agents > 0 ? (job.completed_agents / job.total_agents) * 100 : 0}%`,
                    }}
                  />
                </div>
              </div>
            )}
          </Card>

          {/* Error when job status polling fails */}
          {jobPollingError && (
            <div className="rounded-lg border border-loss/30 bg-loss/5 px-4 py-3">
              <p className="text-sm font-medium text-loss">Failed to retrieve job status</p>
              <p className="text-xs text-muted-foreground mt-1">
                {jobError instanceof Error ? jobError.message : 'Unable to fetch recommendation progress. Please try again.'}
              </p>
              <button
                onClick={handleReset}
                className="mt-3 text-xs text-primary hover:underline"
              >
                Start a new search
              </button>
            </div>
          )}

          {/* Warning when recommendations were dropped */}
          {job && job.dropped_count > 0 && (
            <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/5 px-4 py-3">
              <p className="text-sm font-medium text-yellow-600 dark:text-yellow-500">
                Warning: {job.dropped_count} recommendation{job.dropped_count > 1 ? 's were' : ' was'} dropped due to validation errors
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Some advisors returned malformed recommendations. Check server logs for details.
              </p>
            </div>
          )}

          {/* Consensus summary (show when at least 2 recommendations) */}
          {(job?.recommendations.length ?? 0) >= 2 && (
            <ConsensusSummary
              recommendations={job!.recommendations}
              symbol={job!.symbol}
            />
          )}

          {/* Individual recommendations */}
          {(job?.recommendations.length ?? 0) > 0 && (
            <div>
              <h3 className="text-sm font-medium text-foreground mb-3">Individual Recommendations</h3>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {job!.recommendations.map((rec, idx) => (
                  <RecommendationCard key={`${rec.agent_name}-${idx}`} recommendation={rec} />
                ))}
              </div>
            </div>
          )}

          {/* Error state */}
          {job?.status === 'failed' && (
            <Card>
              <p className="text-sm text-loss">{job.error ?? 'An error occurred.'}</p>
              <button
                onClick={handleReset}
                className="mt-3 rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted transition-colors"
              >
                Try Again
              </button>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}

function Spinner() {
  return (
    <svg
      className="animate-spin h-5 w-5 text-primary"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}
