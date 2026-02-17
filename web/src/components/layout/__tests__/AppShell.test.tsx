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

/** Returns the mobile drawer element directly — works when aria-hidden hides it from role queries. */
function getDrawer() {
  return document.getElementById('mobile-nav') as HTMLElement;
}

describe('AppShell — mobile drawer', () => {
  it('hamburger button opens the mobile drawer', () => {
    renderAppShell();
    expect(getDrawer()).toHaveClass('-translate-x-full');

    fireEvent.click(screen.getByRole('button', { name: /open menu/i }));

    expect(getDrawer()).not.toHaveClass('-translate-x-full');
    expect(getDrawer()).toHaveClass('translate-x-0');
  });

  it('backdrop click closes the drawer', () => {
    renderAppShell();
    fireEvent.click(screen.getByRole('button', { name: /open menu/i }));

    fireEvent.click(screen.getByTestId('mobile-overlay'));

    expect(getDrawer()).toHaveClass('-translate-x-full');
  });

  it('close button inside drawer closes the drawer', () => {
    renderAppShell();
    fireEvent.click(screen.getByRole('button', { name: /open menu/i }));

    fireEvent.click(screen.getByRole('button', { name: /close menu/i }));

    expect(getDrawer()).toHaveClass('-translate-x-full');
  });

  it('Escape key closes the drawer', () => {
    renderAppShell();
    fireEvent.click(screen.getByRole('button', { name: /open menu/i }));

    fireEvent.keyDown(document, { key: 'Escape' });

    expect(getDrawer()).toHaveClass('-translate-x-full');
  });

  it('mobile dashboard link closes the drawer', () => {
    renderAppShell();
    fireEvent.click(screen.getByRole('button', { name: /open menu/i }));

    const mobileNav = getDrawer().querySelector('nav') as HTMLElement;
    fireEvent.click(mobileNav.querySelector('a') as HTMLAnchorElement);

    expect(getDrawer()).toHaveClass('-translate-x-full');
  });

  it('drawer has role="dialog", aria-modal="true", and id="mobile-nav"', () => {
    renderAppShell();
    const drawer = getDrawer();
    expect(drawer).toHaveAttribute('role', 'dialog');
    expect(drawer).toHaveAttribute('aria-modal', 'true');
  });

  it('drawer is aria-hidden and inert when closed', () => {
    renderAppShell();
    const drawer = getDrawer();
    expect(drawer).toHaveAttribute('aria-hidden', 'true');
    expect(drawer).toHaveAttribute('inert');
  });

  it('drawer is not aria-hidden when open', () => {
    renderAppShell();
    fireEvent.click(screen.getByRole('button', { name: /open menu/i }));

    const drawer = getDrawer();
    expect(drawer).toHaveAttribute('aria-hidden', 'false');
    expect(drawer).not.toHaveAttribute('inert');
  });

  it('hamburger aria-expanded reflects drawer state', () => {
    renderAppShell();
    const hamburger = screen.getByRole('button', { name: /open menu/i });
    expect(hamburger).toHaveAttribute('aria-expanded', 'false');

    fireEvent.click(hamburger);
    expect(hamburger).toHaveAttribute('aria-expanded', 'true');

    fireEvent.click(screen.getByRole('button', { name: /close menu/i }));
    expect(hamburger).toHaveAttribute('aria-expanded', 'false');
  });

  it('hamburger aria-controls points to the mobile drawer id', () => {
    renderAppShell();
    const hamburger = screen.getByRole('button', { name: /open menu/i });
    expect(hamburger).toHaveAttribute('aria-controls', 'mobile-nav');
    expect(document.getElementById('mobile-nav')).toBeInTheDocument();
  });

  it('main content gets inert attribute while drawer is open', () => {
    renderAppShell();
    fireEvent.click(screen.getByRole('button', { name: /open menu/i }));

    const main = document.querySelector('main')?.parentElement as HTMLElement;
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
