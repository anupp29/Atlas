import { cn } from '@/lib/utils';
import type { HealthStatus } from '@/types/atlas';

const statusColors: Record<HealthStatus, string> = {
  healthy: 'bg-status-healthy',
  warning: 'bg-status-warning',
  critical: 'bg-status-critical',
};

export function StatusIndicator({ status, className }: { status: HealthStatus; className?: string }) {
  return (
    <span
      className={cn('inline-block h-2 w-2 rounded-full shrink-0', statusColors[status], className)}
      aria-label={status}
    />
  );
}
