import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  useStockNews,
  useStartNewsSummary,
  useNewsSummaryStatus,
} from '../../api/search';
import { Card } from '../ui/Card';
import { Tabs } from '../ui/Tabs';

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

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

function Pagination({ currentPage, totalPages, onPageChange }: PaginationProps) {
  if (totalPages <= 1) return null;

  return (
    <div className="px-6 py-4 border-t border-border flex items-center justify-between flex-shrink-0">
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1}
        className="px-3 py-1.5 text-sm font-medium text-foreground bg-muted rounded-lg hover:bg-muted/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        Previous
      </button>
      <div className="flex items-center gap-1">
        {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
          <button
            key={page}
            onClick={() => onPageChange(page)}
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
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
        className="px-3 py-1.5 text-sm font-medium text-foreground bg-muted rounded-lg hover:bg-muted/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        Next
      </button>
    </div>
  );
}

export function StockNews({ symbol }: StockNewsProps) {
  const { data, isLoading, error } = useStockNews(symbol);
  const [activeTab, setActiveTab] = useState<'articles' | 'summary'>('articles');
  const [articlesPage, setArticlesPage] = useState(1);
  const [summaryPage, setSummaryPage] = useState(1);
  const [summaryJobId, setSummaryJobId] = useState<string | null>(null);

  const startSummaryMutation = useStartNewsSummary(symbol);
  const summaryStatus = useNewsSummaryStatus(symbol, summaryJobId);

  // Reset state when symbol changes
  useEffect(() => {
    setArticlesPage(1);
    setSummaryPage(1);
    setSummaryJobId(null);
    setActiveTab('articles');
  }, [symbol]);

  // Reset article page when articles change
  useEffect(() => {
    setArticlesPage(1);
  }, [data?.count]);

  const handleGenerateSummary = () => {
    const articles = data?.articles ?? [];
    if (articles.length === 0) return;

    startSummaryMutation.mutate(
      { articles },
      {
        onSuccess: (response) => {
          setSummaryJobId(response.job_id);
          setSummaryPage(1);
        },
      }
    );
  };

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

  // Articles pagination
  const articlesTotalPages = Math.ceil(articles.length / ARTICLES_PER_PAGE);
  const articlesStartIndex = (articlesPage - 1) * ARTICLES_PER_PAGE;
  const articlesEndIndex = articlesStartIndex + ARTICLES_PER_PAGE;
  const paginatedArticles = articles.slice(articlesStartIndex, articlesEndIndex);

  const handleArticlesPageChange = (page: number) => {
    setArticlesPage(Math.max(1, Math.min(page, articlesTotalPages)));
  };

  // Summary sections pagination
  const summarySections = summaryStatus.data?.sections ?? [];
  const summaryTotalPages = summarySections.length;
  const currentSection =
    summarySections.length > 0 ? summarySections[summaryPage - 1] : null;

  const handleSummaryPageChange = (page: number) => {
    setSummaryPage(Math.max(1, Math.min(page, summaryTotalPages)));
  };

  return (
    <Card padding={false} className="h-full flex flex-col">
      <div className="px-6 pt-6 pb-2 flex-shrink-0">
        <Tabs
          tabs={[
            { id: 'articles', label: 'Articles' },
            { id: 'summary', label: 'AI Summary' },
          ]}
          activeTab={activeTab}
          onChange={(tab) => setActiveTab(tab as 'articles' | 'summary')}
        />
      </div>

      {activeTab === 'articles' && (
        <>
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
          <Pagination
            currentPage={articlesPage}
            totalPages={articlesTotalPages}
            onPageChange={handleArticlesPageChange}
          />
        </>
      )}

      {activeTab === 'summary' && (
        <>
          <div className="flex-1 overflow-y-auto min-h-0 px-6 py-4">
            {!summaryJobId && (
              <div className="flex flex-col items-center justify-center h-full gap-4">
                <p className="text-sm text-muted-foreground text-center">
                  Generate an AI-powered summary analyzing these {articles.length}{' '}
                  articles
                </p>
                <button
                  onClick={handleGenerateSummary}
                  disabled={startSummaryMutation.isPending}
                  className="px-4 py-2 bg-primary text-primary-foreground text-sm font-medium rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {startSummaryMutation.isPending
                    ? 'Starting...'
                    : 'Generate AI Summary'}
                </button>
                {startSummaryMutation.isError && (
                  <p className="text-sm text-loss">
                    Failed to start summary generation
                  </p>
                )}
              </div>
            )}

            {summaryJobId && summaryStatus.data?.status === 'running' && (
              <div className="flex flex-col items-center justify-center h-full gap-4">
                <div className="animate-pulse space-y-3 w-full">
                  <div className="h-4 bg-muted rounded w-1/4" />
                  <div className="h-3 bg-muted rounded w-full" />
                  <div className="h-3 bg-muted rounded w-5/6" />
                  <div className="h-3 bg-muted rounded w-4/5" />
                </div>
                <p className="text-sm text-muted-foreground">
                  Analyzing {articles.length} articles...
                </p>
              </div>
            )}

            {summaryJobId && summaryStatus.data?.status === 'failed' && (
              <div className="flex flex-col items-center justify-center h-full gap-4">
                <p className="text-sm text-loss">
                  {summaryStatus.data.error || 'Summary generation failed'}
                </p>
                <button
                  onClick={handleGenerateSummary}
                  className="px-4 py-2 bg-primary text-primary-foreground text-sm font-medium rounded-lg hover:bg-primary/90 transition-colors"
                >
                  Retry
                </button>
              </div>
            )}

            {summaryJobId &&
              summaryStatus.data?.status === 'completed' &&
              currentSection && (
                <div className="prose prose-sm max-w-none">
                  <h3 className="text-base font-semibold text-foreground mb-3">
                    {currentSection.title}
                  </h3>
                  <div className="text-sm text-foreground leading-relaxed">
                    <ReactMarkdown>{currentSection.content}</ReactMarkdown>
                  </div>
                </div>
              )}
          </div>

          {summaryJobId && summaryStatus.data?.status === 'completed' && (
            <Pagination
              currentPage={summaryPage}
              totalPages={summaryTotalPages}
              onPageChange={handleSummaryPageChange}
            />
          )}
        </>
      )}
    </Card>
  );
}
