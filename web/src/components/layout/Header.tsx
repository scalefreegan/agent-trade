import { type RefObject } from 'react';
import { useLocation, Link } from 'react-router-dom';
import { useTheme } from '../../context/ThemeContext';

interface HeaderProps {
  onMenuClick: () => void;
  hamburgerRef: RefObject<HTMLButtonElement | null>;
}

interface Crumb {
  label: string;
  to?: string;
}

/** Parse breadcrumbs from pathname so this works outside <Routes> context. */
function useBreadcrumbs(): Crumb[] {
  const { pathname } = useLocation();

  const crumbs: Crumb[] = [{ label: 'Dashboard', to: '/' }];

  const agentMatch = pathname.match(/^\/experiments\/([^/]+)\/agents\/([^/]+)/);
  const experimentMatch = pathname.match(/^\/experiments\/([^/]+)/);

  if (agentMatch) {
    const [, experimentId, agentId] = agentMatch;
    crumbs.push({ label: `Experiment ${experimentId}`, to: `/experiments/${experimentId}` });
    crumbs.push({ label: `Agent ${agentId}` });
  } else if (experimentMatch) {
    const [, experimentId] = experimentMatch;
    crumbs.push({ label: `Experiment ${experimentId}` });
  }

  return crumbs;
}

export function Header({ onMenuClick, hamburgerRef }: HeaderProps) {
  const { theme, toggleTheme } = useTheme();
  const crumbs = useBreadcrumbs();
  const isRoot = useLocation().pathname === '/';

  return (
    <header className="bg-card border-b border-border px-4 py-3 flex items-center gap-3 flex-shrink-0">
      {/* Hamburger — mobile only */}
      <button
        ref={hamburgerRef}
        onClick={onMenuClick}
        className="xl:hidden p-1.5 rounded-lg text-muted-foreground hover:bg-muted transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        aria-label="Open menu"
        aria-expanded={false}
        aria-controls="mobile-nav"
      >
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </button>

      {/* Breadcrumbs */}
      {!isRoot && (
        <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-sm min-w-0">
          {crumbs.map((crumb, i) => {
            const isLast = i === crumbs.length - 1;
            return (
              <span key={i} className="flex items-center gap-1.5 min-w-0">
                {i > 0 && (
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 14 14"
                    fill="none"
                    className="shrink-0 text-muted-foreground"
                    aria-hidden="true"
                  >
                    <path
                      d="M5 3l4 4-4 4"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                )}
                {crumb.to ? (
                  <Link
                    to={crumb.to}
                    aria-current={isLast ? 'page' : undefined}
                    className="text-muted-foreground hover:text-foreground transition-colors truncate focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded"
                  >
                    {crumb.label}
                  </Link>
                ) : (
                  <span aria-current="page" className="text-foreground font-medium truncate">
                    {crumb.label}
                  </span>
                )}
              </span>
            );
          })}
        </nav>
      )}

      <div className="flex-1" />

      {/* Dark mode toggle */}
      <button
        onClick={toggleTheme}
        className="p-1.5 rounded-lg text-muted-foreground hover:bg-muted transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        title={theme === 'dark' ? 'Light mode' : 'Dark mode'}
      >
        {theme === 'dark' ? (
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
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
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
          </svg>
        )}
      </button>
    </header>
  );
}
