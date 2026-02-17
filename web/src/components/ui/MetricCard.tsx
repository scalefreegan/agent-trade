import type { ReactNode } from 'react';

interface MetricCardProps {
  label: string;
  value: ReactNode;
  secondary?: ReactNode;
  className?: string;
}

export function MetricCard({ label, value, secondary, className = '' }: MetricCardProps) {
  return (
    <div className={className}>
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="text-lg font-medium text-foreground mt-0.5">{value}</p>
      {secondary && <p className="text-xs text-muted-foreground mt-0.5">{secondary}</p>}
    </div>
  );
}
