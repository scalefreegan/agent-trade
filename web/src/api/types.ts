// TypeScript types mirroring backend Pydantic models

export interface ExperimentListItem {
  id: string;
  name: string;
  created_at: string;
  num_agents: number;
  status: string;
  current_day: number | null;
}

export interface ExperimentDetail {
  id: string;
  name: string;
  created_at: string;
  starting_capital: number;
  num_agents: number;
  status: string;
  current_day: number | null;
}

export interface TaxLot {
  shares: number;
  cost_basis: number;
  purchase_date: string; // ISO datetime string
}

export interface StockPosition {
  symbol: string;
  total_shares: number;
  total_cost_basis: number;
  current_price: number | null;
  current_value: number | null;
  unrealized_gain: number | null;
  lots: TaxLot[];
}

export interface Portfolio {
  cash: number;
  positions: Record<string, StockPosition>;
}

export interface AgentState {
  agent_id: string;
  name: string;
  portfolio: Portfolio;
  status: string;
}

export interface GameState {
  trading_day: number;
  last_run: string | null;
  agents: AgentState[];
}

// ==============================================================================
// Leaderboard & Performance Types
// ==============================================================================

export interface LeaderboardEntry {
  rank: number;
  agent_id: string;
  name: string;
  portfolio_value: number;
  returns_pct: number | null;
  status: string;
}

export interface LeaderboardResponse {
  entries: LeaderboardEntry[];
}

export interface PerformanceDataPoint {
  date: string; // ISO date string
  trading_day: number;
  values: Record<string, number>; // agent_id -> portfolio_value
}

export interface PerformanceResponse {
  data_points: PerformanceDataPoint[];
}

// ==============================================================================
// Agent Detail Types
// ==============================================================================

export interface PortfolioMetrics {
  total_value: number;
  unrealized_gain: number;
  unrealized_gain_pct: number;
  positions_count: number;
  cash_pct: number;
  invested_pct: number;
}

export interface InvestmentThesis {
  philosophy: string;
  risk_tolerance: string;
  preferred_sectors: string[];
  time_horizon: string;
  key_metrics: string[];
}

export interface StrategyLearning {
  date: string;
  observation: string;
  outcome: string;
  lesson: string;
}

export interface AgentStrategy {
  thesis: InvestmentThesis;
  rationale: string;
  learnings: StrategyLearning[];
  last_updated: string;
}

export interface TransactionRecord {
  date: string;
  action: 'BUY' | 'SELL';
  symbol: string;
  shares: number;
  price: number;
  total: number;
  tax_paid: number | null;
}

export interface TransactionHistory {
  transactions: TransactionRecord[];
  total_buy_volume: number;
  total_sell_volume: number;
  total_tax_paid: number;
}

export interface DecisionLogEntry {
  date: string;
  trading_day: number;
  has_orders: boolean;
  order_count: number;
}

export interface AgentDetail {
  agent_id: string;
  name: string;
  description: string | null;
  status: string;
  portfolio: Portfolio;
  metrics: PortfolioMetrics;
  created_at: string;
  eliminated_at: string | null;
  guidance: string | null;
}

export interface StrategyEditInput {
  philosophy?: string;
  risk_tolerance?: 'conservative' | 'moderate' | 'aggressive';
  preferred_sectors?: string[];
  time_horizon?: string;
  key_metrics?: string[];
  rationale?: string;
}

export interface StrategyUpdateResponse {
  updated: string[];
  message: string;
}

export interface GuidanceUpdateResponse {
  guidance: string | null;
  message: string;
}

export interface UpdateAgentResponse {
  agent_id: string;
  name: string;
  description: string | null;
}

// ==============================================================================
// Holdings Info Types
// ==============================================================================

export interface BuyReason {
  date: string;
  reasoning: string;
}

export interface PricePoint {
  date: string;
  close: number;
}

