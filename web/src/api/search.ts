// TanStack Query hooks for stock search
import { useMutation, useQuery } from '@tanstack/react-query';
import { fetchApi, postApi } from './client';
import type {
  TickerSearchResponse,
  StockInfo,
  HistoricalPriceResponse,
  StockNewsResponse,
  NewsSummaryRequest,
  NewsSummaryJobResponse,
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

export function useStockNews(symbol: string | null, companyName?: string) {
  return useQuery({
    queryKey: ['stockNews', symbol, companyName],
    queryFn: () => {
      let url = `/search/stocks/${symbol}/news?limit=15`;
      if (companyName) {
        url += `&company_name=${encodeURIComponent(companyName)}`;
      }
      return fetchApi<StockNewsResponse>(url);
    },
    enabled: !!symbol,
    staleTime: 5 * 60 * 1000,
  });
}

export function useStartNewsSummary(symbol: string) {
  return useMutation({
    mutationFn: (body: NewsSummaryRequest) =>
      postApi<NewsSummaryJobResponse>(
        `/search/stocks/${symbol}/news/summary`,
        body
      ),
  });
}

export function useNewsSummaryStatus(symbol: string, jobId: string | null) {
  return useQuery({
    queryKey: ['newsSummary', symbol, jobId],
    queryFn: () =>
      fetchApi<NewsSummaryJobResponse>(
        `/search/stocks/${symbol}/news/summary/${jobId}`
      ),
    enabled: !!jobId,
    refetchInterval: (query) =>
      query.state.data?.status === 'running' ? 2000 : false,
  });
}
