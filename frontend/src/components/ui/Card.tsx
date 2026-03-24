import { cn } from '@/lib/utils'

interface CardProps {
  children: React.ReactNode
  className?: string
  glow?: 'none' | 'red' | 'amber' | 'green' | 'blue'
}

const glowMap = {
  none:  '',
  red:   'shadow-glow-red ring-1 ring-red-200',
  amber: 'shadow-glow-amber ring-1 ring-amber-200',
  green: 'shadow-glow-green ring-1 ring-green-200',
  blue:  'shadow-glow-blue ring-1 ring-blue-200',
}

export function Card({ children, className, glow = 'none' }: CardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border border-border bg-surface shadow-card',
        glowMap[glow],
        className,
      )}
    >
      {children}
    </div>
  )
}

export function CardHeader({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn('flex items-center justify-between px-4 py-3 border-b border-border', className)}>
      {children}
    </div>
  )
}

export function CardTitle({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <h3 className={cn('text-xs font-semibold uppercase tracking-widest text-subtle', className)}>
      {children}
    </h3>
  )
}

export function CardBody({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn('p-4', className)}>{children}</div>
}
