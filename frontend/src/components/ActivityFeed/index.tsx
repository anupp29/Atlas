import { useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn, activityBorderClass, activityIcon, timeOnly } from '@/lib/utils'
import { StatusDot } from '@/components/ui/StatusDot'
import type { ActivityEntry, ConnectionStatus } from '@/types/atlas'

interface ActivityFeedProps {
  entries: ActivityEntry[]
  status: ConnectionStatus
}

const TYPE_LABELS: Record<string, string> = {
  agent_detection:   'Agent',
  orchestrator_node: 'Orchestrator',
  human_action:      'Human',
  veto_fired:        'Veto',
  resolution:        'Resolution',
  early_warning:     'Warning',
  execution:         'Execution',
  cmdb_change:       'CMDB',
  incident_created:  'Incident',
}

const TYPE_BG: Record<string, string> = {
  agent_detection:   'bg-orange-50 text-orange-700',
  orchestrator_node: 'bg-blue-50 text-blue-700',
  human_action:      'bg-emerald-50 text-emerald-700',
  veto_fired:        'bg-red-50 text-red-700',
  resolution:        'bg-teal-50 text-teal-700',
  early_warning:     'bg-amber-50 text-amber-700',
  execution:         'bg-blue-50 text-blue-700',
  cmdb_change:       'bg-yellow-50 text-yellow-700',
  incident_created:  'bg-red-50 text-red-700',
}

export function ActivityFeed({ entries, status }: ActivityFeedProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = 0
  }, [entries.length])

  return (
    <aside className="w-80 shrink-0 border-l border-border bg-white flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border bg-slate-50 flex items-center justify-between shrink-0">
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-widest text-subtle">
            Activity Feed
          </h2>
          <p className="text-xs text-faint mt-0.5">{entries.length} events</p>
        </div>
        <StatusDot
          status={status === 'connected' ? 'healthy' : status === 'reconnecting' ? 'warning' : 'incident'}
          size="md"
        />
      </div>

      {/* Status banners */}
      {status === 'disconnected' && (
        <div className="px-3 py-2 bg-red-50 border-b border-red-200 text-xs text-red-700 text-center font-medium">
          Backend disconnected — data may be stale
        </div>
      )}
      {status === 'reconnecting' && (
        <div className="px-3 py-2 bg-amber-50 border-b border-amber-200 text-xs text-amber-700 text-center font-medium">
          Reconnecting…
        </div>
      )}

      {/* Feed */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto"
      >
        {entries.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 text-faint text-xs gap-1">
            <span className="text-2xl">📡</span>
            <span className="font-medium text-subtle">Monitoring active</span>
            <span>Waiting for events…</span>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {entries.map(entry => (
              <motion.div
                key={entry.id}
                initial={{ opacity: 0, x: 12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2 }}
                className={cn(
                  'border-l-2 px-3 py-2.5 border-b border-border/60 hover:bg-slate-50 transition-colors',
                  activityBorderClass(entry.type),
                )}
              >
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className={cn(
                    'inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium',
                    TYPE_BG[entry.type] ?? 'bg-slate-100 text-subtle',
                  )}>
                    <span>{activityIcon(entry.type)}</span>
                    {TYPE_LABELS[entry.type] ?? entry.type}
                  </span>
                  <span className="font-mono text-xs text-faint tabular-nums shrink-0">
                    {timeOnly(entry.timestamp)}
                  </span>
                </div>
                <p className="text-xs text-subtle leading-relaxed break-words">
                  {entry.message}
                </p>
                {entry.meta && Object.keys(entry.meta).length > 0 && (
                  <div className="mt-1 flex flex-wrap gap-1">
                    {Object.entries(entry.meta).slice(0, 3).map(([k, v]) => (
                      <span key={k} className="text-xs font-mono text-faint">
                        {k}={String(v)}
                      </span>
                    ))}
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>
    </aside>
  )
}
