import { cn } from '@/lib/utils';
import { Check, Radio, Radar, GitBranch, Search, Brain, Shield, Zap, BookOpen, Wrench } from 'lucide-react';

export type PipelineStage = 'ingest' | 'detect' | 'correlate' | 'search' | 'reason' | 'select' | 'route' | 'act' | 'learn';

const stages: { key: PipelineStage; label: string; icon: React.ElementType; description: string }[] = [
  { key: 'ingest', label: 'Ingest', icon: Radio, description: 'Signal ingestion' },
  { key: 'detect', label: 'Detect', icon: Radar, description: 'Anomaly detection' },
  { key: 'correlate', label: 'Correlate', icon: GitBranch, description: 'Dependency mapping' },
  { key: 'search', label: 'KB Search', icon: Search, description: 'Knowledge base' },
  { key: 'reason', label: 'Reason', icon: Brain, description: 'Root cause analysis' },
  { key: 'select', label: 'Select', icon: Shield, description: 'Action & governance' },
  { key: 'route', label: 'Route', icon: Zap, description: 'Engineer routing' },
  { key: 'act', label: 'Act', icon: Wrench, description: 'Playbook execution' },
  { key: 'learn', label: 'Learn', icon: BookOpen, description: 'Post-incident learning' },
];

const stageOrder: Record<PipelineStage, number> = {
  ingest: 0, detect: 1, correlate: 2, search: 3, reason: 4, select: 5, route: 6, act: 7, learn: 8,
};

interface PipelineIndicatorProps {
  currentStage: PipelineStage;
  className?: string;
  compact?: boolean;
}

export function PipelineIndicator({ currentStage, className, compact }: Readonly<PipelineIndicatorProps>) {
  const currentIndex = stageOrder[currentStage];

  const analysisComplete = currentIndex >= stageOrder.route;
  const lifecycleComplete = currentIndex >= stageOrder.learn;
  let statusLabel = 'Processing...';
  if (lifecycleComplete) {
    statusLabel = 'Lifecycle complete';
  } else if (analysisComplete) {
    statusLabel = 'Analysis complete';
  }
  const statusClass = lifecycleComplete || analysisComplete ? 'text-status-healthy' : 'text-accent';
  const showPulse = !lifecycleComplete && !analysisComplete;

  const connectorClass = (index: number): string => {
    if (index < currentIndex - 1) return 'bg-status-healthy/40';
    if (index === currentIndex - 1) return 'bg-accent/40';
    return 'bg-border';
  };

  return (
    <div className={cn('bg-card border border-border rounded-lg shadow-atlas overflow-hidden', className)}>
      <div className="px-4 py-2.5 flex items-center justify-between border-b border-border">
        <div className="flex items-center gap-2">
          <div className="h-5 w-5 rounded bg-accent/10 flex items-center justify-center">
            <Brain className="h-3 w-3 text-accent" />
          </div>
          <span className="text-[11px] font-semibold text-foreground uppercase tracking-wider">ATLAS Intelligence Pipeline</span>
        </div>
        <div className="flex items-center gap-1.5">
          {showPulse ? <div className="h-1.5 w-1.5 rounded-full bg-accent atlas-pulse" /> : <Check className="h-3 w-3 text-status-healthy" />}
          <span className={cn('text-[10px] font-medium', statusClass)}>{statusLabel}</span>
        </div>
      </div>

      <div className="px-4 py-3">
        <div className="flex items-center justify-between">
          {stages.map((stage, i) => {
            const isComplete = i < currentIndex || (lifecycleComplete && i === currentIndex);
            const isCurrent = !lifecycleComplete && i === currentIndex;
            const isFuture = i > currentIndex;
            const Icon = stage.icon;

            return (
              <div key={stage.key} className="flex items-center">
                <div className="flex flex-col items-center gap-1 min-w-[56px]">
                  <div
                    className={cn(
                      'h-7 w-7 rounded-full flex items-center justify-center transition-all duration-200',
                      isComplete && 'bg-status-healthy/10 border border-status-healthy/30',
                      isCurrent && 'bg-accent/10 border-2 border-accent atlas-pulse',
                      isFuture && 'bg-muted border border-border',
                    )}
                  >
                    {isComplete ? (
                      <Check className="h-3.5 w-3.5 text-status-healthy" />
                    ) : (
                      <Icon className={cn(
                        'h-3 w-3',
                        isCurrent ? 'text-accent' : 'text-muted-foreground',
                      )} />
                    )}
                  </div>
                  <span className={cn(
                    'text-[8px] font-semibold uppercase tracking-wider leading-tight text-center',
                    isComplete && 'text-status-healthy',
                    isCurrent && 'text-accent',
                    isFuture && 'text-muted-foreground',
                  )}>
                    {stage.label}
                  </span>
                  {!compact && (
                    <span className="text-[7px] text-muted-foreground leading-tight text-center hidden lg:block">
                      {stage.description}
                    </span>
                  )}
                </div>
                {i < stages.length - 1 && (
                  <div className={cn(
                    'h-[2px] w-3 lg:w-5 -mt-3',
                    connectorClass(i),
                  )} />
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
