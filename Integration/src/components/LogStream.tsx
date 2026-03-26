import React, { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { LogEntry } from '../store/connectionStore'
import { formatTime, getLogLevelColor, getLogLevelBgColor } from '../utils/helpers'

interface LogStreamProps {
  logs: LogEntry[]
}

export default function LogStream({ logs }: LogStreamProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0
    }
  }, [logs])

  return (
    <div
      ref={scrollRef}
      className="h-96 overflow-y-auto bg-slate-800/50 p-4 space-y-2 font-mono text-sm"
    >
      <AnimatePresence>
        {logs.length === 0 ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center py-12 text-slate-500"
          >
            <p>Waiting for logs...</p>
          </motion.div>
        ) : (
          logs.map((log, index) => (
            <motion.div
              key={log.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              transition={{ duration: 0.3 }}
              className={`p-2 rounded border-l-2 ${getLogLevelBgColor(log.level)} border-l-${
                log.level === 'error'
                  ? 'red'
                  : log.level === 'warning'
                    ? 'yellow'
                    : log.level === 'info'
                      ? 'blue'
                      : 'gray'
              }-500`}
            >
              <div className="flex items-start gap-3">
                <span className="text-slate-500 flex-shrink-0 w-20">
                  {formatTime(log.timestamp)}
                </span>
                <span
                  className={`font-semibold flex-shrink-0 w-16 uppercase text-xs ${getLogLevelColor(
                    log.level
                  )}`}
                >
                  {log.level}
                </span>
                <span className="text-slate-300 flex-1 break-words">{log.message}</span>
              </div>
            </motion.div>
          ))
        )}
      </AnimatePresence>
    </div>
  )
}
