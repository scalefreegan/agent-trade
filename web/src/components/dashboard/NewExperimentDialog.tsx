import { useEffect, useRef, useReducer, useCallback } from 'react';
import { createPortal } from 'react-dom';
import type { CreateExperimentInput } from '../../api/experiments';
import type { AgentInitHints, PortfolioPositionSpec } from '../../api/types';

/** Internal row type — `id` is a stable key never sent to the server. */
interface PositionRow extends PortfolioPositionSpec {
  id: number;
}

let positionIdSeq = 0;
function nextPositionId(): number {
  return ++positionIdSeq;
}

interface NewExperimentDialogProps {
  open: boolean;
  onClose: () => void;
  onCreate: (data: CreateExperimentInput) => void;
  isLoading: boolean;
  error: string | null;
}

interface FormErrors {
  name?: string;
  num_agents?: string;
  starting_capital?: string;
  cash_override?: string;
}

const RISK_OPTIONS = ['conservative', 'moderate', 'aggressive'] as const;

interface FormState {
  name: string;
  numAgents: number;
  startingCapital: number;
  errors: FormErrors;
  showAdvanced: boolean;
  guidance: string;
  agentPhilosophy: string;
  agentRisk: string;
  agentSectors: string;
  agentHorizon: string;
  agentMetrics: string;
  agentRationale: string;
  cashOverride: string;
  positions: PositionRow[];
}

type FormAction =
  | { type: 'RESET' }
  | { type: 'SET_FIELD'; field: keyof Omit<FormState, 'positions' | 'errors'>; value: string | number | boolean }
  | { type: 'SET_ERRORS'; errors: FormErrors }
  | { type: 'ADD_POSITION' }
  | { type: 'REMOVE_POSITION'; id: number }
  | { type: 'UPDATE_POSITION'; id: number; field: keyof PortfolioPositionSpec; value: string | number };

const INITIAL_STATE: FormState = {
  name: '',
  numAgents: 10,
  startingCapital: 1000,
  errors: {},
  showAdvanced: false,
  guidance: '',
  agentPhilosophy: '',
  agentRisk: '',
  agentSectors: '',
  agentHorizon: '',
  agentMetrics: '',
  agentRationale: '',
  cashOverride: '',
  positions: [],
};

function formReducer(state: FormState, action: FormAction): FormState {
  switch (action.type) {
    case 'RESET':
      return INITIAL_STATE;
    case 'SET_FIELD':
      return { ...state, [action.field]: action.value };
    case 'SET_ERRORS':
      return { ...state, errors: action.errors };
    case 'ADD_POSITION':
      return { ...state, positions: [...state.positions, { id: nextPositionId(), symbol: '', shares: 0, cost_basis: 0 }] };
    case 'REMOVE_POSITION':
      return { ...state, positions: state.positions.filter((p) => p.id !== action.id) };
    case 'UPDATE_POSITION':
      return { ...state, positions: state.positions.map((p) => (p.id === action.id ? { ...p, [action.field]: action.value } : p)) };
  }
}

const inputClass =
  'w-full px-3 py-2.5 text-sm font-mono bg-gray-50 dark:bg-gray-800 border rounded transition-colors outline-none text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-600 focus:ring-2 focus:ring-brand-700 focus:border-brand-700 dark:focus:ring-brand-600 dark:focus:border-brand-600 border-gray-300 dark:border-gray-600';
const labelClass =
  'block text-xs font-mono font-semibold uppercase tracking-widest text-gray-500 dark:text-gray-400 mb-1.5';

