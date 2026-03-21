import { motion } from 'framer-motion'
import { cn, formatCountdown } from '@/lib/utils'
import { useSLACountdown } from '@/hooks/useSLACountdown'

interface SLATimerProps {
  slaBreachTime: string
  ticketId: string
}

export function SLATimer({ slaBreachTime, ticketId }: SLATimerProps) {
  const { secondsRemaining, tier } = useSLACountdown(slaBreachTime)

  const timerColour = {
    safe:     'text-healthy',
    warning:  'text-warning',
    critical: 'text-incident',
    breached: 'text-incident',
  }[tier]

  const boxBorder = {
    safe:     'border-healthy/30',
    warning:  'border-warning/50',
    critical: 'border-incident/60',
    breached: 'border-incident',
  }[tier]

  return (
    <div className="flex items-center gap-4">
      <div className={cn('border rounded-lg px-4 py-2 text-center min-w-[100px]', boxBorder)}>
        <motion.span
          key={tier}
          animate={tier === 'critical' ? { opacity: [1, 0.4, 1] } : {}}
          transition={{ duration: 1, repeat: Infinity }}
          className={cn('font-mono text-3xl font-bold tabular-nums block', timerColour)}
        >
          {tier === 'breached' ? 'BREACHED' : formatCountdown(secondsRemaining)}
        </motion.span>
        <span className="text-xs text-zinc-500 mt-0.5 block">SLA Breach</span>
      </div>

      <div className="text-xs text-zinc-500">
        <div>ServiceNow</div>
        <div className="font-mono text-zinc-300 font-medium">{ticketId || '—'}</div>
      </div>
    </div>
  )
}