export interface HoldingRationale {
  symbol: string;
  total_shares: number;
  avg_cost_basis: number;
  current_price: number | null;
  current_value: number | null;
  unrealized_gain: number | null;
  first_buy_date: string;
  buy_reasons: BuyReason[];
  // Business / fundamental data
  company_name: string | null;
  sector: string | null;
  industry: string | null;
  market_cap: number | null;
  pe_ratio: number | null;
  fifty_two_week_high: number | null;
  fifty_two_week_low: number | null;
  business_summary: string | null;
  price_history: PricePoint[];
}

export interface HoldingsInfo {
  holdings: HoldingRationale[];
}

// ==============================================================================
// Alerts Types
// ==============================================================================

export interface AlertEntry {
  date: string;
  symbol: string;
  thesis: string;
  confidence: 'high' | 'very_high';
  catalyst: string;
  time_horizon: string;
}

export interface AlertsResponse {
  alerts: AlertEntry[];
  total_count: number;
}

// ==============================================================================
// Benchmark Types
// ==============================================================================

export interface BenchmarkDataPoint {
  date: string;
  value: number;
}

export interface BenchmarkSeries {
  symbol: string;
  label: string;
  data: BenchmarkDataPoint[];
}

export interface BenchmarkResponse {
  benchmarks: BenchmarkSeries[];
}

// ==============================================================================
// Experiment Creation Advanced Options Types
// ==============================================================================

export interface AgentInitHints {
  philosophy?: string;
  risk_tolerance?: 'conservative' | 'moderate' | 'aggressive';
  preferred_sectors?: string[];
  time_horizon?: string;
  key_metrics?: string[];
  rationale?: string;
}

export interface PortfolioPositionSpec {
  symbol: string;
  shares: number;
  cost_basis: number;
  purchase_date?: string; // ISO date string YYYY-MM-DD
}

export interface StartingPortfolioSpec {
  cash?: number;
  positions: PortfolioPositionSpec[];
}

// ==============================================================================
// Stock Search Types
// ==============================================================================

export interface TickerSearchResult {
  symbol: string;
  name: string;
  exchange: string | null;
  type: string | null;
}

export interface TickerSearchResponse {
  query: string;
  results: TickerSearchResult[];
  count: number;
}

export interface StockInfo {
  symbol: string;
  name: string | null;
  current_price: number | null;
  market_cap: number | null;
  sector: string | null;
  industry: string | null;
  pe_ratio: number | null;
  fifty_two_week_high: number | null;
  fifty_two_week_low: number | null;
  volume: number | null;
  average_volume: number | null;
  business_summary: string | null;
}

export interface HistoricalPricePoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface HistoricalPriceResponse {
  symbol: string;
  period: string;
  count: number;
  data: HistoricalPricePoint[];
  error: string | null;
}

export interface StockNewsArticle {
  title: string | null;
  description: string | null;
  url: string | null;
  source: string | null;
  published_at: string | null;
  tickers: string[];
}

export interface StockNewsResponse {
  symbol: string;
  count: number;
  articles: StockNewsArticle[];
  error: string | null;
}

// ==============================================================================
// Advisor Types
// ==============================================================================

export interface AdvisorPreset {
  id: string;
  name: string;
  philosophy: string;
  icon: string;
}

export interface AdvisorPresetsResponse {
  presets: AdvisorPreset[];
}

export interface AdvisorAgentConfig {
  name: string;
  philosophy: string;
  agent_id?: string; // For experiment agents - unique identifier
}

export interface AdvisorRequest {
  symbol: string;
  agents: AdvisorAgentConfig[];
  portfolio_value?: number;
}

export interface AdvisorRecommendation {
  agent_name: string;
  action: 'BUY' | 'SELL' | 'HOLD';
  confidence: number;
  target_price: number | null;
  current_price: number | null;
  amount_guidance: string;
  reasoning: string;
  risk_factors: string[];
  time_horizon: string;
}

export interface AdvisorJobStatus {
  job_id: string;
  symbol: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  started_at: string;
  completed_at: string | null;
  error: string | null;
  recommendations: AdvisorRecommendation[];
  total_agents: number;
  completed_agents: number;
}

export interface ExperimentAgentInfo {
  agent_id: string;
  name: string;
  philosophy: string;
}
