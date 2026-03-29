import { useEffect, useRef } from 'react';
import { X, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ActivityFeedEntry } from '@/types/atlas';

const healthColors: Record<string, string> = {
  healthy: 'text-status-healthy',
  warning: 'text-status-warning',
  critical: 'text-status-critical',
};

const healthDot: Record<string, string> = {
  healthy: 'bg-status-healthy',
  warning: 'bg-status-warning',
  critical: 'bg-status-critical',
};

interface ActivityDrawerProps {
  open: boolean;
  onClose: () => void;
  entries: ActivityFeedEntry[];
}

export function ActivityDrawer({ open, onClose, entries }: ActivityDrawerProps) {
  const drawerRef = useRef<HTMLDivElement>(null);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, onClose]);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (drawerRef.current && !drawerRef.current.contains(e.target as Node)) onClose();
    };
    // Delay to avoid immediate close on the button click that opened it
    const t = setTimeout(() => document.addEventListener('mousedown', handler), 50);
    return () => { clearTimeout(t); document.removeEventListener('mousedown', handler); };
  }, [open, onClose]);

  const p1Count = entries.filter(e => e.priority === 'P1').length;
  const p2Count = entries.filter(e => e.priority === 'P2').length;

  return (
    <>
      {/* Backdrop */}
      <div
        className={cn(
          'fixed inset-0 bg-black/20 backdrop-blur-[1px] z-40 transition-opacity duration-200',
          open ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none',
        )}
      />

      {/* Drawer */}
      <div
        ref={drawerRef}
        className={cn(
          'fixed top-0 right-0 h-full w-[360px] bg-card border-l border-border shadow-2xl z-50 flex flex-col transition-transform duration-200 ease-out',
          open ? 'translate-x-0' : 'translate-x-full',
        )}
      >
        {/* Header */}
        <div className="px-4 py-3.5 border-b border-border flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="h-6 w-6 rounded bg-accent/10 flex items-center justify-center">
              <Activity className="h-3.5 w-3.5 text-accent" />
            </div>
            <div>
              <h2 className="text-[13px] font-semibold text-foreground">Activity Feed</h2>
              <p className="text-[10px] text-muted-foreground">{entries.length} events</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {/* Live indicator */}
            <div className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-status-healthy live-dot" />
              <span className="text-[10px] text-muted-foreground">Live</span>
            </div>
            <button
              onClick={onClose}
              className="h-7 w-7 rounded-lg flex items-center justify-center hover:bg-muted transition-colors"
            >
              <X className="h-3.5 w-3.5 text-muted-foreground" />
            </button>
          </div>
        </div>

        {/* Summary pills */}
        {(p1Count > 0 || p2Count > 0) && (
          <div className="px-4 py-2 border-b border-border flex items-center gap-2 shrink-0">
            {p1Count > 0 && (
              <span className="flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-status-critical/10 text-status-critical">
                <span className="h-1.5 w-1.5 rounded-full bg-status-critical" />
                {p1Count} P1
              </span>
            )}
            {p2Count > 0 && (
              <span className="flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-status-warning/10 text-status-warning">
                <span className="h-1.5 w-1.5 rounded-full bg-status-warning" />
                {p2Count} P2
              </span>
            )}
          </div>
        )}

        {/* Feed */}
        <div className="flex-1 overflow-auto">
          {entries.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center px-6">
              <Activity className="h-8 w-8 text-muted-foreground/30 mb-3" />
              <p className="text-[13px] text-foreground font-medium">No activity yet</p>
              <p className="text-[11px] text-muted-foreground mt-1">Events will appear here as ATLAS monitors your infrastructure.</p>
            </div>
          ) : (
            <div className="flex flex-col">
              {entries.map((entry) => (
                <div
                  key={entry.id}
                  className={cn(
                    'px-4 py-3 border-b border-border/60 transition-colors hover:bg-muted/20',
                    entry.priority === 'P1' && 'border-l-[3px] border-l-status-critical bg-destructive/[0.015]',
                    entry.priority === 'P2' && 'border-l-[3px] border-l-status-warning',
                    !entry.priority && 'border-l-[3px] border-l-transparent',
                  )}
                >
                  <div className="flex items-start gap-2.5">
                    {/* Client health dot */}
                    <span className={cn('h-1.5 w-1.5 rounded-full shrink-0 mt-[5px]', healthDot[entry.clientHealth] || 'bg-muted-foreground')} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2 mb-0.5">
                        <span className={cn('text-[11px] font-semibold truncate', healthColors[entry.clientHealth])}>
                          {entry.clientName}
                        </span>
                        <span className="font-mono text-[9px] text-muted-foreground shrink-0 tabular-nums">
                          {entry.timestamp}
                        </span>
                      </div>
                      <p className="text-[11px] text-muted-foreground leading-[1.5]">{entry.description}</p>
                      {entry.priority && (
                        <span className={cn(
                          'inline-flex items-center gap-1 mt-1.5 text-[9px] font-semibold px-1.5 py-0.5 rounded',
                          entry.priority === 'P1' ? 'bg-status-critical/10 text-status-critical' : 'bg-status-warning/10 text-status-warning',
                        )}>
                          {entry.priority}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2.5 border-t border-border shrink-0">
          <p className="text-[10px] text-muted-foreground text-center">
            Showing last {entries.length} events · Auto-updates via WebSocket
          </p>
        </div>
      </div>
    </>
  );
}
