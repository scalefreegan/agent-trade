import { type RefObject } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { DashboardIcon } from '../../assets/icons/DashboardIcon';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  mobileOpen: boolean;
  onMobileClose: () => void;
  closeButtonRef: RefObject<HTMLButtonElement | null>;
}

export function Sidebar({ collapsed, onToggle, mobileOpen, onMobileClose, closeButtonRef }: SidebarProps) {
  const location = useLocation();

  const isActive = (path: string) =>
    location.pathname === path
      ? 'bg-white/15 text-white'
      : 'text-white/70 hover:bg-white/10 hover:text-white';

  return (
    <>
      {/* Desktop sidebar — always visible, collapsible */}
      <div
        className={`
          hidden xl:flex
          flex-shrink-0 h-full bg-sidebar-bg text-sidebar-foreground flex-col
          transition-all duration-200 ease-in-out overflow-hidden
          ${collapsed ? 'w-12' : 'w-64'}
        `}
      >
        <SidebarContent collapsed={collapsed} onToggle={onToggle} isActive={isActive} />
      </div>

      {/* Mobile sidebar — slide-in drawer */}
      <div
        id="mobile-nav"
        role="dialog"
        aria-modal="true"
        aria-label="Navigation menu"
        className={`
          fixed inset-y-0 left-0 z-30 xl:hidden
          flex flex-col w-64 bg-sidebar-bg text-sidebar-foreground
          transition-transform duration-200 ease-in-out
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        {/* Mobile close button */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
          <div>
            <h1 className="text-lg font-bold text-white">Agent Trade</h1>
            <p className="text-xs text-white/60 uppercase tracking-widest">Multi-Agent Trading</p>
          </div>
          <button
            ref={closeButtonRef}
            onClick={onMobileClose}
            className="p-1.5 rounded-lg text-white/40 hover:text-white hover:bg-white/10 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50"
            aria-label="Close menu"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M3 3l10 10M13 3L3 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        <nav aria-label="Mobile navigation" className="flex-1 flex flex-col px-1.5 pt-3 space-y-1 overflow-hidden">
          <Link
            to="/"
            onClick={onMobileClose}
            aria-current={location.pathname === '/' ? 'page' : undefined}
            className={`flex items-center rounded-lg px-4 py-3 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50 ${isActive('/')}`}
          >
            <DashboardIcon className="w-5 h-5 shrink-0" />
            <span className="ml-3 text-sm font-medium whitespace-nowrap">Dashboard</span>
          </Link>
        </nav>
      </div>
    </>
  );
}

interface SidebarContentProps {
  collapsed: boolean;
  onToggle: () => void;
  isActive: (path: string) => string;
}

function SidebarContent({ collapsed, onToggle, isActive }: SidebarContentProps) {
  const location = useLocation();

  return (
    <>
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
      <nav aria-label="Desktop navigation" className="flex-1 flex flex-col px-1.5 space-y-1 overflow-hidden">
        <Link
          to="/"
          title={collapsed ? 'Dashboard' : undefined}
          aria-current={location.pathname === '/' ? 'page' : undefined}
          className={`flex items-center rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50 ${isActive('/')} ${
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
          className="w-full flex items-center justify-center rounded-lg py-2 text-white/40 hover:text-white hover:bg-white/10 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50"
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
          {!collapsed && <span className="ml-2 text-xs font-mono">Collapse</span>}
        </button>
      </div>
    </>
  );
}
