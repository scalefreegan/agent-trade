import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider } from '../../../context/ThemeContext';
import { AppShell } from '../AppShell';

function renderAppShell(initialPath = '/') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <ThemeProvider>
        <AppShell>
          <div>Page content</div>
        </AppShell>
      </ThemeProvider>
    </MemoryRouter>,
  );
}

describe('AppShell — mobile drawer', () => {
  it('hamburger button opens the mobile drawer', () => {
    renderAppShell();
    const drawer = screen.getByRole('dialog', { name: /navigation menu/i });
    expect(drawer).toHaveClass('-translate-x-full');

    const hamburger = screen.getByRole('button', { name: /open menu/i });
    fireEvent.click(hamburger);

    expect(drawer).not.toHaveClass('-translate-x-full');
    expect(drawer).toHaveClass('translate-x-0');
  });

  it('backdrop click closes the drawer', () => {
    renderAppShell();
    fireEvent.click(screen.getByRole('button', { name: /open menu/i }));

    const backdrop = document.querySelector('[aria-hidden="true"]') as HTMLElement;
    fireEvent.click(backdrop);

    const drawer = screen.getByRole('dialog', { name: /navigation menu/i });
    expect(drawer).toHaveClass('-translate-x-full');
  });

  it('close button inside drawer closes the drawer', () => {
    renderAppShell();
    fireEvent.click(screen.getByRole('button', { name: /open menu/i }));

    fireEvent.click(screen.getByRole('button', { name: /close menu/i }));

    const drawer = screen.getByRole('dialog', { name: /navigation menu/i });
    expect(drawer).toHaveClass('-translate-x-full');
  });

  it('Escape key closes the drawer', () => {
    renderAppShell();
    fireEvent.click(screen.getByRole('button', { name: /open menu/i }));

    fireEvent.keyDown(document, { key: 'Escape' });

    const drawer = screen.getByRole('dialog', { name: /navigation menu/i });
    expect(drawer).toHaveClass('-translate-x-full');
  });

  it('mobile dashboard link closes the drawer', () => {
    renderAppShell();
    fireEvent.click(screen.getByRole('button', { name: /open menu/i }));

    // Click the Dashboard link inside the mobile nav
    const mobileNav = screen.getByRole('navigation', { name: /mobile navigation/i });
    const dashboardLink = mobileNav.querySelector('a') as HTMLAnchorElement;
    fireEvent.click(dashboardLink);

    const drawer = screen.getByRole('dialog', { name: /navigation menu/i });
    expect(drawer).toHaveClass('-translate-x-full');
  });

  it('drawer has role="dialog" and aria-modal="true"', () => {
    renderAppShell();
    const drawer = screen.getByRole('dialog', { name: /navigation menu/i });
    expect(drawer).toHaveAttribute('aria-modal', 'true');
  });

  it('main content gets inert attribute while drawer is open', () => {
    renderAppShell();
    fireEvent.click(screen.getByRole('button', { name: /open menu/i }));

    const main = document.querySelector('main')?.parentElement as HTMLElement;
    // The flex wrapper div around header+main gets inert
    expect(main.hasAttribute('inert')).toBe(true);
  });
});

describe('AppShell — breadcrumbs', () => {
  it('does not show breadcrumbs on root route', () => {
    renderAppShell('/');
    expect(screen.queryByRole('navigation', { name: /breadcrumb/i })).toBeNull();
  });

  it('shows breadcrumbs on experiment route', () => {
    renderAppShell('/experiments/exp-1');
    const nav = screen.getByRole('navigation', { name: /breadcrumb/i });
    expect(nav).toBeInTheDocument();
    expect(nav).toHaveTextContent('Dashboard');
    expect(nav).toHaveTextContent('Experiment exp-1');
  });

  it('shows breadcrumbs on agent route', () => {
    renderAppShell('/experiments/exp-1/agents/agent-2');
    const nav = screen.getByRole('navigation', { name: /breadcrumb/i });
    expect(nav).toHaveTextContent('Dashboard');
    expect(nav).toHaveTextContent('Experiment exp-1');
    expect(nav).toHaveTextContent('Agent agent-2');
  });

  it('last breadcrumb item has aria-current="page"', () => {
    renderAppShell('/experiments/exp-1/agents/agent-2');
    const current = screen.getByText('Agent agent-2');
    expect(current).toHaveAttribute('aria-current', 'page');
  });

  it('intermediate breadcrumb items are links', () => {
    renderAppShell('/experiments/exp-1/agents/agent-2');
    const expLink = screen.getByRole('link', { name: /experiment exp-1/i });
    expect(expLink).toHaveAttribute('href', '/experiments/exp-1');
  });
});
