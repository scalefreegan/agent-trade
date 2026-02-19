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
  status: string;
  portfolio: Portfolio;
  metrics: PortfolioMetrics;
  created_at: string;
  eliminated_at: string | null;
}

// ==============================================================================
// Holdings Info Types
// ==============================================================================

export interface BuyReason {
  date: string;
  reasoning: string;
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
