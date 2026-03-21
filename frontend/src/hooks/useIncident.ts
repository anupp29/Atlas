import { useCallback, useEffect, useRef, useState } from 'react'
import type { AtlasState, ActivityEntry, WSMessage, ConnectionStatus } from '@/types/atlas'
import { useWebSocket } from './useWebSocket'

const MAX_ACTIVITY_ENTRIES = 100

interface UseIncidentReturn {
  incident: AtlasState | null
  isActive: boolean
  activityFeed: ActivityEntry[]
  logLines: LogLine[]
  incidentStatus: ConnectionStatus
  activityStatus: ConnectionStatus
  logStatus: ConnectionStatus
}

export interface LogLine {
  id: string
  timestamp: string
  severity: string
  source: string
  message: string
  raw: string
}

let _entryCounter = 0
function nextId(): string {
  return `entry-${++_entryCounter}`
}

/**
 * Aggregates all three WebSocket streams for a given client into a single
 * coherent state object. Components read from this hook only — no raw WS calls.
 */
export function useIncident(clientId: string): UseIncidentReturn {
  const [incident, setIncident] = useState<AtlasState | null>(null)
  const [activityFeed, setActivityFeed] = useState<ActivityEntry[]>([])
  const [logLines, setLogLines] = useState<LogLine[]>([])

  // ── Incident WebSocket ────────────────────────────────────────────────────
  const handleIncidentMessage = useCallback((msg: WSMessage) => {
    if (msg.type === 'active_incidents') {
      const relevant = msg.incidents.find(i => i.client_id === clientId)
      if (relevant) setIncident(relevant)
    } else if (msg.type === 'new_incident' && msg.client_id === clientId) {
      // Fetch full state via REST to hydrate the incident
      fetch(`/api/incidents/active?client_id=${clientId}`)
        .then(r => r.json())
        .then((data: { incidents: AtlasState[] }) => {
          const found = data.incidents.find(i => i.thread_id === msg.thread_id)
          if (found) setIncident(found)
        })
        .catch(() => {/* non-fatal */})
    } else if (msg.type === 'incident_approved') {
      setIncident(prev =>
        prev ? { ...prev, execution_status: msg.execution_status } : prev,
      )
    }
  }, [clientId])

  const { status: incidentStatus } = useWebSocket(
    `/ws/incidents/${clientId}`,
    { onMessage: handleIncidentMessage },
  )

  // ── Activity WebSocket ────────────────────────────────────────────────────
  const handleActivityMessage = useCallback((msg: WSMessage) => {
    if (
      msg.type === 'agent_detection' ||
      msg.type === 'orchestrator_node' ||
      msg.type === 'human_action' ||
      msg.type === 'veto_fired' ||
      msg.type === 'resolution' ||
      msg.type === 'early_warning' ||
      msg.type === 'execution' ||
      msg.type === 'cmdb_change' ||
      msg.type === 'incident_created'
    ) {
      const base = msg as ActivityEntry
      const entry: ActivityEntry = {
        ...base,
        id: base.id ?? nextId(),
      }
      setActivityFeed(prev => [entry, ...prev].slice(0, MAX_ACTIVITY_ENTRIES))
    }
  }, [])

  const { status: activityStatus } = useWebSocket(
    '/ws/activity',
    { onMessage: handleActivityMessage },
  )

  // ── Log WebSocket ─────────────────────────────────────────────────────────
  const handleLogMessage = useCallback((msg: WSMessage) => {
    if (msg.type === 'log_line' && msg.client_id === clientId) {
      const line: LogLine = {
        id: nextId(),
        timestamp: msg.timestamp,
        severity: msg.severity,
        source: msg.source,
        message: msg.line,
        raw: msg.line,
      }
      setLogLines(prev => [...prev.slice(-499), line])
    }
  }, [clientId])

  const { status: logStatus } = useWebSocket(
    `/ws/logs/${clientId}`,
    { onMessage: handleLogMessage },
  )

  // ── Poll active incidents on mount ────────────────────────────────────────
  const hasFetchedRef = useRef(false)
  useEffect(() => {
    if (hasFetchedRef.current) return
    hasFetchedRef.current = true
    fetch(`/api/incidents/active?client_id=${clientId}`)
      .then(r => r.json())
      .then((data: { incidents: AtlasState[] }) => {
        if (data.incidents.length > 0) {
          setIncident(data.incidents[0])
        }
      })
      .catch(() => {/* non-fatal */})
  }, [clientId])

  return {
    incident,
    isActive: incident !== null && incident.execution_status !== 'resolved',
    activityFeed,
    logLines,
    incidentStatus,
    activityStatus,
    logStatus,
  }
}
