// Kalshi prediction markets API client and React Query hooks
import { useQuery } from '@tanstack/react-query';

const KALSHI_BASE = '/kalshi-api';

// TypeScript interfaces for Kalshi API responses
export interface KalshiMarket {
  ticker: string;
  title: string;
  status: string;
  volume: number;
  volume_24h: number;
  open_interest: number;
  yes_bid: number;
  yes_ask: number;
  no_bid: number;
  no_ask: number;
  last_price: number;
  close_time: string;
  created_time: string;
  event_ticker?: string;
  category?: string;
  subtitle?: string;
  // Added for URL construction
  eventTicker?: string;
  eventTitle?: string;
}

export interface KalshiEvent {
  ticker: string;
  title: string;
  category: string;
  sub_title?: string;
  mutually_exclusive: boolean;
  markets?: KalshiMarket[];
}

export interface KalshiEventsResponse {
  events: KalshiEvent[];
  cursor?: string;
}

export interface KalshiMarketsResponse {
  markets: KalshiMarket[];
  cursor?: string;
}

interface FetchKalshiParams {
  [key: string]: string | number | boolean | undefined;
}

// Custom fetch function for Kalshi API
async function fetchKalshi<T>(endpoint: string, params?: FetchKalshiParams): Promise<T> {
  const url = new URL(`${KALSHI_BASE}${endpoint}`, window.location.origin);

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        url.searchParams.append(key, String(value));
      }
    });
  }

  let response: Response;
  try {
    response = await fetch(url.toString());
  } catch (err) {
    console.error('Kalshi API network error:', err);
    throw new Error(`Network error: ${err instanceof Error ? err.message : 'Failed to reach Kalshi API'}`);
  }

  if (!response.ok) {
    const errorText = await response.text().catch((err) => {
      console.error('Failed to read error response:', err);
      return response.statusText;
    });
    throw new Error(`Kalshi API error: ${response.status} - ${errorText}`);
  }

  try {
    return await response.json();
  } catch (err) {
    console.error('Failed to parse Kalshi API response:', err);
    throw new Error('Invalid JSON response from Kalshi API');
  }
}

// React Query hooks
export interface UseKalshiEventsParams {
  status?: string;
  limit?: number;
  cursor?: string;
  with_nested_markets?: boolean;
}

export function useKalshiEvents(params: UseKalshiEventsParams = {}) {
  const {
    status,
    limit = 20,
    cursor,
    with_nested_markets = true,
  } = params;

  return useQuery({
    queryKey: ['kalshi-events', { status, limit, cursor, with_nested_markets }],
    queryFn: () =>
      fetchKalshi<KalshiEventsResponse>('/events', {
        status,
        limit,
        cursor,
        with_nested_markets,
      }),
    staleTime: 60_000, // 1 minute
  });
}

export interface UseKalshiMarketsParams {
  status?: string;
  limit?: number;
  cursor?: string;
  event_ticker?: string;
}

export function useKalshiMarkets(params: UseKalshiMarketsParams = {}) {
  const {
    status,
    limit = 40,
    cursor,
    event_ticker,
  } = params;

  return useQuery({
    queryKey: ['kalshi-markets', { status, limit, cursor, event_ticker }],
    queryFn: () =>
      fetchKalshi<KalshiMarketsResponse>('/markets', {
        status,
        limit,
        cursor,
        event_ticker,
      }),
    staleTime: 60_000, // 1 minute
  });
}
