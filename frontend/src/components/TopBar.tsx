import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { nowUTC } from '@/lib/utils'
import { cn } from '@/lib/utils'
import type { ConnectionStatus } from '@/types/atlas'

interface TopBarProps {
  incidentStatus: ConnectionStatus
  activityStatus: ConnectionStatus
}

export function TopBar({ incidentStatus, activityStatus }: TopBarProps) {
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
    connected:    { dot: 'bg-healthy animate-pulse-slow', label: 'Connected',    text: 'text-healthy' },
    reconnecting: { dot: 'bg-warning animate-pulse',      label: 'Reconnecting…', text: 'text-warning' },
    disconnected: { dot: 'bg-incident',                   label: 'Disconnected', text: 'text-incident' },
  }[overallStatus]

  return (
    <header className="h-12 flex items-center justify-between px-5 border-b border-border bg-[#0D1117] shrink-0 z-50">
      {/* Logo */}
      <div className="flex items-center gap-2.5">
        <span className="text-blue-400 text-lg font-bold tracking-tight select-none">◈</span>
        <span className="text-white font-semibold tracking-widest text-sm uppercase">ATLAS</span>
        <span className="text-zinc-600 text-xs font-mono ml-1">AIOps Platform</span>
      </div>

      {/* Right cluster */}
      <div className="flex items-center gap-5">
        {/* Connection status */}
        <AnimatePresence mode="wait">
          <motion.div
            key={overallStatus}
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            transition={{ duration: 0.2 }}
            className="flex items-center gap-1.5"
          >
            <span className={cn('w-1.5 h-1.5 rounded-full', statusConfig.dot)} />
            <span className={cn('text-xs font-medium', statusConfig.text)}>
              {statusConfig.label}
            </span>
          </motion.div>
        </AnimatePresence>

        {/* UTC clock */}
        <span className="font-mono text-xs text-zinc-400 tabular-nums">{time}</span>
      </div>
    </header>
  )
}
