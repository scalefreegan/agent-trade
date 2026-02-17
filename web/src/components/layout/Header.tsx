import { useLocation } from 'react-router-dom';
import { useTheme } from '../../context/ThemeContext';

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

export function Header() {
  const { theme, toggleTheme } = useTheme();
  const label = useBreadcrumb();

  return (
    <header className="bg-card border-b border-border px-4 py-3 flex items-center gap-4 flex-shrink-0">
      {/* Breadcrumb */}
      <p className="text-sm font-mono text-muted-foreground truncate flex-1">{label}</p>

      {/* Dark mode toggle */}
      <button
        onClick={toggleTheme}
        className="p-1.5 rounded text-muted-foreground hover:bg-muted transition-colors"
        aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        title={theme === 'dark' ? 'Light mode' : 'Dark mode'}
      >
        {theme === 'dark' ? (
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="5" />
            <line x1="12" y1="1" x2="12" y2="3" />
            <line x1="12" y1="21" x2="12" y2="23" />
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
            <line x1="1" y1="12" x2="3" y2="12" />
            <line x1="21" y1="12" x2="23" y2="12" />
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
          </svg>
        ) : (
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
          </svg>
        )}
      </button>
    </header>
  );
}
