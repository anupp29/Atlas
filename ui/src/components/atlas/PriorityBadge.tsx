import { cn } from '@/lib/utils';
import type { IncidentPriority } from '@/types/atlas';

export function PriorityBadge({ priority, className }: { priority: IncidentPriority; className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center justify-center rounded-full px-2 py-0.5 text-[11px] font-semibold leading-none text-accent-foreground',
        priority === 'P1' && 'bg-status-critical',
        priority === 'P2' && 'bg-status-warning',
        priority === 'P3' && 'bg-muted text-muted-foreground',
        className,
      )}
    >
      {priority}
    </span>
  );
}
