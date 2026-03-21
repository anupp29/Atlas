import { useEffect, useRef, useState } from 'react'
import { cn, logSeverityClass } from '@/lib/utils'
import type { LogLine } from '@/hooks/useIncident'

interface LogStreamProps {
  lines: LogLine[]
  clientId: string
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

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-2.5 border-b border-border flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-healthy animate-pulse-slow" />
          <span className="text-xs font-semibold uppercase tracking-widest text-zinc-500">
            Live Log Stream — {clientId.replace('_', ' ')}
          </span>
        </div>
        {!autoScroll && (
          <button
            onClick={() => {
              setAutoScroll(true)
              bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
            }}
            className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
          >
            ↓ Resume auto-scroll
          </button>
        )}
      </div>

      {/* Log lines */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto font-mono text-xs leading-relaxed p-3 space-y-0.5"
      >
        {lines.length === 0 ? (
          <div className="text-zinc-600 text-center py-8">
            Waiting for log stream…
          </div>
        ) : (
          lines.map(line => (
            <div
              key={line.id}
              className={cn(
                'px-2 py-0.5 rounded-sm hover:bg-elevated/30 transition-colors',
                logSeverityClass(line.severity),
              )}
            >
              <span className="text-zinc-600 mr-2 tabular-nums">{line.timestamp.slice(11, 23)}</span>
              <span className="text-zinc-500 mr-2">[{line.source}]</span>
              <span>{line.message}</span>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
