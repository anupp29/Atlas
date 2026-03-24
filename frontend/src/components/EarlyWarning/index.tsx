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
      className="rounded-xl border-l-4 border-l-amber-400 border border-amber-200 bg-amber-50 p-4"
    >
      <div className="flex items-center gap-2 mb-3">
        <span className="text-amber-500 text-base">⚠</span>
        <h4 className="text-xs font-semibold uppercase tracking-widest text-amber-700">
          Early Warning — Adjacent Services
        </h4>
      </div>

      <div className="space-y-2">
        {signals.map(signal => (
          <div
            key={signal.service_name}
            className="flex items-center justify-between text-xs bg-white/60 rounded-lg px-3 py-2 border border-amber-100"
          >
            <span className="text-ink font-medium">{signal.service_name}</span>
            <div className="flex items-center gap-3">
              <span className="font-mono text-amber-700 font-bold">
                {signal.deviation_sigma.toFixed(1)}σ
              </span>
              <span className={
                signal.trend === 'rising' ? 'text-red-500 font-bold' :
                signal.trend === 'falling' ? 'text-emerald-600' : 'text-slate-400'
              }>
                {signal.trend === 'rising' ? '↑' : signal.trend === 'falling' ? '↓' : '→'}
              </span>
              <span className="text-faint">{relativeTime(signal.detected_at)}</span>
            </div>
          </div>
        ))}
      </div>

      <p className="text-xs text-amber-600 mt-3 leading-relaxed">
        Below alert threshold but showing deviation from baseline. Monitoring elevated.
      </p>
    </motion.div>
  )
}
