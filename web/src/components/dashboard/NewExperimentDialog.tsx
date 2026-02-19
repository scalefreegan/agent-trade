import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import type { CreateExperimentInput } from '../../api/experiments';
import type { AgentInitHints, PortfolioPositionSpec } from '../../api/types';

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

const inputClass =
  'w-full px-3 py-2.5 text-sm font-mono bg-gray-50 dark:bg-gray-800 border rounded transition-colors outline-none text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-600 focus:ring-2 focus:ring-brand-700 focus:border-brand-700 dark:focus:ring-brand-600 dark:focus:border-brand-600 border-gray-300 dark:border-gray-600';
const labelClass =
  'block text-xs font-mono font-semibold uppercase tracking-widest text-gray-500 dark:text-gray-400 mb-1.5';

function emptyPosition(): PortfolioPositionSpec {
  return { symbol: '', shares: 0, cost_basis: 0 };
}

export function NewExperimentDialog({
  open,
  onClose,
  onCreate,
  isLoading,
  error,
}: NewExperimentDialogProps) {
  // Basic fields
  const [name, setName] = useState('');
  const [numAgents, setNumAgents] = useState(10);
  const [startingCapital, setStartingCapital] = useState(1000);
  const [errors, setErrors] = useState<FormErrors>({});
  const nameRef = useRef<HTMLInputElement>(null);

  // Advanced options toggle
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Guidance
  const [guidance, setGuidance] = useState('');

  // Agent strategy defaults
  const [agentPhilosophy, setAgentPhilosophy] = useState('');
  const [agentRisk, setAgentRisk] = useState('');
  const [agentSectors, setAgentSectors] = useState('');
  const [agentHorizon, setAgentHorizon] = useState('');
  const [agentMetrics, setAgentMetrics] = useState('');
  const [agentRationale, setAgentRationale] = useState('');

  // Starting portfolio
  const [cashOverride, setCashOverride] = useState('');
  const [positions, setPositions] = useState<PortfolioPositionSpec[]>([]);

  useEffect(() => {
    if (open) {
      setName('');
      setNumAgents(10);
      setStartingCapital(1000);
      setErrors({});
      setShowAdvanced(false);
      setGuidance('');
      setAgentPhilosophy('');
      setAgentRisk('');
      setAgentSectors('');
      setAgentHorizon('');
      setAgentMetrics('');
      setAgentRationale('');
      setCashOverride('');
      setPositions([]);
      setTimeout(() => nameRef.current?.focus(), 50);
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [open, onClose]);

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
    setErrors(next);
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
          positions: validPositions.map((p) => ({
            symbol: p.symbol.trim().toUpperCase(),
            shares: p.shares,
            cost_basis: p.cost_basis,
            ...(p.purchase_date ? { purchase_date: p.purchase_date } : {}),
          })),
          ...(hasCash ? { cash: Number(cashOverride) } : {}),
        };
      }
    }

    onCreate(payload);
  };

  const addPosition = () => setPositions((prev) => [...prev, emptyPosition()]);
  const removePosition = (i: number) => setPositions((prev) => prev.filter((_, idx) => idx !== i));
  const updatePosition = (i: number, field: keyof PortfolioPositionSpec, value: string | number) =>
    setPositions((prev) => prev.map((p, idx) => (idx === i ? { ...p, [field]: value } : p)));

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
      <div className="relative w-full max-w-2xl bg-white dark:bg-gray-900 shadow-2xl border border-gray-200 dark:border-gray-700 rounded overflow-hidden max-h-[90vh] flex flex-col">
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
              <div className="rounded border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 px-4 py-3">
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
                onChange={(e) => setName(e.target.value)}
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
                  onChange={(e) => setNumAgents(Number(e.target.value))}
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
                    onChange={(e) => setStartingCapital(Number(e.target.value))}
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
                onClick={() => setShowAdvanced((v) => !v)}
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
                    onChange={(e) => setGuidance(e.target.value)}
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
                        onChange={(e) => setAgentPhilosophy(e.target.value)}
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
                          onChange={(e) => setAgentRisk(e.target.value)}
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
                          onChange={(e) => setAgentHorizon(e.target.value)}
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
                        onChange={(e) => setAgentSectors(e.target.value)}
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
                        onChange={(e) => setAgentMetrics(e.target.value)}
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
                        onChange={(e) => setAgentRationale(e.target.value)}
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
                          onChange={(e) => setCashOverride(e.target.value)}
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
                        {positions.map((pos, i) => (
                          <div key={i} className="grid grid-cols-[1fr_80px_100px_24px] gap-2 items-center">
                            <input
                              type="text"
                              value={pos.symbol}
                              onChange={(e) => updatePosition(i, 'symbol', e.target.value.toUpperCase())}
                              placeholder="AAPL"
                              className={`${inputClass} uppercase`}
                            />
                            <input
                              type="number"
                              value={pos.shares || ''}
                              onChange={(e) => updatePosition(i, 'shares', Number(e.target.value))}
                              min={0}
                              step={1}
                              placeholder="10"
                              className={inputClass}
                            />
                            <input
                              type="number"
                              value={pos.cost_basis || ''}
                              onChange={(e) => updatePosition(i, 'cost_basis', Number(e.target.value))}
                              min={0}
                              step={0.01}
                              placeholder="150.00"
                              className={inputClass}
                            />
                            <button
                              type="button"
                              onClick={() => removePosition(i)}
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
