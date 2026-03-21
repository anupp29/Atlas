import { motion } from 'framer-motion'
import { relativeTime } from '@/lib/utils'
import type { EarlyWarningSignal } from '@/types/atlas'

interface EarlyWarningProps {
  signals: EarlyWarningSignal[]
}

export function EarlyWarning({ signals }: EarlyWarningProps) {
  if (signals.length === 0) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="rounded-lg border-l-4 border-l-warning border border-amber-900/50 bg-[#1C1500] p-4"
    >
      <div className="flex items-center gap-2 mb-3">
        <span className="text-warning text-sm">⚠</span>
        <h4 className="text-xs font-semibold uppercase tracking-widest text-amber-400">
          Early Warning — Adjacent Services
        </h4>
      </div>

      <div className="space-y-2">
        {signals.map(signal => (
          <div
            key={signal.service_name}
            className="flex items-center justify-between text-xs"
          >
            <span className="text-zinc-300 font-medium">{signal.service_name}</span>
            <div className="flex items-center gap-3">
              <span className="font-mono text-amber-300 font-semibold">
                {signal.deviation_sigma.toFixed(1)}σ
              </span>
              <span className="text-amber-500">
                {signal.trend === 'rising' ? '↑' : signal.trend === 'falling' ? '↓' : '→'}
              </span>
              <span className="text-zinc-500">
                {relativeTime(signal.detected_at)}
              </span>
            </div>
          </div>
        ))}
      </div>

      <p className="text-xs text-zinc-600 mt-3 leading-relaxed">
        These services are below alert threshold but showing deviation from baseline.
        Monitoring elevated.
      </p>
    </motion.div>
  )
}
