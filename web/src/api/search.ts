// TanStack Query hooks for stock search
import { useQuery } from '@tanstack/react-query';
import { fetchApi } from './client';
import type {
  TickerSearchResponse,
  StockInfo,
  HistoricalPriceResponse,
  StockNewsResponse,
} from './types';

export function useTickerSearch(query: string) {
  return useQuery({
    queryKey: ['tickerSearch', query],
    queryFn: () =>
      fetchApi<TickerSearchResponse>(
        `/search/autocomplete?q=${encodeURIComponent(query)}`
      ),
    enabled: query.length >= 1,
    staleTime: 60 * 1000,
    placeholderData: (prev) => prev,
  });
}

export function useStockInfo(symbol: string | null) {
  return useQuery({
    queryKey: ['stockInfo', symbol],
    queryFn: () => fetchApi<StockInfo>(`/search/stocks/${symbol}`),
    enabled: !!symbol,
    staleTime: 60 * 1000,
  });
}

export function useStockHistory(
  symbol: string | null,
  period: string = '1mo'
) {
  return useQuery({
    queryKey: ['stockHistory', symbol, period],
    queryFn: () =>
      fetchApi<HistoricalPriceResponse>(
        `/search/stocks/${symbol}/history?period=${period}`
      ),
    enabled: !!symbol,
    staleTime: 60 * 1000,
  });
}

export function useStockNews(symbol: string | null) {
  return useQuery({
    queryKey: ['stockNews', symbol],
    queryFn: () =>
      fetchApi<StockNewsResponse>(`/search/stocks/${symbol}/news?limit=15`),
    enabled: !!symbol,
    staleTime: 5 * 60 * 1000,
  });
}
