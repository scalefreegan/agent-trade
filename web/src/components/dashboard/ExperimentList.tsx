import { ExperimentCard } from './ExperimentCard';
import type { ExperimentListItem } from '../../api/types';

interface ExperimentListProps {
  experiments: ExperimentListItem[];
}

export function ExperimentList({ experiments }: ExperimentListProps) {
  if (experiments.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500 text-lg">No experiments found</p>
        <p className="text-gray-400 text-sm mt-2">
          Create your first experiment using the CLI
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {experiments.map((experiment) => (
        <ExperimentCard key={experiment.id} experiment={experiment} />
      ))}
    </div>
  );
}
