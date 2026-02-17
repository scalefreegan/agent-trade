import type { CSSProperties, MouseEventHandler, ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  padding?: boolean;
  onClick?: MouseEventHandler<HTMLDivElement>;
  style?: CSSProperties;
}

export function Card({ children, className = '', padding = true, onClick, style }: CardProps) {
  return (
    <div
      className={`bg-card text-card-foreground rounded-xl border border-border shadow-card ${padding ? 'p-6' : ''} ${className}`}
      onClick={onClick}
      style={style}
    >
      {children}
    </div>
  );
}
