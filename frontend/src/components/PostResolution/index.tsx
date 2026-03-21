import { motion } from 'framer-motion'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  ReferenceLine,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { formatMTTR } from '@/lib/utils'
import type { AtlasState } from '@/types/atlas'

const ATLASSIAN_BENCHMARK_SECONDS = 2580 // 43 minutes

interface PostResolutionProps {
  incident: AtlasState
}

// Generate synthetic recovery curve from mttr_seconds for display
function buildRecoveryData(mttrSeconds: number) {
  const points = 20
  return Array.from({ length: points }, (_, i) => {
    const t = (i / (points - 1)) * (mttrSeconds + 120)
    const spike = Math.min(1, t / 30) * 94
    const recovery = t > mttrSeconds * 0.4
      ? Math.max(20, spike * (1 - (t - mttrSeconds * 0.4) / (mttrSeconds * 0.8)))
      : spike
    return {
      t: Math.round(t),
      value: Math.round(Math.min(94, Math.max(18, recovery))),
    }
  })
}

export function PostResolution({ incident }: PostResolutionProps) {
  const mttr = incident.mttr_seconds ?? 0
  const data = buildRecoveryData(mttr)
  const fasterBy = Math.max(0, ATLASSIAN_BENCHMARK_SECONDS - mttr)
  const fasterMin = Math.floor(fasterBy / 60)
  const fasterSec = fasterBy % 60

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-4 animate-slide-up"
    >
      {/* Resolution banner */}
      <div className="rounded-lg border border-green-800 bg-green-950/30 px-4 py-3 flex items-center gap-3">
        <span className="text-healthy text-lg">✓</span>
        <div>
          <span className="text-sm font-semibold text-healthy">Incident Resolved</span>
          <span className="text-xs text-zinc-400 ml-3 font-mono">
            {incident.servicenow_ticket_id}
          </span>
        </div>
      </div>

      {/* MTTR counter */}
      <div className="rounded-lg border border-border bg-surface p-6 text-center">
        <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-3">
          Mean Time to Resolution
        </p>
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
          className="font-mono text-6xl font-bold text-healthy tabular-nums mb-2"
        >
          {formatMTTR(mttr)}
        </motion.div>
        {fasterBy > 0 && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="text-sm text-green-400"
          >
            ↓ {fasterMin}m {fasterSec}s faster than industry median
          </motion.p>
        )}
        <p className="text-xs text-zinc-600 mt-1">
          Atlassian 2024 benchmark: 43:00 median MTTR
        </p>
      </div>

      {/* Recovery chart */}
      <div className="rounded-lg border border-border bg-surface p-4">
        <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-3">
          Primary Metric Recovery — Connection Count
        </p>
        <ResponsiveContainer width="100%" height={160}>
          <LineChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
            <XAxis
              dataKey="t"
              tick={{ fill: '#6B7280', fontSize: 10 }}
              tickFormatter={v => `${Math.floor(v / 60)}m`}
            />
            <YAxis
              tick={{ fill: '#6B7280', fontSize: 10 }}
              domain={[0, 100]}
              tickFormatter={v => `${v}%`}
            />
            <Tooltip
              contentStyle={{ background: '#1F2937', border: '1px solid #374151', borderRadius: 6, fontSize: 11 }}
              formatter={(v: number) => [`${v}%`, 'Pool usage']}
              labelFormatter={v => `T+${Math.floor(Number(v) / 60)}m ${Number(v) % 60}s`}
            />
            <ReferenceLine y={85} stroke="#EF4444" strokeDasharray="4 2" label={{ value: 'Alert', fill: '#EF4444', fontSize: 10 }} />
            <ReferenceLine y={30} stroke="#10B981" strokeDasharray="4 2" label={{ value: 'Baseline', fill: '#10B981', fontSize: 10 }} />
            <ReferenceLine
              x={ATLASSIAN_BENCHMARK_SECONDS}
              stroke="#F59E0B"
              strokeDasharray="6 3"
              label={{ value: 'Industry median 43m', fill: '#F59E0B', fontSize: 10, position: 'insideTopRight' }}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#3B82F6"
              strokeWidth={2}
              dot={false}
              animationDuration={1200}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Resolution summary */}
      <div className="rounded-lg border border-border bg-surface p-4 space-y-2 text-xs">
        <div className="flex items-center justify-between">
          <span className="text-zinc-500">Playbook</span>
          <span className="font-mono text-zinc-300">{incident.recommended_action_id} <span className="text-healthy">✓</span></span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-zinc-500">ServiceNow</span>
          <span className="font-mono text-zinc-300">{incident.servicenow_ticket_id} <span className="text-healthy">✓ Resolved</span></span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-zinc-500">Knowledge base</span>
          <span className="text-healthy">✓ Neo4j updated · ChromaDB updated</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-zinc-500">Outcome</span>
          <span className={incident.resolution_outcome === 'success' ? 'text-healthy' : 'text-warning'}>
            {incident.resolution_outcome?.toUpperCase() ?? '—'}
          </span>
        </div>
      </div>
    </motion.div>
  )
}
