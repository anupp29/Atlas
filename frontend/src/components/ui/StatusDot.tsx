import { cn } from '@/lib/utils'

type Status = 'healthy' | 'warning' | 'incident' | 'unknown'

const colourMap: Record<Status, string> = {
  healthy:  'bg-healthy',
  warning:  'bg-warning',
  incident: 'bg-incident',
  unknown:  'bg-zinc-500',
}

const pulseMap: Record<Status, string> = {
  healthy:  '',
  warning:  'animate-pulse-slow',
  incident: 'animate-pulse',
  unknown:  '',
}

interface StatusDotProps {
  status: Status
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

const sizeMap = { sm: 'w-1.5 h-1.5', md: 'w-2 h-2', lg: 'w-2.5 h-2.5' }

export function StatusDot({ status, size = 'md', className }: StatusDotProps) {
  return (
    <span
      className={cn(
        'inline-block rounded-full',
        sizeMap[size],
        colourMap[status],
        pulseMap[status],
        className,
      )}
    />
  )
}
