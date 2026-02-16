import { useExperiments } from '../api/experiments';
import { ExperimentList } from '../components/dashboard/ExperimentList';

export function DashboardPage() {
  const { data: experiments, isLoading, error } = useExperiments();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading experiments...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-red-500">Error loading experiments: {error.message}</div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Experiments</h1>
        <p className="text-gray-600 mt-2">
          Manage and monitor your multi-agent trading experiments
        </p>
      </div>
      <ExperimentList experiments={experiments || []} />
    </div>
  );
}
