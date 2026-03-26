import type { ActivityFeedEntry } from '@/types/atlas';
import { cn } from '@/lib/utils';

const healthColors: Record<string, string> = {
  healthy: 'text-status-healthy',
  warning: 'text-status-warning',
  critical: 'text-status-critical',
};

export function ActivityFeed({ entries }: { entries: ActivityFeedEntry[] }) {
  return (
    <div className="flex flex-col">
      {entries.map((entry) => (
        <div
          key={entry.id}
          className={cn(
            'px-4 py-2 border-b border-border',
            entry.priority === 'P1' && 'border-l-[3px] border-l-status-critical bg-destructive/[0.02]',
            entry.priority === 'P2' && 'border-l-[3px] border-l-status-warning',
            !entry.priority && 'border-l-[3px] border-l-transparent',
          )}
        >
          <div className="flex items-start gap-2">
            <span className="font-mono text-[10px] text-muted-foreground shrink-0 mt-[1px] tabular-nums">
              {entry.timestamp}
            </span>
            <p className="text-[11px] leading-[1.45]">
              <span className={cn('font-medium', healthColors[entry.clientHealth])}>
                {entry.clientName}
              </span>
              <span className="text-muted-foreground"> — {entry.description}</span>
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
