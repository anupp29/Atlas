import { useCallback, useEffect, useRef, useState } from 'react'
import type { ConnectionStatus, WSMessage } from '@/types/atlas'

const BASE_WS_URL = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000'

const MAX_RETRIES = 10
const BASE_DELAY_MS = 1000
const MAX_DELAY_MS = 30_000

interface UseWebSocketOptions {
  onMessage: (msg: WSMessage) => void
  enabled?: boolean
}

interface UseWebSocketReturn {
  status: ConnectionStatus
  send: (data: unknown) => void
}

/**
 * Manages a single WebSocket connection with exponential-backoff reconnect.
 * Per STRUCTURE.md: per-client isolation, min 1s between retries, max 10 retries,
 * then shows "disconnected" — never silently shows stale data.
 */
export function useWebSocket(
  path: string,
  { onMessage, enabled = true }: UseWebSocketOptions,
): UseWebSocketReturn {
  const [status, setStatus] = useState<ConnectionStatus>('reconnecting')
  const wsRef = useRef<WebSocket | null>(null)
  const retriesRef = useRef(0)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage

  const connect = useCallback(() => {
    if (!enabled) return
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const url = `${BASE_WS_URL}${path}`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      retriesRef.current = 0
      setStatus('connected')
    }

    ws.onmessage = (event: MessageEvent<string>) => {
      try {
        const msg = JSON.parse(event.data) as WSMessage
        if (msg.type === 'ping') return
        onMessageRef.current(msg)
      } catch {
        // Malformed message — skip, never crash
      }
    }

    ws.onclose = () => {
      wsRef.current = null
      if (!enabled) return
      if (retriesRef.current >= MAX_RETRIES) {
        setStatus('disconnected')
        return
      }
      setStatus('reconnecting')
      const delay = Math.min(BASE_DELAY_MS * 2 ** retriesRef.current, MAX_DELAY_MS)
      retriesRef.current += 1
      timerRef.current = setTimeout(connect, delay)
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [path, enabled])

  useEffect(() => {
    if (enabled) {
      connect()
    }
    return () => {
      timerRef.current && clearTimeout(timerRef.current)
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [connect, enabled])

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  return { status, send }
}
