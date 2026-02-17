import { useState } from 'react';
import { ExperimentCard } from './ExperimentCard';
import { useDeleteExperiment } from '../../api/experiments';
import type { ExperimentListItem } from '../../api/types';

interface ExperimentListProps {
  experiments: ExperimentListItem[];
}

export function ExperimentList({ experiments }: ExperimentListProps) {
  const deleteMutation = useDeleteExperiment();
  const [pendingDelete, setPendingDelete] = useState<string | null>(null);

  const handleDeleteRequest = (id: string) => setPendingDelete(id);

  const handleDeleteConfirm = () => {
    if (!pendingDelete) return;
    deleteMutation.mutate(pendingDelete, {
      onSuccess: () => setPendingDelete(null),
      onError: () => setPendingDelete(null),
    });
  };

  if (experiments.length === 0) {
    return null; // Parent handles empty state
  }

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {experiments.map((experiment) => (
          <ExperimentCard
            key={experiment.id}
            experiment={experiment}
            onDelete={() => handleDeleteRequest(experiment.id)}
          />
        ))}
      </div>

      {/* Delete confirmation dialog */}
      {pendingDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setPendingDelete(null)} />
          <div className="relative w-full max-w-sm bg-white dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 shadow-2xl overflow-hidden">
            <div className="h-1 bg-red-500" />
            <div className="px-6 py-5">
              <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-1">
                Delete experiment?
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 font-mono">
                This will permanently delete the experiment and all its data. This action cannot be undone.
              </p>
              <div className="mt-5 flex gap-3 justify-end">
                <button
                  onClick={() => setPendingDelete(null)}
                  disabled={deleteMutation.isPending}
                  className="px-4 py-2 text-sm font-mono text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white disabled:opacity-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeleteConfirm}
                  disabled={deleteMutation.isPending}
                  className="
                    px-4 py-2 text-sm font-mono font-semibold rounded
                    bg-red-600 hover:bg-red-700 text-white
                    disabled:opacity-60 disabled:cursor-not-allowed
                    transition-colors flex items-center gap-2
                  "
                >
                  {deleteMutation.isPending && (
                    <svg className="animate-spin h-3.5 w-3.5 text-white" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                  )}
                  Delete
                </button>
              </div>
              {deleteMutation.error && (
                <p className="mt-3 text-xs font-mono text-red-600 dark:text-red-400">
                  {deleteMutation.error.message}
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
