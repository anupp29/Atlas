import { useEffect, useState } from 'react'
import { secondsUntil } from '@/lib/utils'

/**
 * Counts down to a future ISO datetime. Returns seconds remaining and a
 * colour tier for the SLA timer display.
 */
export function useSLACountdown(slaBreachTime: string): {
  secondsRemaining: number
  tier: 'safe' | 'warning' | 'critical' | 'breached'
} {
  const [secondsRemaining, setSecondsRemaining] = useState(() =>
    secondsUntil(slaBreachTime),
  )

  useEffect(() => {
    const tick = () => setSecondsRemaining(secondsUntil(slaBreachTime))
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [slaBreachTime])

  const tier =
    secondsRemaining <= 0     ? 'breached' :
    secondsRemaining <= 120   ? 'critical' :
    secondsRemaining <= 300   ? 'warning'  : 'safe'

  return { secondsRemaining, tier }
}
