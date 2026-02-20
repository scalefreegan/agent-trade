import { useState } from 'react';
import { Card } from '../ui/Card';
import { Tabs } from '../ui/Tabs';
import { useAdvisorPresets, useExperimentAgents } from '../../api/advisor';
import { useExperiments } from '../../api/experiments';
import type { AdvisorAgentConfig, AdvisorPreset } from '../../api/types';

const selectorTabs = [
  { id: 'presets' as const, label: 'Presets' },
  { id: 'custom' as const, label: 'Custom' },
  { id: 'experiment' as const, label: 'From Experiment' },
];

type SelectorTab = (typeof selectorTabs)[number]['id'];

interface AgentSelectorProps {
  selected: AdvisorAgentConfig[];
  onSelectionChange: (agents: AdvisorAgentConfig[]) => void;
  maxAgents?: number;
}

// Generate unique key for an agent (handles name collisions in experiments)
function agentKey(agent: AdvisorAgentConfig): string {
  return agent.agent_id ? `exp:${agent.agent_id}` : `name:${agent.name}`;
}

export function AgentSelector({ selected, onSelectionChange, maxAgents = 10 }: AgentSelectorProps) {
  const [activeTab, setActiveTab] = useState<SelectorTab>('presets');
  const [customName, setCustomName] = useState('');
  const [customPhilosophy, setCustomPhilosophy] = useState('');

  const isSelected = (agent: AdvisorAgentConfig) => selected.some((a) => agentKey(a) === agentKey(agent));
  const atLimit = selected.length >= maxAgents;

  const toggleAgent = (agent: AdvisorAgentConfig) => {
    if (isSelected(agent)) {
      onSelectionChange(selected.filter((a) => agentKey(a) !== agentKey(agent)));
    } else if (!atLimit) {
      onSelectionChange([...selected, agent]);
    }
  };

  const addCustom = () => {
    const name = customName.trim();
    const philosophy = customPhilosophy.trim();
    const tempAgent = { name, philosophy };
    if (!name || !philosophy || atLimit || isSelected(tempAgent)) return;
    onSelectionChange([...selected, tempAgent]);
    setCustomName('');
    setCustomPhilosophy('');
  };

  return (
    <Card>
      <h3 className="text-sm font-medium text-foreground mb-3">Select Advisors ({selected.length}/{maxAgents})</h3>
      <Tabs tabs={selectorTabs} active={activeTab} onChange={setActiveTab} className="mb-4" />

      {activeTab === 'presets' && <PresetsGrid selected={selected} onToggle={toggleAgent} atLimit={atLimit} />}
      {activeTab === 'custom' && (
        <CustomForm
          name={customName}
          philosophy={customPhilosophy}
          onNameChange={setCustomName}
          onPhilosophyChange={setCustomPhilosophy}
          onAdd={addCustom}
          disabled={atLimit}
          duplicate={isSelected({ name: customName.trim(), philosophy: '' })}
        />
      )}
      {activeTab === 'experiment' && (
        <ExperimentPicker selected={selected} onToggle={toggleAgent} atLimit={atLimit} />
      )}

      {/* Selected chips */}
      {selected.length > 0 && (
        <div className="mt-4 pt-3 border-t border-border">
          <p className="text-xs text-muted-foreground mb-2">Selected</p>
          <div className="flex flex-wrap gap-2">
            {selected.map((a) => (
              <button
                key={agentKey(a)}
                onClick={() => toggleAgent(a)}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-primary/15 text-primary hover:bg-primary/25 transition-colors"
              >
                {a.name}
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                  <path d="M3 3l6 6M9 3L3 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
              </button>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}

/* ─── Sub-components ─────────────────────────────────────────────────── */

function PresetsGrid({
  selected,
  onToggle,
  atLimit,
}: {
  selected: AdvisorAgentConfig[];
  onToggle: (a: AdvisorAgentConfig) => void;
  atLimit: boolean;
}) {
  const { data, isLoading } = useAdvisorPresets();
  const presets = data?.presets ?? [];

  if (isLoading) return <p className="text-sm text-muted-foreground py-4">Loading presets...</p>;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
      {presets.map((preset) => {
        const presetConfig = { name: preset.name, philosophy: preset.philosophy };
        const isActive = selected.some((a) => agentKey(a) === agentKey(presetConfig));
        return (
          <PresetCard
            key={preset.id}
            preset={preset}
            active={isActive}
            disabled={atLimit && !isActive}
            onToggle={() => onToggle(presetConfig)}
          />
        );
      })}
    </div>
  );
}

function PresetCard({
  preset,
  active,
  disabled,
  onToggle,
}: {
  preset: AdvisorPreset;
  active: boolean;
  disabled: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      onClick={onToggle}
      disabled={disabled}
      className={`
        text-left rounded-lg border p-3 transition-all
        ${active
          ? 'border-primary bg-primary/10 ring-1 ring-primary'
          : disabled
            ? 'border-border bg-muted/50 opacity-50 cursor-not-allowed'
            : 'border-border bg-card hover:border-primary/50 hover:bg-primary/5'
        }
      `}
    >
      <p className="text-sm font-medium text-foreground">{preset.name}</p>
      <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{preset.philosophy}</p>
    </button>
  );
}

function CustomForm({
  name,
  philosophy,
  onNameChange,
  onPhilosophyChange,
  onAdd,
  disabled,
  duplicate,
}: {
  name: string;
  philosophy: string;
  onNameChange: (v: string) => void;
  onPhilosophyChange: (v: string) => void;
  onAdd: () => void;
  disabled: boolean;
  duplicate: boolean;
}) {
  const canAdd = name.trim() && philosophy.trim() && !disabled && !duplicate;

  return (
    <div className="space-y-3">
      <div>
        <label htmlFor="custom-name" className="block text-xs font-medium text-muted-foreground mb-1">
          Advisor Name
        </label>
        <input
          id="custom-name"
          type="text"
          value={name}
          onChange={(e) => onNameChange(e.target.value)}
          placeholder="e.g. My Value Advisor"
          className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
        />
        {duplicate && <p className="text-xs text-loss mt-1">An advisor with this name is already selected.</p>}
      </div>
      <div>
        <label htmlFor="custom-philosophy" className="block text-xs font-medium text-muted-foreground mb-1">
          Investment Philosophy
        </label>
        <textarea
          id="custom-philosophy"
          value={philosophy}
          onChange={(e) => onPhilosophyChange(e.target.value)}
          placeholder="Describe the advisor's investment approach, preferred metrics, risk tolerance..."
          rows={3}
          className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary resize-none"
        />
      </div>
      <button
        onClick={onAdd}
        disabled={!canAdd}
        className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        Add Advisor
      </button>
    </div>
  );
}

function ExperimentPicker({
  selected,
  onToggle,
  atLimit,
}: {
  selected: AdvisorAgentConfig[];
  onToggle: (a: AdvisorAgentConfig) => void;
  atLimit: boolean;
}) {
  const { data: experiments, isLoading: loadingExperiments } = useExperiments();
  const [experimentId, setExperimentId] = useState<string>('');
  const { data: agents, isLoading: loadingAgents } = useExperimentAgents(experimentId || null);

  if (loadingExperiments) return <p className="text-sm text-muted-foreground py-4">Loading experiments...</p>;

  return (
    <div className="space-y-3">
      <div>
        <label htmlFor="experiment-select" className="block text-xs font-medium text-muted-foreground mb-1">
          Experiment
        </label>
        <select
          id="experiment-select"
          value={experimentId}
          onChange={(e) => setExperimentId(e.target.value)}
          className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
        >
          <option value="">Select an experiment...</option>
          {(experiments ?? []).map((exp) => (
            <option key={exp.id} value={exp.id}>
              {exp.name}
            </option>
          ))}
        </select>
      </div>

      {loadingAgents && <p className="text-sm text-muted-foreground">Loading agents...</p>}

      {agents && agents.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {agents.map((agent) => {
            const agentConfig = { name: agent.name, philosophy: agent.philosophy, agent_id: agent.agent_id };
            const isActive = selected.some((a) => agentKey(a) === agentKey(agentConfig));
            return (
              <button
                key={agent.agent_id}
                onClick={() => onToggle(agentConfig)}
                disabled={atLimit && !isActive}
                className={`
                  text-left rounded-lg border p-3 transition-all
                  ${isActive
                    ? 'border-primary bg-primary/10 ring-1 ring-primary'
                    : atLimit
                      ? 'border-border bg-muted/50 opacity-50 cursor-not-allowed'
                      : 'border-border bg-card hover:border-primary/50 hover:bg-primary/5'
                  }
                `}
              >
                <p className="text-sm font-medium text-foreground">{agent.name}</p>
                {agent.philosophy && (
                  <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{agent.philosophy}</p>
                )}
              </button>
            );
          })}
        </div>
      )}

      {agents && agents.length === 0 && (
        <p className="text-sm text-muted-foreground">No agents found in this experiment.</p>
      )}
    </div>
  );
}
