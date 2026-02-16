/**
 * Brand color palette for agent chart lines.
 * Top-ranked agents get the deepest green.
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
