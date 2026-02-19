import { useStockNews } from '../../api/search';
import { Card } from '../ui/Card';

interface StockNewsProps {
  symbol: string;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '';
  try {
    return new Date(dateStr).toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

export function StockNews({ symbol }: StockNewsProps) {
  const { data, isLoading, error } = useStockNews(symbol);

  if (isLoading) {
    return (
      <Card>
        <h3 className="text-sm font-medium text-foreground mb-4">News</h3>
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="animate-pulse">
              <div className="h-4 bg-muted rounded w-3/4 mb-2" />
              <div className="h-3 bg-muted rounded w-full" />
            </div>
          ))}
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <h3 className="text-sm font-medium text-foreground mb-4">News</h3>
        <p className="text-sm text-loss">Failed to load news</p>
      </Card>
    );
  }

  const articles = data?.articles ?? [];

  if (articles.length === 0) {
    return (
      <Card>
        <h3 className="text-sm font-medium text-foreground mb-4">News</h3>
        <p className="text-sm text-muted-foreground">
          {data?.error || 'No news articles available'}
        </p>
      </Card>
    );
  }

  return (
    <Card padding={false}>
      <div className="px-6 pt-6 pb-2">
        <h3 className="text-sm font-medium text-foreground">News</h3>
      </div>
      <div className="divide-y divide-border">
        {articles.map((article, i) => (
          <a
            key={article.url ?? i}
            href={article.url ?? '#'}
            target="_blank"
            rel="noopener noreferrer"
            className="block px-6 py-3 hover:bg-muted/50 transition-colors"
          >
            <h4 className="text-sm font-medium text-foreground leading-snug">
              {article.title}
            </h4>
            {article.description && (
              <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                {article.description}
              </p>
            )}
            <div className="flex items-center gap-2 mt-1.5">
              {article.source && (
                <span className="text-xs font-medium text-primary">
                  {article.source}
                </span>
              )}
              {article.published_at && (
                <span className="text-xs text-muted-foreground">
                  {formatDate(article.published_at)}
                </span>
              )}
            </div>
          </a>
        ))}
      </div>
    </Card>
  );
}
