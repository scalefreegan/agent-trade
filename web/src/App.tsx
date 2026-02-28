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
import { ErrorBoundary } from './components/ui/ErrorBoundary';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <ErrorBoundary>
            <AppShell>
              <Routes>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/experiments/:experimentId" element={<ExperimentPage />} />
                <Route path="/experiments/:experimentId/agents/:agentId" element={<AgentPage />} />
                <Route path="/search" element={<SearchPage />} />
                <Route path="/predictions" element={<PredictionMarketsPage />} />
                <Route path="/advisor" element={<AdvisorPage />} />
                <Route path="/chat" element={<ConversationPage />} />
              </Routes>
            </AppShell>
          </ErrorBoundary>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

export default App;
