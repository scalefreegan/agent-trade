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
        <div className="mb-4 w-14 h-14 rounded border border-border bg-muted flex items-center justify-center text-2xl select-none">
          {icon}
        </div>
      )}

      <h3 className="text-base font-semibold text-foreground tracking-tight mb-1">
        {title}
      </h3>

      {description && (
        <p className="text-sm text-muted-foreground font-mono max-w-xs leading-relaxed">
          {description}
        </p>
      )}

      {action && (
        <button
          onClick={action.onClick}
          className="
            mt-5 px-5 py-2 rounded text-sm font-mono font-semibold
            bg-primary hover:bg-primary/90 text-primary-foreground
            transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-background
          "
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
