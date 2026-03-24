import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { nowUTC, cn } from '@/lib/utils'
import type { ConnectionStatus } from '@/types/atlas'

interface TopBarProps {
  incidentStatus: ConnectionStatus
  activityStatus: ConnectionStatus
  onTriggerDemo: (clientId: string) => void
  demoRunning: boolean
}

export function TopBar({ incidentStatus, activityStatus, onTriggerDemo, demoRunning }: TopBarProps) {
  const [time, setTime] = useState(nowUTC)

  useEffect(() => {
    const id = setInterval(() => setTime(nowUTC()), 1000)
    return () => clearInterval(id)
  }, [])

  const overallStatus: ConnectionStatus =
    incidentStatus === 'disconnected' || activityStatus === 'disconnected'
      ? 'disconnected'
      : incidentStatus === 'reconnecting' || activityStatus === 'reconnecting'
      ? 'reconnecting'
      : 'connected'

  const statusConfig = {
    connected:    { dot: 'bg-emerald-500', label: 'Live',           text: 'text-emerald-700', bg: 'bg-emerald-50 border-emerald-200' },
    reconnecting: { dot: 'bg-amber-500 animate-pulse', label: 'Reconnecting…', text: 'text-amber-700', bg: 'bg-amber-50 border-amber-200' },
    disconnected: { dot: 'bg-red-500',    label: 'Disconnected',   text: 'text-red-700',     bg: 'bg-red-50 border-red-200' },
  }[overallStatus]

  return (
    <header className="h-14 flex items-center justify-between px-6 border-b border-border bg-white shadow-sm shrink-0 z-50">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-violet-600 flex items-center justify-center shadow-sm">
          <span className="text-white text-sm font-bold select-none">◈</span>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-ink font-bold tracking-tight text-base">ATLAS</span>
          <span className="text-faint text-xs font-mono">AIOps Platform</span>
        </div>
        <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded-full bg-blue-50 border border-blue-100 text-xs text-blue-600 font-medium">
          Atos Managed Services
        </span>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={() => onTriggerDemo('FINCORE_UK_001')}
          disabled={demoRunning}
          className={cn(
            'px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all duration-150',
            demoRunning
              ? 'bg-slate-100 text-slate-400 border-slate-200 cursor-not-allowed'
              : 'bg-red-50 text-red-700 border-red-200 hover:bg-red-100 shadow-sm hover:shadow',
          )}
        >
          {demoRunning ? '⏳ Demo Running…' : '▶ FinanceCore Demo'}
        </button>
        <button
          onClick={() => onTriggerDemo('RETAILMAX_EU_002')}
          disabled={demoRunning}
          className={cn(
            'px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all duration-150',
            demoRunning
              ? 'bg-slate-100 text-slate-400 border-slate-200 cursor-not-allowed'
              : 'bg-violet-50 text-violet-700 border-violet-200 hover:bg-violet-100 shadow-sm hover:shadow',
          )}
        >
          {demoRunning ? '' : '▶ RetailMax Demo'}
        </button>

        <AnimatePresence mode="wait">
          <motion.div
            key={overallStatus}
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            transition={{ duration: 0.2 }}
            className={cn(
              'flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium',
              statusConfig.bg, statusConfig.text,
            )}
          >
            <span className={cn('w-1.5 h-1.5 rounded-full', statusConfig.dot)} />
            {statusConfig.label}
          </motion.div>
        </AnimatePresence>

        <div className="hidden md:flex items-center px-2.5 py-1 rounded-full bg-slate-50 border border-slate-200">
          <span className="font-mono text-xs text-subtle tabular-nums">{time}</span>
        </div>
      </div>
    </header>
  )
}
