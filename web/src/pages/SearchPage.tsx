import { useSearchParams } from 'react-router-dom';
import { useStockInfo } from '../api/search';
import { SearchInput } from '../components/search/SearchInput';
import { StockOverview } from '../components/search/StockOverview';
import { StockChart } from '../components/search/StockChart';
import { StockNews } from '../components/search/StockNews';

export function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const symbol = searchParams.get('symbol');

  const { data: stock, isLoading, error } = useStockInfo(symbol);

  const handleSelect = (sym: string) => {
    setSearchParams({ symbol: sym });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground">Stock Search</h1>
      </div>

      <SearchInput onSelect={handleSelect} initialValue={symbol ?? ''} />

      {!symbol && (
        <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
          Search for a stock to see its details
        </div>
      )}

      {symbol && isLoading && (
        <div className="space-y-4">
          <div className="animate-pulse bg-card rounded-xl border border-border p-6">
            <div className="h-6 bg-muted rounded w-32 mb-2" />
            <div className="h-4 bg-muted rounded w-48 mb-4" />
            <div className="h-10 bg-muted rounded w-36 mb-6" />
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i}>
                  <div className="h-3 bg-muted rounded w-16 mb-1" />
                  <div className="h-5 bg-muted rounded w-24" />
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {symbol && error && (
        <div className="bg-loss/10 border border-loss/20 rounded-lg p-4 text-loss text-sm">
          Could not find stock information for &ldquo;{symbol}&rdquo;. Please check the symbol and try again.
        </div>
      )}

      {stock && (
        <div className="space-y-6">
          <StockOverview stock={stock} />
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <StockChart symbol={stock.symbol} />
            </div>
            <div>
              <StockNews symbol={stock.symbol} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
