import { useState, useEffect } from 'react';
import { useStockNews } from '../../api/search';
import { Card } from '../ui/Card';

interface StockNewsProps {
  symbol: string;
}

const ARTICLES_PER_PAGE = 3;

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
  const [currentPage, setCurrentPage] = useState(1);

  // Reset pagination when symbol changes or articles change
  useEffect(() => {
    setCurrentPage(1);
  }, [symbol, data?.count]);

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

  // Pagination
  const totalPages = Math.ceil(articles.length / ARTICLES_PER_PAGE);
  const startIndex = (currentPage - 1) * ARTICLES_PER_PAGE;
  const endIndex = startIndex + ARTICLES_PER_PAGE;
  const paginatedArticles = articles.slice(startIndex, endIndex);

  const goToPage = (page: number) => {
    setCurrentPage(Math.max(1, Math.min(page, totalPages)));
  };

  return (
    <Card padding={false} className="h-full flex flex-col">
      <div className="px-6 pt-6 pb-2">
        <h3 className="text-sm font-medium text-foreground">News</h3>
      </div>
      <div className="flex-1 divide-y divide-border overflow-y-auto min-h-0">
        {paginatedArticles.map((article, i) => (
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
      {totalPages > 1 && (
        <div className="px-6 py-4 border-t border-border flex items-center justify-between flex-shrink-0">
          <button
            onClick={() => goToPage(currentPage - 1)}
            disabled={currentPage === 1}
            className="px-3 py-1.5 text-sm font-medium text-foreground bg-muted rounded-lg hover:bg-muted/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Previous
          </button>
          <div className="flex items-center gap-1">
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
              <button
                key={page}
                onClick={() => goToPage(page)}
                className={`w-8 h-8 text-sm font-medium rounded-lg transition-colors ${
                  page === currentPage
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-muted'
                }`}
              >
                {page}
              </button>
            ))}
          </div>
          <button
            onClick={() => goToPage(currentPage + 1)}
            disabled={currentPage === totalPages}
            className="px-3 py-1.5 text-sm font-medium text-foreground bg-muted rounded-lg hover:bg-muted/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Next
          </button>
        </div>
      )}
    </Card>
  );
}
