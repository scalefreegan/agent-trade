import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

interface NewExperimentDialogProps {
  open: boolean;
  onClose: () => void;
  onCreate: (data: { name: string; num_agents: number; starting_capital: number }) => void;
  isLoading: boolean;
  error: string | null;
}

interface FormErrors {
  name?: string;
  num_agents?: string;
  starting_capital?: string;
}

export function NewExperimentDialog({
  open,
  onClose,
  onCreate,
  isLoading,
  error,
}: NewExperimentDialogProps) {
  const [name, setName] = useState('');
  const [numAgents, setNumAgents] = useState(10);
  const [startingCapital, setStartingCapital] = useState(1000);
  const [errors, setErrors] = useState<FormErrors>({});
  const nameRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setName('');
      setNumAgents(10);
      setStartingCapital(1000);
      setErrors({});
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
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    onCreate({ name: name.trim(), num_agents: numAgents, starting_capital: startingCapital });
  };

  if (!open) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="dialog-title"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="relative w-full max-w-md bg-white dark:bg-gray-900 shadow-2xl border border-gray-200 dark:border-gray-700 rounded overflow-hidden">
        {/* Header bar */}
        <div className="bg-brand-900 px-6 py-4 flex items-center justify-between">
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
        <form onSubmit={handleSubmit} noValidate>
          <div className="px-6 pt-6 pb-4 space-y-5">
            {/* Server error */}
            {error && (
              <div className="rounded border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 px-4 py-3">
                <p className="text-sm text-red-700 dark:text-red-400 font-mono">{error}</p>
              </div>
            )}

            {/* Name */}
            <div>
              <label
                htmlFor="exp-name"
                className="block text-xs font-mono font-semibold uppercase tracking-widest text-gray-500 dark:text-gray-400 mb-1.5"
              >
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
                className={`
                  w-full px-3 py-2.5 text-sm font-mono bg-gray-50 dark:bg-gray-800
                  border rounded transition-colors outline-none
                  text-gray-900 dark:text-gray-100
                  placeholder-gray-400 dark:placeholder-gray-600
                  focus:ring-2 focus:ring-brand-700 focus:border-brand-700
                  dark:focus:ring-brand-600 dark:focus:border-brand-600
                  ${errors.name
                    ? 'border-red-400 dark:border-red-600 bg-red-50 dark:bg-red-900/10'
                    : 'border-gray-300 dark:border-gray-600'}
                `}
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
                <label
                  htmlFor="exp-agents"
                  className="block text-xs font-mono font-semibold uppercase tracking-widest text-gray-500 dark:text-gray-400 mb-1.5"
                >
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
                  className={`
                    w-full px-3 py-2.5 text-sm font-mono bg-gray-50 dark:bg-gray-800
                    border rounded transition-colors outline-none
                    text-gray-900 dark:text-gray-100
                    focus:ring-2 focus:ring-brand-700 focus:border-brand-700
                    dark:focus:ring-brand-600 dark:focus:border-brand-600
                    ${errors.num_agents
                      ? 'border-red-400 dark:border-red-600 bg-red-50 dark:bg-red-900/10'
                      : 'border-gray-300 dark:border-gray-600'}
                  `}
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
                <label
                  htmlFor="exp-capital"
                  className="block text-xs font-mono font-semibold uppercase tracking-widest text-gray-500 dark:text-gray-400 mb-1.5"
                >
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
                    className={`
                      w-full pl-7 pr-3 py-2.5 text-sm font-mono bg-gray-50 dark:bg-gray-800
                      border rounded transition-colors outline-none
                      text-gray-900 dark:text-gray-100
                      focus:ring-2 focus:ring-brand-700 focus:border-brand-700
                      dark:focus:ring-brand-600 dark:focus:border-brand-600
                      ${errors.starting_capital
                        ? 'border-red-400 dark:border-red-600 bg-red-50 dark:bg-red-900/10'
                        : 'border-gray-300 dark:border-gray-600'}
                    `}
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
          </div>

          {/* Footer */}
          <div className="px-6 py-4 bg-gray-50 dark:bg-gray-800/50 border-t border-gray-200 dark:border-gray-700 flex items-center justify-end gap-3">
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
              className="
                px-5 py-2 text-sm font-mono font-semibold rounded
                bg-brand-700 hover:bg-brand-800 text-white
                dark:bg-brand-700 dark:hover:bg-brand-800
                disabled:opacity-60 disabled:cursor-not-allowed
                transition-colors flex items-center gap-2
                focus:outline-none focus:ring-2 focus:ring-brand-600 focus:ring-offset-2
              "
            >
              {isLoading && (
                <svg className="animate-spin h-4 w-4 text-white" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
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
