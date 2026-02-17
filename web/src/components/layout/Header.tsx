import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';

interface HeaderProps {
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
}

function useDarkMode() {
  const [dark, setDark] = useState(() => {
    if (typeof window === 'undefined') return false;
    const stored = localStorage.getItem('theme');
    if (stored) return stored === 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    const root = document.documentElement;
    if (dark) {
      root.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      root.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [dark]);

  return [dark, setDark] as const;
}

function useBreadcrumb() {
  const location = useLocation();
  const parts = location.pathname.split('/').filter(Boolean);
  if (parts.length === 0) return 'Dashboard';
  if (parts[0] === 'experiments') {
    if (parts.length === 1) return 'Experiments';
    if (parts.length === 2) return `Experiment · ${parts[1]}`;
    if (parts[2] === 'agents' && parts[3]) return `Agent · ${parts[3]}`;
  }
  return parts[parts.length - 1];
}

export function Header({ onToggleSidebar }: HeaderProps) {
  const [dark, setDark] = useDarkMode();
  const label = useBreadcrumb();

  return (
    <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 px-4 py-3 flex items-center gap-4 flex-shrink-0">
      {/* Sidebar toggle */}
      <button
        onClick={onToggleSidebar}
        className="p-1.5 rounded text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
        aria-label="Toggle sidebar"
      >
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
          <path d="M2 4h14M2 9h14M2 14h14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </button>

      {/* Breadcrumb */}
      <p className="text-sm font-mono text-gray-500 dark:text-gray-400 truncate flex-1">
        {label}
      </p>

      {/* Dark mode toggle */}
      <button
        onClick={() => setDark((d) => !d)}
        className="p-1.5 rounded text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
        aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
        title={dark ? 'Light mode' : 'Dark mode'}
      >
        {dark ? (
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <circle cx="9" cy="9" r="4" stroke="currentColor" strokeWidth="1.5" />
            <path
              d="M9 1v2M9 15v2M1 9h2M15 9h2M3.22 3.22l1.42 1.42M13.36 13.36l1.42 1.42M3.22 14.78l1.42-1.42M13.36 4.64l1.42-1.42"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
          </svg>
        ) : (
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path
              d="M15 10.5A6 6 0 017.5 3a6.5 6.5 0 100 12A6 6 0 0115 10.5z"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinejoin="round"
            />
          </svg>
        )}
      </button>
    </header>
  );
}
