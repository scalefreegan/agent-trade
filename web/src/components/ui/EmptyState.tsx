interface EmptyStateProps {
  icon?: string; // emoji
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
      {icon && (
        <div className="mb-4 w-14 h-14 rounded border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 flex items-center justify-center text-2xl select-none">
          {icon}
        </div>
      )}

      <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 tracking-tight mb-1">
        {title}
      </h3>

      {description && (
        <p className="text-sm text-gray-500 dark:text-gray-400 font-mono max-w-xs leading-relaxed">
          {description}
        </p>
      )}

      {action && (
        <button
          onClick={action.onClick}
          className="
            mt-5 px-5 py-2 rounded text-sm font-mono font-semibold
            bg-brand-700 hover:bg-brand-800 text-white
            transition-colors focus:outline-none focus:ring-2 focus:ring-brand-600 focus:ring-offset-2
            dark:focus:ring-offset-gray-900
          "
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