export function NewExperimentDialog({
  open,
  onClose,
  onCreate,
  isLoading,
  error,
}: NewExperimentDialogProps) {
  const [state, dispatch] = useReducer(formReducer, INITIAL_STATE);
  const {
    name, numAgents, startingCapital, errors, showAdvanced,
    guidance, agentPhilosophy, agentRisk, agentSectors,
    agentHorizon, agentMetrics, agentRationale, cashOverride, positions,
  } = state;
  const nameRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      dispatch({ type: 'RESET' });
      setTimeout(() => nameRef.current?.focus(), 50);
    }
  }, [open]);

  const dialogRef = useRef<HTMLDivElement>(null);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
        return;
      }
      if (e.key === 'Tab' && dialogRef.current) {
        const focusable = dialogRef.current.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey) {
          if (document.activeElement === first) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    },
    [onClose],
  );

  useEffect(() => {
    if (!open) return;
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open, handleKeyDown]);

  const validate = (): boolean => {
    const next: FormErrors = {};
    if (!name.trim()) next.name = 'Name is required';
    else if (name.length > 100) next.name = 'Name must be 100 characters or fewer';
    if (numAgents < 1 || numAgents > 50) next.num_agents = 'Must be between 1 and 50';
    if (startingCapital < 100 || startingCapital > 1_000_000)
      next.starting_capital = 'Must be between $100 and $1,000,000';
    if (showAdvanced && cashOverride.trim() !== '') {
      const val = Number(cashOverride);
      if (!Number.isFinite(val) || val < 0)
        next.cash_override = 'Cash override must be a non-negative number';
    }
    dispatch({ type: 'SET_ERRORS', errors: next });
    return Object.keys(next).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    const payload: CreateExperimentInput = {
      name: name.trim(),
      num_agents: numAgents,
      starting_capital: startingCapital,
    };

    if (showAdvanced) {
      if (guidance.trim()) payload.guidance = guidance.trim();

      // Agent defaults — only include non-empty fields
      const agentDefaults: AgentInitHints = {};
      if (agentPhilosophy.trim()) agentDefaults.philosophy = agentPhilosophy.trim();
      if (agentRisk) agentDefaults.risk_tolerance = agentRisk as AgentInitHints['risk_tolerance'];
      const sectors = agentSectors.split(',').map((s) => s.trim()).filter(Boolean);
      if (sectors.length) agentDefaults.preferred_sectors = sectors;
      if (agentHorizon.trim()) agentDefaults.time_horizon = agentHorizon.trim();
      const metrics = agentMetrics.split(',').map((s) => s.trim()).filter(Boolean);
      if (metrics.length) agentDefaults.key_metrics = metrics;
      if (agentRationale.trim()) agentDefaults.rationale = agentRationale.trim();
      if (Object.keys(agentDefaults).length > 0) payload.agent_defaults = agentDefaults;

      // Starting portfolio
      const validPositions = positions.filter((p) => p.symbol.trim() && p.shares > 0 && p.cost_basis > 0);
      const hasCash = cashOverride.trim() !== '';
      if (hasCash || validPositions.length > 0) {
        payload.starting_portfolio = {
          // Strip internal `id` before sending to the server
          positions: validPositions.map(({ id: _id, ...p }) => ({
            ...p,
            symbol: p.symbol.trim().toUpperCase(),
          })),
          ...(hasCash ? { cash: Number(cashOverride) } : {}),
        };
      }
    }

    onCreate(payload);
  };

  const addPosition = () => dispatch({ type: 'ADD_POSITION' });
  const removePosition = (id: number) => dispatch({ type: 'REMOVE_POSITION', id });
  const updatePosition = (id: number, field: keyof PortfolioPositionSpec, value: string | number) =>
    dispatch({ type: 'UPDATE_POSITION', id, field, value });

  if (!open) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="dialog-title"
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

      {/* Panel */}
      <div ref={dialogRef} className="relative w-full max-w-2xl bg-white dark:bg-gray-900 shadow-2xl border border-gray-200 dark:border-gray-700 rounded overflow-hidden max-h-[90vh] flex flex-col">
        {/* Header bar */}
        <div className="bg-brand-900 px-6 py-4 flex items-center justify-between flex-shrink-0">
          <div>
            <p className="text-xs font-mono text-brand-400 uppercase tracking-widest mb-0.5">
              Experiment
            </p>
            <h2 id="dialog-title" className="text-lg font-semibold text-white tracking-tight">
              New Experiment
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-brand-300 hover:text-white transition-colors p-1 rounded"
            aria-label="Close"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M2 2l14 14M16 2L2 16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} noValidate className="flex flex-col min-h-0">
          <div className="px-6 pt-6 pb-4 space-y-5 overflow-y-auto">
            {/* Server error */}
            {error && (
              <div role="alert" className="rounded border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 px-4 py-3">
                <p className="text-sm text-red-700 dark:text-red-400 font-mono">{error}</p>
              </div>
            )}

            {/* Name */}
            <div>
              <label htmlFor="exp-name" className={labelClass}>
                Experiment Name
              </label>
              <input
                ref={nameRef}
                id="exp-name"
                type="text"
                value={name}
                onChange={(e) => dispatch({ type: 'SET_FIELD', field: 'name', value: e.target.value })}
                placeholder="e.g. Bull Market Trial #1"
                maxLength={100}
                className={`${inputClass} ${errors.name ? 'border-red-400 dark:border-red-600 bg-red-50 dark:bg-red-900/10' : ''}`}
                aria-describedby={errors.name ? 'name-error' : undefined}
              />
              {errors.name && (
                <p id="name-error" className="mt-1 text-xs text-red-600 dark:text-red-400 font-mono">
                  {errors.name}
                </p>
              )}
              <p className="mt-1 text-xs text-gray-400 dark:text-gray-600 font-mono text-right">
                {name.length}/100
              </p>
            </div>

            {/* Two-column row */}
            <div className="grid grid-cols-2 gap-4">
              {/* Num Agents */}
              <div>
                <label htmlFor="exp-agents" className={labelClass}>
                  Agents
                </label>
                <input
                  id="exp-agents"
                  type="number"
                  value={numAgents}
                  onChange={(e) => dispatch({ type: 'SET_FIELD', field: 'numAgents', value: Number(e.target.value) })}
                  min={1}
                  max={50}
                  step={1}
                  className={`${inputClass} ${errors.num_agents ? 'border-red-400 dark:border-red-600 bg-red-50 dark:bg-red-900/10' : ''}`}
                  aria-describedby={errors.num_agents ? 'agents-error' : undefined}
                />
                {errors.num_agents && (
                  <p id="agents-error" className="mt-1 text-xs text-red-600 dark:text-red-400 font-mono">
                    {errors.num_agents}
                  </p>
                )}
                <p className="mt-1 text-xs text-gray-400 dark:text-gray-600 font-mono">1 – 50</p>
              </div>

              {/* Starting Capital */}
              <div>
                <label htmlFor="exp-capital" className={labelClass}>
                  Capital (USD)
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm font-mono text-gray-500 dark:text-gray-400">
                    $
                  </span>
                  <input
                    id="exp-capital"
                    type="number"
                    value={startingCapital}
                    onChange={(e) => dispatch({ type: 'SET_FIELD', field: 'startingCapital', value: Number(e.target.value) })}
                    min={100}
                    max={1_000_000}
                    step={100}
                    className={`${inputClass} pl-7 ${errors.starting_capital ? 'border-red-400 dark:border-red-600 bg-red-50 dark:bg-red-900/10' : ''}`}
                    aria-describedby={errors.starting_capital ? 'capital-error' : undefined}
                  />
                </div>
                {errors.starting_capital && (
                  <p id="capital-error" className="mt-1 text-xs text-red-600 dark:text-red-400 font-mono">
                    {errors.starting_capital}
                  </p>
                )}
                <p className="mt-1 text-xs text-gray-400 dark:text-gray-600 font-mono">$100 – $1M</p>
              </div>
            </div>

            {/* Advanced Options Toggle */}
            <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
              <button
                type="button"
                onClick={() => dispatch({ type: 'SET_FIELD', field: 'showAdvanced', value: !showAdvanced })}
                className="flex items-center gap-2 text-xs font-mono font-semibold uppercase tracking-widest text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
              >
                <svg
                  width="12"
                  height="12"
                  viewBox="0 0 12 12"
                  fill="none"
                  className={`transition-transform ${showAdvanced ? 'rotate-90' : ''}`}
                >
                  <path d="M4 2l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                Advanced Options
              </button>
            </div>

            {showAdvanced && (
              <div className="space-y-6">
                {/* Experiment Guidance */}
                <div>
                  <p className="text-xs font-mono font-semibold uppercase tracking-widest text-gray-500 dark:text-gray-400 mb-3 pb-1 border-b border-gray-200 dark:border-gray-700">
                    Experiment Guidance
                  </p>
                  <textarea
                    id="exp-guidance"
                    rows={3}
                    value={guidance}
                    onChange={(e) => dispatch({ type: 'SET_FIELD', field: 'guidance', value: e.target.value })}
                    placeholder="Optional text injected into every agent's prompt each trading day…"
                    className={`${inputClass} resize-y`}
                  />
                </div>

                {/* Agent Strategy Defaults */}
                <div>
                  <p className="text-xs font-mono font-semibold uppercase tracking-widest text-gray-500 dark:text-gray-400 mb-1 pb-1 border-b border-gray-200 dark:border-gray-700">
                    Agent Strategy Defaults
                  </p>
                  <p className="text-xs text-gray-400 dark:text-gray-600 font-mono mb-3">
                    Unset fields will be randomized per agent.
                  </p>
                  <div className="space-y-4">
                    <div>
                      <label htmlFor="adv-philosophy" className={labelClass}>Philosophy</label>
                      <textarea
                        id="adv-philosophy"
                        rows={2}
                        value={agentPhilosophy}
                        onChange={(e) => dispatch({ type: 'SET_FIELD', field: 'agentPhilosophy', value: e.target.value })}
                        placeholder="e.g. Value investing with a focus on undervalued companies"
                        className={`${inputClass} resize-y`}
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label htmlFor="adv-risk" className={labelClass}>Risk Tolerance</label>
                        <select
                          id="adv-risk"
                          value={agentRisk}
                          onChange={(e) => dispatch({ type: 'SET_FIELD', field: 'agentRisk', value: e.target.value })}
                          className={inputClass}
                        >
                          <option value="">— randomized —</option>
                          {RISK_OPTIONS.map((opt) => (
                            <option key={opt} value={opt}>
                              {opt.charAt(0).toUpperCase() + opt.slice(1)}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label htmlFor="adv-horizon" className={labelClass}>Time Horizon</label>
                        <input
                          id="adv-horizon"
                          type="text"
                          value={agentHorizon}
                          onChange={(e) => dispatch({ type: 'SET_FIELD', field: 'agentHorizon', value: e.target.value })}
                          placeholder="e.g. 6-12 months"
                          className={inputClass}
                        />
                      </div>
                    </div>
                    <div>
                      <label htmlFor="adv-sectors" className={labelClass}>Preferred Sectors</label>
                      <input
                        id="adv-sectors"
                        type="text"
                        value={agentSectors}
                        onChange={(e) => dispatch({ type: 'SET_FIELD', field: 'agentSectors', value: e.target.value })}
                        placeholder="e.g. Technology, Healthcare"
                        className={inputClass}
                      />
                      <p className="mt-1 text-xs text-gray-400 dark:text-gray-600 font-mono">Comma-separated</p>
                    </div>
                    <div>
                      <label htmlFor="adv-metrics" className={labelClass}>Key Metrics</label>
                      <input
                        id="adv-metrics"
                        type="text"
                        value={agentMetrics}
                        onChange={(e) => dispatch({ type: 'SET_FIELD', field: 'agentMetrics', value: e.target.value })}
                        placeholder="e.g. P/E ratio, Revenue growth"
                        className={inputClass}
                      />
                      <p className="mt-1 text-xs text-gray-400 dark:text-gray-600 font-mono">Comma-separated</p>
                    </div>
                    <div>
                      <label htmlFor="adv-rationale" className={labelClass}>Rationale</label>
                      <textarea
                        id="adv-rationale"
                        rows={2}
                        value={agentRationale}
                        onChange={(e) => dispatch({ type: 'SET_FIELD', field: 'agentRationale', value: e.target.value })}
                        placeholder="e.g. This strategy prioritizes capital preservation…"
                        className={`${inputClass} resize-y`}
                      />
                    </div>
                  </div>
                </div>

                {/* Starting Portfolio */}
                <div>
                  <p className="text-xs font-mono font-semibold uppercase tracking-widest text-gray-500 dark:text-gray-400 mb-3 pb-1 border-b border-gray-200 dark:border-gray-700">
                    Starting Portfolio
                  </p>
                  <div className="space-y-4">
                    <div>
                      <label htmlFor="adv-cash" className={labelClass}>Cash Override (USD)</label>
                      <div className="relative">
                        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm font-mono text-gray-500 dark:text-gray-400">$</span>
                        <input
                          id="adv-cash"
                          type="number"
                          value={cashOverride}
                          onChange={(e) => dispatch({ type: 'SET_FIELD', field: 'cashOverride', value: e.target.value })}
                          min={0}
                          step={100}
                          placeholder="Leave blank to use Starting Capital"
                          className={`${inputClass} pl-7 ${errors.cash_override ? 'border-red-400 dark:border-red-600 bg-red-50 dark:bg-red-900/10' : ''}`}
                          aria-describedby={errors.cash_override ? 'cash-error' : undefined}
                        />
                      </div>
                      {errors.cash_override && (
                        <p id="cash-error" className="mt-1 text-xs text-red-600 dark:text-red-400 font-mono">
                          {errors.cash_override}
                        </p>
                      )}
                    </div>

                    {/* Position rows */}
                    {positions.length > 0 && (
                      <div className="space-y-2">
                        <div className="grid grid-cols-[1fr_80px_100px_24px] gap-2 text-[0.65rem] font-mono font-semibold uppercase tracking-widest text-gray-400 dark:text-gray-600 px-1">
                          <span>Symbol</span>
                          <span>Shares</span>
                          <span>Cost/sh</span>
                          <span />
                        </div>
                        {positions.map((pos) => (
                          <div key={pos.id} className="grid grid-cols-[1fr_80px_100px_24px] gap-2 items-center">
                            <input
                              type="text"
                              value={pos.symbol}
                              onChange={(e) => updatePosition(pos.id, 'symbol', e.target.value.toUpperCase())}
                              placeholder="AAPL"
                              className={`${inputClass} uppercase`}
                            />
                            <input
                              type="number"
                              value={pos.shares || ''}
                              onChange={(e) => updatePosition(pos.id, 'shares', Number(e.target.value))}
                              min={0}
                              step={1}
                              placeholder="10"
                              className={inputClass}
                            />
                            <input
                              type="number"
                              value={pos.cost_basis || ''}
                              onChange={(e) => updatePosition(pos.id, 'cost_basis', Number(e.target.value))}
                              min={0}
                              step={0.01}
                              placeholder="150.00"
                              className={inputClass}
                            />
                            <button
                              type="button"
                              onClick={() => removePosition(pos.id)}
                              className="text-gray-400 hover:text-red-500 transition-colors w-6 h-6 flex items-center justify-center"
                              aria-label="Remove position"
                            >
                              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                                <path d="M2 2l8 8M10 2L2 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                              </svg>
                            </button>
                          </div>
                        ))}
                      </div>
                    )}

                    <button
                      type="button"
                      onClick={addPosition}
                      className="flex items-center gap-1.5 text-xs font-mono text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
                    >
                      <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                        <path d="M6 1v10M1 6h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                      </svg>
                      Add position
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-6 py-4 bg-gray-50 dark:bg-gray-800/50 border-t border-gray-200 dark:border-gray-700 flex items-center justify-end gap-3 flex-shrink-0">
            <button
              type="button"
              onClick={onClose}
              disabled={isLoading}
              className="px-4 py-2 text-sm font-mono text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white disabled:opacity-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="px-5 py-2 text-sm font-mono font-semibold rounded bg-brand-700 hover:bg-brand-800 text-white disabled:opacity-60 disabled:cursor-not-allowed transition-colors flex items-center gap-2 focus:outline-none focus:ring-2 focus:ring-brand-600 focus:ring-offset-2"
            >
              {isLoading && (
                <svg className="animate-spin h-4 w-4 text-white" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              )}
              {isLoading ? 'Creating…' : 'Create Experiment'}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body
  );
}
