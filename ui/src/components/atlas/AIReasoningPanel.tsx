import { useState, useEffect, useMemo } from 'react';
import { cn } from '@/lib/utils';
import { Brain, Zap, Search, GitBranch, Shield, ChevronDown, ChevronRight } from 'lucide-react';
import type { Incident } from '@/types/atlas';

interface AIReasoningPanelProps {
  incident: Incident;
  showFullDetail?: boolean;
}

interface ThinkingStep {
  id: string;
  icon: React.ElementType;
  label: string;
  duration: string;
  detail: string;
  subSteps?: string[];
}

export function AIReasoningPanel({ incident, showFullDetail = false }: AIReasoningPanelProps) {
  const [expanded, setExpanded] = useState(showFullDetail);
  const [animatedSteps, setAnimatedSteps] = useState(0);

  // Memoize so the array reference is stable — prevents useEffect from re-running on every render
  const thinkingSteps: ThinkingStep[] = useMemo(() => [
    {
      id: 'ingest',
      icon: Zap,
      label: 'Signal Ingestion',
      duration: '0.3s',
      detail: `Received ${incident.services.length} metric streams. Anomaly threshold breached on ${incident.services.filter(s => s.health !== 'healthy').map(s => s.name).join(', ') || 'monitored services'}.`,
      subSteps: [
        `Ingested ${incident.services.length * 14} metric data points across ${incident.services.length} services`,
        `Noise filter eliminated 23 transient spikes (< 30s duration)`,
        `Persistent anomaly confirmed: ${incident.services[0]?.triggerMetric || 'metric'} at ${incident.services[0]?.triggerValue || 'elevated'}`,
      ],
    },
    {
      id: 'correlate',
      icon: GitBranch,
      label: 'Dependency Correlation',
      duration: '1.2s',
      detail: `Traversed service dependency graph (${incident.services.length} nodes, ${incident.services.length * 2} edges). Identified causal chain.`,
      subSteps: [
        `Graph traversal: ${incident.services.map(s => s.name).join(' → ')}`,
        incident.deploymentCorrelation
          ? `Deployment correlation: ${incident.deploymentCorrelation.changeId} (${incident.deploymentCorrelation.daysAgo}d ago) — ${incident.deploymentCorrelation.description}`
          : 'No recent deployment correlated',
        `Cascade analysis: ${incident.services.filter(s => s.health === 'warning').length} downstream services impacted`,
      ],
    },
    {
      id: 'match',
      icon: Search,
      label: 'Knowledge Base Search',
      duration: '0.8s',
      detail: incident.historicalMatch
        ? `Found historical precedent ${incident.historicalMatch.incidentId} with ${incident.historicalMatch.similarity}% similarity.`
        : 'No strong historical match found. Pattern flagged as novel.',
      subSteps: [
        `Searched 2,847 historical incident records`,
        `Vector similarity scan across 14 feature dimensions`,
        incident.historicalMatch
          ? `Best match: ${incident.historicalMatch.incidentId} (${incident.historicalMatch.occurredAt}) — ${incident.historicalMatch.rootCause}`
          : `Closest match below 60% threshold — treating as novel pattern`,
        `Cross-client pattern check: ${incident.alternativeHypotheses.length} alternative hypotheses generated`,
      ],
    },
    {
      id: 'reason',
      icon: Brain,
      label: 'Root Cause Reasoning',
      duration: '2.1s',
      detail: `Diagnosis: ${incident.rootCause.diagnosis.slice(0, 120)}${incident.rootCause.diagnosis.length > 120 ? '…' : ''} (${incident.rootCause.confidence}% confidence)`,
      subSteps: [
        `Evaluated ${2 + incident.alternativeHypotheses.length} candidate hypotheses`,
        `Primary hypothesis scored ${incident.rootCause.confidence}% — factors: historical ${incident.rootCause.factors.historicalAccuracy}%, certainty ${incident.rootCause.factors.rootCauseCertainty}%, safety ${incident.rootCause.factors.actionSafetyClass}%, freshness ${incident.rootCause.factors.evidenceFreshness}%`,
        ...incident.alternativeHypotheses.map((alt, i) =>
          `Rejected hypothesis ${i + 1}: "${alt.hypothesis}" — ${alt.evidenceAgainst.length} contra-indicators`,
        ),
        `Final diagnosis locked at ${incident.rootCause.confidence}% confidence`,
      ],
    },
    {
      id: 'select',
      icon: Shield,
      label: 'Action Selection & Governance',
      duration: '0.4s',
      detail: `Selected playbook ${incident.recommendedAction.playbookName}. Risk: ${incident.recommendedAction.riskClass}. Rollback: ${incident.recommendedAction.rollbackAvailable ? 'Available' : 'Manual'}.`,
      subSteps: [
        `Matched ${incident.recommendedAction.playbookName} from playbook library (${incident.recommendedAction.riskClass} risk)`,
        `Governance check: ${incident.recommendedAction.riskClass === 'Low' ? 'Passed — Class 1 auto-eligible' : 'Flagged — requires human approval'}`,
        `Estimated resolution time: ${incident.recommendedAction.estimatedTime}`,
        `Rollback procedure: ${incident.recommendedAction.rollbackAvailable ? 'Automated rollback available' : 'Manual rollback required'}`,
      ],
    },
  // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [incident.id]); // Re-compute only when incident changes, not on every render

  // Reset animation when incident changes
  useEffect(() => {
    setAnimatedSteps(0);
  }, [incident.id]);

  // Animate steps in one at a time — stable because thinkingSteps.length is stable
  useEffect(() => {
    if (animatedSteps >= thinkingSteps.length) return;
    const timer = setTimeout(() => setAnimatedSteps(prev => prev + 1), 200);
    return () => clearTimeout(timer);
  }, [animatedSteps, thinkingSteps.length]);

  const totalTime = thinkingSteps.reduce((sum, s) => sum + parseFloat(s.duration), 0);

  return (
    <div className="bg-card border border-border rounded-lg shadow-atlas overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-muted/30 transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <div className="h-6 w-6 rounded-full bg-accent/10 flex items-center justify-center">
            <Brain className="h-3.5 w-3.5 text-accent" />
          </div>
          <span className="text-[12px] font-semibold text-foreground uppercase tracking-wider">ATLAS AI Reasoning</span>
          <span className="text-[10px] font-mono text-muted-foreground tabular-nums">{totalTime.toFixed(1)}s total</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex gap-0.5">
            {thinkingSteps.map((_, i) => (
              <div
                key={i}
                className={cn(
                  'h-1.5 w-4 rounded-full transition-all duration-300',
                  i < animatedSteps ? 'bg-status-healthy' : 'bg-muted',
                )}
              />
            ))}
          </div>
          {expanded ? <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" /> : <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />}
        </div>
      </button>

      {expanded && (
        <div className="border-t border-border">
          {thinkingSteps.map((step, i) => (
            <StepRow key={step.id} step={step} isLast={i === thinkingSteps.length - 1} visible={i < animatedSteps} />
          ))}
        </div>
      )}
    </div>
  );
}

function StepRow({ step, isLast, visible }: { step: ThinkingStep; isLast: boolean; visible: boolean }) {
  const [showSub, setShowSub] = useState(false);
  const Icon = step.icon;

  return (
    <div
      className={cn(
        'transition-all duration-300',
        !isLast && 'border-b border-border',
        !visible && 'opacity-0 max-h-0 overflow-hidden',
        visible && 'opacity-100',
      )}
    >
      <button
        onClick={() => step.subSteps && setShowSub(!showSub)}
        className="w-full px-4 py-2.5 flex items-start gap-3 text-left hover:bg-muted/20 transition-colors"
      >
        <div className="mt-0.5 shrink-0">
          <div className="h-5 w-5 rounded-full bg-status-healthy/10 flex items-center justify-center">
            <Icon className="h-3 w-3 text-status-healthy" />
          </div>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-[11px] font-semibold text-foreground">{step.label}</span>
            <span className="font-mono text-[9px] text-muted-foreground tabular-nums">{step.duration}</span>
          </div>
          <p className="text-[11px] text-muted-foreground leading-relaxed">{step.detail}</p>
        </div>
        {step.subSteps && (
          <div className="mt-1 shrink-0">
            {showSub ? <ChevronDown className="h-3 w-3 text-muted-foreground" /> : <ChevronRight className="h-3 w-3 text-muted-foreground" />}
          </div>
        )}
      </button>
      {showSub && step.subSteps && (
        <div className="px-4 pb-3 pl-12">
          <div className="border-l-2 border-accent/20 pl-3 space-y-1">
            {step.subSteps.map((sub, j) => (
              <p key={j} className="text-[10px] text-muted-foreground leading-relaxed flex items-start gap-1.5">
                <span className="text-accent shrink-0 mt-[1px]">›</span>
                {sub}
              </p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
