import { useEffect, useState } from 'react';
import { useTheme } from '../context/ThemeContext';

interface ChartTheme {
  grid: string;
  axis: string;
  axisStroke: string;
  tooltip: {
    bg: string;
    border: string;
    text: string;
  };
  // Brand green palette (resolved hex values)
  brandColors: string[];
  cashColor: string;
  primaryColor: string;
  gainColor: string;
  lossColor: string;
  // Semantic bar colors (resolved hex)
  shortTermColor: string;
  longTermColor: string;
  holdingBucketColors: Record<string, string>;
}

function resolveVar(varName: string, fallback = '#000000'): string {
  const value = getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
  return value || fallback;
}

function buildTheme(): ChartTheme {
  const isDark = document.documentElement.classList.contains('dark');

  return {
    grid: resolveVar('--border-color', '#e5e7eb'),
    axis: resolveVar('--muted-foreground', '#6b7280'),
    axisStroke: resolveVar('--border-color', '#e5e7eb'),
    tooltip: {
      bg: resolveVar('--card', '#ffffff'),
      border: resolveVar('--border-color', '#e5e7eb'),
      text: resolveVar('--foreground', '#111827'),
    },
    // Brand color palette — same hex in both themes (colors are perceptually distinct)
    brandColors: [
      '#007F5F',
      '#2B9348',
      '#55A630',
      '#80B918',
      '#AACC00',
      '#BFD200',
    ],
    cashColor: isDark ? '#64748b' : '#6B7280',
    primaryColor: isDark ? '#55A630' : '#007F5F',
    gainColor: resolveVar('--gain', '#059669'),
    lossColor: resolveVar('--loss', '#dc2626'),
    // Tax chart colors — adjusted for dark mode readability
    shortTermColor: isDark ? '#fbbf24' : '#f59e0b',
    longTermColor: isDark ? '#34d399' : '#059669',
    holdingBucketColors: {
      '0-30': isDark ? '#f87171' : '#dc2626',
      '31-90': isDark ? '#fbbf24' : '#f59e0b',
      '91-180': isDark ? '#facc15' : '#eab308',
      '181-365': isDark ? '#a3e635' : '#84cc16',
      '365+': isDark ? '#34d399' : '#059669',
    },
  };
}

export function useChartTheme(): ChartTheme {
  const { theme } = useTheme();

  // On cold load, the index.html inline script has already applied the .dark
  // class synchronously, so buildTheme() reads the correct class here.
  // On toggle, ThemeProvider.useLayoutEffect applies the class synchronously
  // before paint; the rAF below fires after that, so it too reads correctly.
  const [chartTheme, setChartTheme] = useState<ChartTheme>(buildTheme);

  useEffect(() => {
    // ThemeProvider uses useLayoutEffect, so the .dark class is always set
    // before this effect fires. The rAF defers the DOM read until after the
    // current paint cycle, ensuring getComputedStyle sees the updated values.
    const id = requestAnimationFrame(() => setChartTheme(buildTheme()));
    return () => cancelAnimationFrame(id);
  }, [theme]);

  return chartTheme;
}
