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
