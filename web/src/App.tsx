import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from './context/ThemeContext';
import { AppShell } from './components/layout/AppShell';
import { DashboardPage } from './pages/DashboardPage';
import { ExperimentPage } from './pages/ExperimentPage';
import { AgentPage } from './pages/AgentPage';
import { SearchPage } from './pages/SearchPage';
import { PredictionMarketsPage } from './pages/PredictionMarketsPage';
import { AdvisorPage } from './pages/AdvisorPage';
import { ConversationPage } from './pages/ConversationPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { ErrorBoundary } from './components/ui/ErrorBoundary';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function FeatureErrorFallback({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[40vh] text-center px-4">
      <p className="text-sm font-mono font-semibold uppercase tracking-widest text-red-500 mb-2">
        Something went wrong
      </p>
      <p className="text-sm text-muted-foreground mb-4 max-w-sm">
        {error.message || 'An unexpected error occurred in this section.'}
      </p>
      <button
        onClick={reset}
        className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
      >
        Try again
      </button>
    </div>
  );
}

function featureFallback(error: Error, reset: () => void) {
  return <FeatureErrorFallback error={error} reset={reset} />;
}

function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <ErrorBoundary>
            <AppShell>
              <Routes>
                <Route path="/" element={<ErrorBoundary fallback={featureFallback}><DashboardPage /></ErrorBoundary>} />
                <Route path="/experiments/:experimentId" element={<ErrorBoundary fallback={featureFallback}><ExperimentPage /></ErrorBoundary>} />
                <Route path="/experiments/:experimentId/agents/:agentId" element={<ErrorBoundary fallback={featureFallback}><AgentPage /></ErrorBoundary>} />
                <Route path="/search" element={<ErrorBoundary fallback={featureFallback}><SearchPage /></ErrorBoundary>} />
                <Route path="/predictions" element={<ErrorBoundary fallback={featureFallback}><PredictionMarketsPage /></ErrorBoundary>} />
                <Route path="/advisor" element={<ErrorBoundary fallback={featureFallback}><AdvisorPage /></ErrorBoundary>} />
                <Route path="/chat" element={<ErrorBoundary fallback={featureFallback}><ConversationPage /></ErrorBoundary>} />
                <Route path="*" element={<NotFoundPage />} />
              </Routes>
            </AppShell>
          </ErrorBoundary>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

export default App;
