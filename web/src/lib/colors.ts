/**
 * Brand color palette for agent chart lines.
 * Top-ranked agents get the deepest green.
 *
 * These hex values work in both light and dark mode because Recharts renders
 * them as SVG fill/stroke attributes (not CSS), so they cannot reference CSS
 * variables. The palette was chosen to be perceptually distinct on both the
 * light (#f8fafc) and dark (#0f172a) backgrounds used in this app.
 *
 * For theme-aware chart colors use the `useChartTheme` hook instead.
 */
export const CHART_COLORS = [
  '#007F5F', // brand-900: deep green
  '#2B9348', // brand-800: forest green
  '#55A630', // brand-700: green
  '#80B918', // brand-600: lime green
  '#AACC00', // brand-500: yellow-green
  '#BFD200', // brand-400: chartreuse
  '#D4D700', // brand-300: yellow-chartreuse
  '#DDDF00', // brand-200: yellow
  '#EEEF20', // brand-100: bright yellow
  '#FFFF3F', // brand-50: vivid yellow
];

/**
 * Get chart color for an agent based on rank.
 * Rank 1 (top) gets deepest green, subsequent ranks get progressively lighter colors.
 */
export function getChartColor(rank: number): string {
  const index = Math.min(rank - 1, CHART_COLORS.length - 1);
  return CHART_COLORS[index];
}

/**
 * Convert a `#rrggbb` hex string to an `rgba()` string with the given alpha.
 * Used for subtle tints derived from a resolved theme color.
 */
export function hexToRgba(hex: string, alpha: number): string {
  const h = hex.replace('#', '');
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
