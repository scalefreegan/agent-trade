type BadgeVariant = 'success' | 'warning' | 'error' | 'info' | 'neutral';

interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  className?: string;
}

const variantClasses: Record<BadgeVariant, string> = {
  success: 'bg-gain/15 text-gain',
  warning: 'bg-warning/15 text-warning',
  error: 'bg-loss/15 text-loss',
  info: 'bg-primary/15 text-primary',
  neutral: 'bg-muted text-muted-foreground',
};

export function Badge({ variant = 'neutral', children, className = '' }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${variantClasses[variant]} ${className}`}
    >
      {children}
    </span>
  );
}

/** Map a status string to a badge variant */
export function statusVariant(status: string): BadgeVariant {
  switch (status.toLowerCase()) {
    case 'active':
    case 'complete':
    case 'completed':
      return 'success';
    case 'running':
      return 'info';
    case 'paused':
      return 'warning';
    case 'error':
    case 'eliminated':
      return 'error';
    default:
      return 'neutral';
  }
}
