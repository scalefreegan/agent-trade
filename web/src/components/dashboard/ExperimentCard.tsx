import { Link } from 'react-router-dom';
import type { ExperimentListItem } from '../../api/types';

interface ExperimentCardProps {
  experiment: ExperimentListItem;
}

export function ExperimentCard({ experiment }: ExperimentCardProps) {
  const statusColor = {
    active: 'bg-brand-600 text-white',
    paused: 'bg-yellow-500 text-white',
    completed: 'bg-gray-500 text-white',
  }[experiment.status] || 'bg-gray-400 text-white';

  return (
    <Link
      to={`/experiments/${experiment.id}`}
      className="block bg-white rounded-lg shadow hover:shadow-lg transition-shadow p-6 border border-gray-200"
    >
      <div className="flex items-start justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">{experiment.name}</h3>
        <span className={`px-3 py-1 rounded-full text-xs font-medium ${statusColor}`}>
          {experiment.status}
        </span>
      </div>
      <div className="space-y-2 text-sm text-gray-600">
        <div className="flex justify-between">
          <span>Created:</span>
          <span className="font-medium text-gray-900">
            {new Date(experiment.created_at).toLocaleDateString()}
          </span>
        </div>
        <div className="flex justify-between">
          <span>Agents:</span>
          <span className="font-medium text-gray-900">{experiment.num_agents}</span>
        </div>
        {experiment.current_day !== null && (
          <div className="flex justify-between">
            <span>Trading Day:</span>
            <span className="font-medium text-gray-900">{experiment.current_day}</span>
          </div>
        )}
      </div>
    </Link>
  );
}
