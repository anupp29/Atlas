import { motion } from 'framer-motion'
import { cn, formatCountdown } from '@/lib/utils'
import { useSLACountdown } from '@/hooks/useSLACountdown'

interface SLATimerProps {
  slaBreachTime: string
  ticketId: string
}

export function SLATimer({ slaBreachTime, ticketId }: SLATimerProps) {
  const { secondsRemaining, tier } = useSLACountdown(slaBreachTime)

  const config = {
    safe:     { border: 'border-emerald-200 bg-emerald-50', text: 'text-emerald-700', label: 'text-emerald-500' },
    warning:  { border: 'border-amber-200 bg-amber-50',     text: 'text-amber-700',   label: 'text-amber-500' },
    critical: { border: 'border-red-200 bg-red-50',         text: 'text-red-700',     label: 'text-red-500' },
    breached: { border: 'border-red-300 bg-red-100',        text: 'text-red-800',     label: 'text-red-600' },
  }[tier]

  return (
    <div className="flex items-center gap-3">
      <div className={cn('border rounded-xl px-4 py-2 text-center min-w-[110px]', config.border)}>
        <motion.span
          key={tier}
          animate={tier === 'critical' ? { opacity: [1, 0.5, 1] } : {}}
          transition={{ duration: 1, repeat: Infinity }}
          className={cn('font-mono text-2xl font-bold tabular-nums block', config.text)}
        >
          {tier === 'breached' ? 'BREACHED' : formatCountdown(secondsRemaining)}
        </motion.span>
        <span className={cn('text-xs mt-0.5 block font-medium', config.label)}>SLA Breach</span>
      </div>
      <div className="text-xs">
        <div className="text-faint">ServiceNow</div>
        <div className="font-mono text-ink font-semibold">{ticketId || '—'}</div>
      </div>
    </div>
  )
}
