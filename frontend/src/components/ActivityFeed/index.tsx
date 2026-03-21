import { useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn, activityBorderClass, timeOnly } from '@/lib/utils'
import { StatusDot } from '@/components/ui/StatusDot'
import type { ActivityEntry, ConnectionStatus } from '@/types/atlas'

interface ActivityFeedProps {
  entries: ActivityEntry[]
  status: ConnectionStatus
}

const TYPE_LABELS: Record<string, string> = {
  agent_detection:  'Agent',
  orchestrator_node: 'Orchestrator',
  human_action:     'Human',
  veto_fired:       'Veto',
  resolution:       'Resolution',
  early_warning:    'Warning',
  execution:        'Execution',
  cmdb_change:      'CMDB',
  incident_created: 'Incident',
}

export function ActivityFeed({ entries, status }: ActivityFeedProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to top (newest first)
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0
    }
  }, [entries.length])

  return (
    <aside className="w-80 shrink-0 border-l border-border bg-canvas flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border flex items-center justify-between shrink-0">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-500">
          Activity Feed
        </h2>
        <div className="flex items-center gap-1.5">
          <StatusDot
            status={status === 'connected' ? 'healthy' : status === 'reconnecting' ? 'warning' : 'incident'}
            size="sm"
          />
          <span className="text-xs text-zinc-600">{entries.length}</span>
        </div>
      </div>

      {/* Disconnected banner */}
      {status === 'disconnected' && (
        <div className="px-3 py-2 bg-red-950 border-b border-red-900 text-xs text-red-300 text-center">
          Backend disconnected — data may be stale
        </div>
      )}
      {status === 'reconnecting' && (
        <div className="px-3 py-2 bg-amber-950 border-b border-amber-900 text-xs text-amber-300 text-center">
          Reconnecting…
        </div>
      )}

      {/* Feed */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto scrollbar-thin scrollbar-track-canvas scrollbar-thumb-border"
      >
        {entries.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-zinc-600 text-xs">
            <span>Monitoring active</span>
            <span className="mt-1 text-zinc-700">Waiting for events…</span>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {entries.map(entry => (
              <motion.div
                key={entry.id}
                initial={{ opacity: 0, x: 8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2 }}
                className={cn(
                  'border-l-2 px-3 py-2 border-b border-border/50 hover:bg-elevated/40 transition-colors',
                  activityBorderClass(entry.type),
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <span className="font-mono text-xs text-zinc-500 shrink-0 tabular-nums">
                    {timeOnly(entry.timestamp)}
                  </span>
                  <span className="text-xs text-zinc-600 shrink-0">
                    {TYPE_LABELS[entry.type] ?? entry.type}
                  </span>
                </div>
                <p className="text-xs text-zinc-300 mt-0.5 leading-relaxed break-words">
                  {entry.message}
                </p>
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>
    </aside>
  )
}
