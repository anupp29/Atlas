import { cn } from '@/lib/utils'

interface CardProps {
  children: React.ReactNode
  className?: string
  glow?: 'none' | 'red' | 'amber' | 'green' | 'blue'
}

const glowMap = {
  none:  '',
  red:   'shadow-[0_0_20px_rgba(239,68,68,0.15)]',
  amber: 'shadow-[0_0_20px_rgba(245,158,11,0.15)]',
  green: 'shadow-[0_0_20px_rgba(16,185,129,0.15)]',
  blue:  'shadow-[0_0_20px_rgba(59,130,246,0.15)]',
}

export function Card({ children, className, glow = 'none' }: CardProps) {
  return (
    <div
      className={cn(
        'rounded-lg border border-border bg-surface',
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
    <h3 className={cn('text-xs font-semibold uppercase tracking-widest text-zinc-400', className)}>
      {children}
    </h3>
  )
}

export function CardBody({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn('p-4', className)}>{children}</div>
}
