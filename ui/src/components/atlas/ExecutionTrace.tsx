import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { Check, X, Loader2 } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, ReferenceLine, ResponsiveContainer } from 'recharts';

export interface ExecutionStepData {
  id: string;
  description: string;
  status: 'pending' | 'running' | 'complete' | 'failed';
  timestamp?: string;
}

interface ExecutionTraceProps {
  playbookName: string;
  onComplete?: () => void;
}

const initialSteps: ExecutionStepData[] = [
  { id: 'pre', description: 'Pre-execution validation: checking service endpoints and prerequisites', status: 'pending' },
  { id: 'exec', description: 'Executing action: PATCH /actuator/config — updating maxPoolSize to 150', status: 'pending' },
  { id: 'monitor', description: 'Monitoring recovery: tracking connection pool utilization and response times', status: 'pending' },
  { id: 'resolve', description: 'Resolution confirmed: all success criteria met', status: 'pending' },
];

// Simulated metric recovery data
function generateRecoveryData(phase: number) {
  const data = [];
  for (let i = 0; i <= 20; i++) {
    let value: number;
    if (i <= 8) {
      value = 90 + Math.random() * 8; // Pre-fix: high
    } else if (i <= 12) {
      value = 90 - (i - 8) * 12 + Math.random() * 5; // Dropping
    } else {
      value = 42 + Math.random() * 8; // Recovered
    }
    if (phase < 2 && i > 12) continue;
    if (phase < 1 && i > 8) continue;
    data.push({ time: `${i * 15}s`, value: Math.max(0, Math.min(100, value)) });
  }
  return data;
}

export function ExecutionTrace({ playbookName, onComplete }: ExecutionTraceProps) {
  const [steps, setSteps] = useState<ExecutionStepData[]>(initialSteps);
  const [recoveryPhase, setRecoveryPhase] = useState(0);

  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = [];

    // Step 1: Pre-validation running
    timers.push(setTimeout(() => {
      setSteps(prev => prev.map((s, i) => i === 0 ? { ...s, status: 'running' } : s));
    }, 500));

    // Step 1: Complete
    timers.push(setTimeout(() => {
      setSteps(prev => prev.map((s, i) => i === 0 ? { ...s, status: 'complete', timestamp: new Date().toLocaleTimeString('en-GB') } : s));
    }, 2500));

    // Step 2: Running
    timers.push(setTimeout(() => {
      setSteps(prev => prev.map((s, i) => i === 1 ? { ...s, status: 'running' } : s));
    }, 3000));

    // Step 2: Complete
    timers.push(setTimeout(() => {
      setSteps(prev => prev.map((s, i) => i === 1 ? { ...s, status: 'complete', timestamp: new Date().toLocaleTimeString('en-GB') } : s));
      setRecoveryPhase(1);
    }, 5000));

    // Step 3: Running (monitoring)
    timers.push(setTimeout(() => {
      setSteps(prev => prev.map((s, i) => i === 2 ? { ...s, status: 'running' } : s));
    }, 5500));

    // Recovery progressing
    timers.push(setTimeout(() => setRecoveryPhase(2), 7500));

    // Step 3: Complete
    timers.push(setTimeout(() => {
      setSteps(prev => prev.map((s, i) => i === 2 ? { ...s, status: 'complete', timestamp: new Date().toLocaleTimeString('en-GB') } : s));
    }, 9500));

    // Step 4: Running & Complete
    timers.push(setTimeout(() => {
      setSteps(prev => prev.map((s, i) => i === 3 ? { ...s, status: 'running' } : s));
    }, 10000));

    timers.push(setTimeout(() => {
      setSteps(prev => prev.map((s, i) => i === 3 ? { ...s, status: 'complete', timestamp: new Date().toLocaleTimeString('en-GB') } : s));
      onComplete?.();
    }, 11500));

    return () => timers.forEach(clearTimeout);
  }, [onComplete]);

  const recoveryData = generateRecoveryData(recoveryPhase);
  const monitoringStep = steps.find(s => s.id === 'monitor');
  const showChart = monitoringStep?.status === 'running' || monitoringStep?.status === 'complete';

  return (
    <div className="bg-card border border-border rounded-lg p-5 shadow-atlas">
      <h3 className="text-base font-semibold text-foreground mb-4">
        Executing: <span className="font-mono text-sm text-accent">{playbookName}</span>
      </h3>

      <div className="space-y-0">
        {steps.map((step) => (
          <div key={step.id} className="flex items-start gap-3 py-2.5">
            {/* Status icon */}
            <div className="mt-0.5 shrink-0">
              {step.status === 'complete' && (
                <div className="h-5 w-5 rounded-full bg-status-healthy flex items-center justify-center">
                  <Check className="h-3 w-3 text-white" />
                </div>
              )}
              {step.status === 'failed' && (
                <div className="h-5 w-5 rounded-full bg-status-critical flex items-center justify-center">
                  <X className="h-3 w-3 text-white" />
                </div>
              )}
              {step.status === 'running' && (
                <div className="h-5 w-5 rounded-full bg-accent flex items-center justify-center">
                  <Loader2 className="h-3 w-3 text-white animate-spin" />
                </div>
              )}
              {step.status === 'pending' && (
                <div className="h-5 w-5 rounded-full bg-muted border border-border" />
              )}
            </div>

            {/* Description */}
            <div className="flex-1 min-w-0">
              <p className={cn(
                'text-sm',
                step.status === 'complete' && 'text-foreground',
                step.status === 'running' && 'text-foreground font-medium',
                step.status === 'pending' && 'text-muted-foreground',
                step.status === 'failed' && 'text-status-critical',
              )}>
                {step.description}
              </p>
            </div>

            {/* Timestamp */}
            {step.timestamp && (
              <span className="font-mono text-[11px] text-muted-foreground shrink-0">
                {step.timestamp}
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Recovery metric chart */}
      {showChart && (
        <div className="mt-4 pt-4 border-t border-border">
          <p className="text-[12px] font-medium text-muted-foreground mb-2">Connection Pool Utilization (%)</p>
          <div className="h-[140px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={recoveryData}>
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: 'hsl(215, 16%, 47%)' }} tickLine={false} axisLine={{ stroke: 'hsl(214, 32%, 91%)' }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: 'hsl(215, 16%, 47%)' }} tickLine={false} axisLine={false} width={30} />
                <ReferenceLine y={70} stroke="hsl(32, 95%, 44%)" strokeDasharray="4 4" label={{ value: 'Threshold', position: 'right', fill: 'hsl(32, 95%, 44%)', fontSize: 10 }} />
                <Line type="monotone" dataKey="value" stroke="hsl(211, 100%, 40%)" strokeWidth={2} dot={false} animationDuration={500} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
