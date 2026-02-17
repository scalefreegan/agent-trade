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

function resolveVar(varName: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
}

function buildTheme(): ChartTheme {
  const isDark = document.documentElement.classList.contains('dark');

  return {
    grid: resolveVar('--border-color'),
    axis: resolveVar('--muted-foreground'),
    axisStroke: resolveVar('--border-color'),
    tooltip: {
      bg: resolveVar('--card'),
      border: resolveVar('--border-color'),
      text: resolveVar('--foreground'),
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
    gainColor: resolveVar('--gain'),
    lossColor: resolveVar('--loss'),
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
  const [chartTheme, setChartTheme] = useState<ChartTheme>(buildTheme);

  useEffect(() => {
    // Re-resolve after the DOM has applied the new class
    const id = requestAnimationFrame(() => setChartTheme(buildTheme()));
    return () => cancelAnimationFrame(id);
  }, [theme]);

  return chartTheme;
}
