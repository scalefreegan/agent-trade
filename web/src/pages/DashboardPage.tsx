import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCreateExperiment, useExperiments, type CreateExperimentInput } from '../api/experiments';
import { ExperimentList } from '../components/dashboard/ExperimentList';
import { NewExperimentDialog } from '../components/dashboard/NewExperimentDialog';
import { ExperimentCardSkeleton } from '../components/ui/Skeleton';
import { EmptyState } from '../components/ui/EmptyState';

export function DashboardPage() {
  const { data: experiments, isLoading, error } = useExperiments();
  const [dialogOpen, setDialogOpen] = useState(false);
  const navigate = useNavigate();

  const createMutation = useCreateExperiment();

  const handleCreate = (data: CreateExperimentInput) => {
    createMutation.mutate(data, {
      onSuccess: (newExp) => {
        setDialogOpen(false);
        createMutation.reset();
        navigate(`/experiments/${newExp.id}`);
      },
    });
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    createMutation.reset();
  };

  return (
    <div>
      {/* Page header */}
      <div className="mb-8 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground tracking-tight">Experiments</h1>
          <p className="text-muted-foreground mt-1 text-sm font-mono">
            Manage and monitor your multi-agent trading experiments
          </p>
        </div>
        <button
          onClick={() => setDialogOpen(true)}
          className="
            flex items-center gap-2 px-4 py-2 rounded text-sm font-mono font-semibold
            bg-primary hover:bg-primary/90 text-primary-foreground
            transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2
            whitespace-nowrap flex-shrink-0
          "
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 1v12M1 7h12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          New Experiment
        </button>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 3 }).map((_, i) => (
            <ExperimentCardSkeleton key={i} />
          ))}
        </div>
      ) : error ? (
        <div className="rounded border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 px-6 py-4">
          <p className="text-sm font-mono text-red-700 dark:text-red-400">
            Failed to load experiments: {error.message}
          </p>
        </div>
      ) : experiments && experiments.length === 0 ? (
        <EmptyState
          icon="🧪"
          title="No experiments yet"
          description="Create your first experiment to start running multi-agent trading simulations."
          action={{ label: 'New Experiment', onClick: () => setDialogOpen(true) }}
        />
      ) : (
        <ExperimentList experiments={experiments ?? []} />
      )}

      {/* New experiment dialog */}
      <NewExperimentDialog
        open={dialogOpen}
        onClose={handleCloseDialog}
        onCreate={handleCreate}
        isLoading={createMutation.isPending}
        error={createMutation.error?.message ?? null}
      />
    </div>
  );
}
