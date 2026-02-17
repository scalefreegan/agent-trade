import { Link, useLocation } from 'react-router-dom';
import { DashboardIcon } from '../../assets/icons/DashboardIcon';

interface SidebarProps {
  onClose?: () => void;
}

export function Sidebar({ onClose }: SidebarProps) {
  const location = useLocation();

  const isActive = (path: string) =>
    location.pathname === path
      ? 'bg-white/15 text-white'
      : 'text-white/70 hover:bg-white/10 hover:text-white';

  return (
    <div className="w-64 flex-shrink-0 h-full bg-sidebar-bg text-sidebar-foreground flex flex-col">
      {/* Logo */}
      <div className="p-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Agent Trade</h1>
          <p className="text-xs text-white/60 mt-0.5 uppercase tracking-widest">Multi-Agent Trading</p>
        </div>
        {/* Close button (mobile only) */}
        {onClose && (
          <button
            onClick={onClose}
            className="lg:hidden text-white/60 hover:text-white transition-colors p-1 rounded"
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
          <DashboardIcon className="w-5 h-5 mr-3 shrink-0" />
          <span className="text-sm font-medium">Dashboard</span>
        </Link>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-white/10">
        <p className="text-xs font-mono text-white/40">Agent Trade v1.0</p>
      </div>
    </div>
  );
}
