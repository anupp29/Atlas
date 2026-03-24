import { useEffect, useRef, useState } from 'react'
import { cn, logSeverityClass } from '@/lib/utils'
import type { LogLine } from '@/hooks/useIncident'

interface LogStreamProps {
  lines: LogLine[]
  clientId: string
}

const SEV_ICON: Record<string, string> = {
  FATAL: '💀',
  ERROR: '✖',
  WARN:  '⚠',
  INFO:  '·',
  DEBUG: '·',
}

export function LogStream({ lines, clientId }: LogStreamProps) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)

  useEffect(() => {
    if (autoScroll && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [lines, autoScroll])

  const handleScroll = () => {
    const el = containerRef.current
    if (!el) return
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40
    setAutoScroll(atBottom)
  }

  const errorCount = lines.filter(l => l.severity === 'ERROR' || l.severity === 'FATAL').length
  const warnCount  = lines.filter(l => l.severity === 'WARN').length

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border bg-slate-50 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse-slow" />
            <span className="text-xs font-semibold uppercase tracking-widest text-subtle">
              Live Log Stream
            </span>
          </div>
          <span className="text-xs text-faint font-mono">{clientId.replace(/_/g, ' ')}</span>
        </div>
        <div className="flex items-center gap-3">
          {errorCount > 0 && (
            <span className="flex items-center gap-1 text-xs font-medium text-red-600 bg-red-50 border border-red-200 px-2 py-0.5 rounded-full">
              ✖ {errorCount} error{errorCount !== 1 ? 's' : ''}
            </span>
          )}
          {warnCount > 0 && (
            <span className="flex items-center gap-1 text-xs font-medium text-amber-600 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full">
              ⚠ {warnCount} warn{warnCount !== 1 ? 's' : ''}
            </span>
          )}
          <span className="text-xs text-faint font-mono">{lines.length} lines</span>
          {!autoScroll && (
            <button
              onClick={() => {
                setAutoScroll(true)
                bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
              }}
              className="text-xs text-blue-600 hover:text-blue-700 font-medium transition-colors"
            >
              ↓ Resume
            </button>
          )}
        </div>
      </div>

      {/* Log lines */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto font-mono text-xs leading-relaxed p-3 space-y-0.5 bg-slate-50"
      >
        {lines.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 gap-3 text-faint">
            <span className="text-3xl">📋</span>
            <div className="text-center">
              <p className="font-medium text-subtle">Waiting for log stream</p>
              <p className="text-xs mt-1">Click a demo button in the top bar to start</p>
            </div>
          </div>
        ) : (
          lines.map(line => (
            <div
              key={line.id}
              className={cn(
                'px-2 py-0.5 rounded hover:bg-white/80 transition-colors flex items-start gap-2',
                logSeverityClass(line.severity),
              )}
            >
              <span className="shrink-0 w-4 text-center opacity-60">
                {SEV_ICON[line.severity.toUpperCase()] ?? '·'}
              </span>
              <span className="text-slate-400 shrink-0 tabular-nums">
                {line.timestamp.slice(11, 23)}
              </span>
              <span className="text-slate-500 shrink-0 font-medium">[{line.source}]</span>
              <span className="break-all">{line.message}</span>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
