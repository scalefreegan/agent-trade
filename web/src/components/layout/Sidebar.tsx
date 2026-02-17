import { Link, useLocation } from 'react-router-dom';

interface SidebarProps {
  onClose?: () => void;
}

export function Sidebar({ onClose }: SidebarProps) {
  const location = useLocation();

  const isActive = (path: string) =>
    location.pathname === path
      ? 'bg-brand-800 text-white'
      : 'text-gray-300 hover:bg-brand-900 hover:text-white';

  return (
    <div className="w-64 h-full bg-brand-900 dark:bg-gray-950 text-white flex flex-col">
      {/* Logo */}
      <div className="p-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-brand-400">Agent Trade</h1>
          <p className="text-xs font-mono text-brand-300 mt-0.5 uppercase tracking-widest">
            Multi-Agent Trading
          </p>
        </div>
        {/* Close button (mobile only) */}
        {onClose && (
          <button
            onClick={onClose}
            className="lg:hidden text-brand-300 hover:text-white transition-colors p-1 rounded"
            aria-label="Close sidebar"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path
                d="M2 2l14 14M16 2L2 16"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </button>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 px-4 space-y-1">
        <Link
          to="/"
          className={`flex items-center px-4 py-3 rounded-lg transition-colors ${isActive('/')}`}
          onClick={onClose}
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 18 18"
            fill="none"
            className="mr-3 flex-shrink-0"
          >
            <rect x="1" y="9" width="4" height="8" rx="1" fill="currentColor" opacity="0.6" />
            <rect x="7" y="5" width="4" height="12" rx="1" fill="currentColor" opacity="0.8" />
            <rect x="13" y="1" width="4" height="16" rx="1" fill="currentColor" />
          </svg>
          <span className="text-sm font-medium">Dashboard</span>
        </Link>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-brand-800 dark:border-gray-800">
        <p className="text-xs font-mono text-brand-300 dark:text-gray-600">Agent Trade v1.0</p>
      </div>
    </div>
  );
}
