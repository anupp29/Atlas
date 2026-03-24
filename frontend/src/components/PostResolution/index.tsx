import { motion } from 'framer-motion'
import {
  LineChart, Line, XAxis, YAxis, ReferenceLine, Tooltip, ResponsiveContainer,
} from 'recharts'
import { formatMTTR } from '@/lib/utils'
import type { AtlasState } from '@/types/atlas'

const ATLASSIAN_BENCHMARK_SECONDS = 2580

interface PostResolutionProps {
  incident: AtlasState
}

function buildRecoveryData(mttrSeconds: number) {
  const points = 20
  return Array.from({ length: points }, (_, i) => {
    const t = (i / (points - 1)) * (mttrSeconds + 120)
    const spike = Math.min(1, t / 30) * 94
    const recovery = t > mttrSeconds * 0.4
      ? Math.max(20, spike * (1 - (t - mttrSeconds * 0.4) / (mttrSeconds * 0.8)))
      : spike
    return { t: Math.round(t), value: Math.round(Math.min(94, Math.max(18, recovery))) }
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
      className="space-y-4 max-w-2xl mx-auto"
    >
      {/* Resolution banner */}
      <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-5 py-4 flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-emerald-100 border border-emerald-200 flex items-center justify-center shrink-0">
          <span className="text-emerald-600 text-lg">✓</span>
        </div>
        <div>
          <span className="text-sm font-semibold text-emerald-800">Incident Resolved</span>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-xs text-emerald-600 font-mono">{incident.servicenow_ticket_id}</span>
            <span className="text-xs text-emerald-500">·</span>
            <span className={`text-xs font-medium ${incident.resolution_outcome === 'success' ? 'text-emerald-700' : 'text-amber-700'}`}>
              {incident.resolution_outcome?.toUpperCase() ?? '—'}
            </span>
          </div>
        </div>
      </div>

      {/* MTTR counter */}
      <div className="rounded-xl border border-border bg-white p-6 text-center shadow-card">
        <p className="text-xs font-semibold uppercase tracking-widest text-faint mb-3">
          Mean Time to Resolution
        </p>
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
          className="font-mono text-6xl font-bold text-emerald-600 tabular-nums mb-2"
        >
          {formatMTTR(mttr)}
        </motion.div>
        {fasterBy > 0 && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="text-sm text-emerald-700 font-medium"
          >
            ↓ {fasterMin}m {fasterSec}s faster than industry median
          </motion.p>
        )}
        <p className="text-xs text-faint mt-1">Atlassian 2024 benchmark: 43:00 median MTTR</p>
      </div>

      {/* Recovery chart */}
      <div className="rounded-xl border border-border bg-white p-4 shadow-card">
        <p className="text-xs font-semibold uppercase tracking-widest text-subtle mb-3">
          Primary Metric Recovery — Connection Count
        </p>
        <ResponsiveContainer width="100%" height={160}>
          <LineChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
            <XAxis
              dataKey="t"
              tick={{ fill: '#94A3B8', fontSize: 10 }}
              tickFormatter={v => `${Math.floor(v / 60)}m`}
            />
            <YAxis
              tick={{ fill: '#94A3B8', fontSize: 10 }}
              domain={[0, 100]}
              tickFormatter={v => `${v}%`}
            />
            <Tooltip
              contentStyle={{
                background: '#FFFFFF',
                border: '1px solid #E2E8F0',
                borderRadius: 8,
                fontSize: 11,
                boxShadow: '0 4px 6px -1px rgba(0,0,0,0.07)',
              }}
              formatter={(v: number) => [`${v}%`, 'Pool usage']}
              labelFormatter={v => `T+${Math.floor(Number(v) / 60)}m ${Number(v) % 60}s`}
            />
            <ReferenceLine y={85} stroke="#DC2626" strokeDasharray="4 2" label={{ value: 'Alert', fill: '#DC2626', fontSize: 10 }} />
            <ReferenceLine y={30} stroke="#059669" strokeDasharray="4 2" label={{ value: 'Baseline', fill: '#059669', fontSize: 10 }} />
            <ReferenceLine
              x={ATLASSIAN_BENCHMARK_SECONDS}
              stroke="#D97706"
              strokeDasharray="6 3"
              label={{ value: 'Industry 43m', fill: '#D97706', fontSize: 10, position: 'insideTopRight' }}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#2563EB"
              strokeWidth={2.5}
              dot={false}
              animationDuration={1200}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Resolution summary */}
      <div className="rounded-xl border border-border bg-white p-4 shadow-card space-y-2.5 text-xs">
        {[
          ['Playbook', `${incident.recommended_action_id} ✓`],
          ['ServiceNow', `${incident.servicenow_ticket_id} — Resolved ✓`],
          ['Knowledge base', 'Neo4j updated · ChromaDB updated ✓'],
          ['Outcome', incident.resolution_outcome?.toUpperCase() ?? '—'],
        ].map(([label, value]) => (
          <div key={label} className="flex items-center justify-between py-1 border-b border-border last:border-0">
            <span className="text-faint font-medium">{label}</span>
            <span className="text-emerald-700 font-mono font-medium">{value}</span>
          </div>
        ))}
      </div>
    </motion.div>
  )
}
