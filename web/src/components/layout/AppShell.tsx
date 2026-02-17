import { useState, useEffect, useRef, type ReactNode } from 'react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const hamburgerRef = useRef<HTMLButtonElement>(null);
  const drawerCloseRef = useRef<HTMLButtonElement>(null);

  // Escape key closes drawer
  useEffect(() => {
    if (!mobileOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMobileOpen(false);
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [mobileOpen]);

  // Focus management: into drawer on open, back to hamburger on close
  useEffect(() => {
    if (mobileOpen) {
      drawerCloseRef.current?.focus();
    } else {
      hamburgerRef.current?.focus();
    }
  }, [mobileOpen]);

  return (
    <div className="flex h-screen bg-background">
      {/* Mobile overlay backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/50 xl:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      <Sidebar
        collapsed={collapsed}
        onToggle={() => setCollapsed((c) => !c)}
        mobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
        closeButtonRef={drawerCloseRef}
      />

      <div
        className="flex-1 flex flex-col overflow-hidden min-w-0"
        aria-hidden={mobileOpen ? true : undefined}
        inert={mobileOpen ? true : undefined}
      >
        <Header onMenuClick={() => setMobileOpen((o) => !o)} hamburgerRef={hamburgerRef} />
        <main className="flex-1 overflow-y-auto p-6">
          <div className="max-w-7xl mx-auto">{children}</div>
        </main>
      </div>
    </div>
  );
}
