import { Link, useLocation } from 'react-router-dom';
import { DashboardIcon } from '../../assets/icons/DashboardIcon';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const location = useLocation();

  const isActive = (path: string) =>
    location.pathname === path
      ? 'bg-white/15 text-white'
      : 'text-white/70 hover:bg-white/10 hover:text-white';

  return (
    <div
      className={`
        flex-shrink-0 h-full bg-sidebar-bg text-sidebar-foreground flex flex-col
        transition-all duration-200 ease-in-out overflow-hidden
        ${collapsed ? 'w-12' : 'w-64'}
      `}
    >
      {/* Logo */}
      <div className={`flex items-center flex-shrink-0 ${collapsed ? 'justify-center px-0 py-6' : 'p-6'}`}>
        {collapsed ? (
          <span className="text-xl font-bold text-white leading-none">A</span>
        ) : (
          <div>
            <h1 className="text-2xl font-bold text-white">Agent Trade</h1>
            <p className="text-xs text-white/60 mt-0.5 uppercase tracking-widest">Multi-Agent Trading</p>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 flex flex-col px-1.5 space-y-1 overflow-hidden">
        <Link
          to="/"
          title={collapsed ? 'Dashboard' : undefined}
          className={`flex items-center rounded-lg transition-colors ${isActive('/')} ${
            collapsed ? 'justify-center px-0 py-3' : 'px-4 py-3'
          }`}
        >
          <DashboardIcon className="w-5 h-5 shrink-0" />
          {!collapsed && <span className="ml-3 text-sm font-medium whitespace-nowrap">Dashboard</span>}
        </Link>
      </nav>

      {/* Collapse toggle */}
      <div className={`flex-shrink-0 border-t border-white/10 ${collapsed ? 'p-1.5' : 'p-3'}`}>
        <button
          onClick={onToggle}
          className="w-full flex items-center justify-center rounded-lg py-2 text-white/40 hover:text-white hover:bg-white/10 transition-colors"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            className={`transition-transform duration-200 ${collapsed ? 'rotate-180' : ''}`}
          >
            <path
              d="M10 3L5 8l5 5"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          {!collapsed && (
            <span className="ml-2 text-xs font-mono">Collapse</span>
          )}
        </button>
      </div>
    </div>
  );
}
