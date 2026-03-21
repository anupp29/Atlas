import { useState, useCallback } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { TopBar } from '@/components/TopBar'
import { ClientRoster } from '@/components/ClientRoster'
import { ActivityFeed } from '@/components/ActivityFeed'
import { LogStream } from '@/components/LogStream'
import { BriefingCard } from '@/components/BriefingCard'
import { L1Interface } from '@/components/L1Interface'
import { PostResolution } from '@/components/PostResolution'
import { useIncident } from '@/hooks/useIncident'
import type { ClientHealth } from '@/types/atlas'

type ViewMode = 'L1' | 'L2'

export default function App() {
  const [selectedClientId, setSelectedClientId] = useState('FINCORE_UK_001')
  const [viewMode, setViewMode] = useState<ViewMode>('L2')

  const {
    incident,
    isActive,
    activityFeed,
    logLines,
    incidentStatus,
    activityStatus,
  } = useIncident(selectedClientId)

  const isResolved = incident?.execution_status === 'resolved' || incident?.resolution_outcome === 'success'

  // ── API actions ────────────────────────────────────────────────────────────
  const handleApprove = useCallback(async (threadId: string, incidentId: string, clientId: string) => {
    const res = await fetch('/api/incidents/approve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ thread_id: threadId, incident_id: incidentId, client_id: clientId, approver: 'engineer@atos.com' }),
    })
    if (!res.ok) throw new Error(`Approval failed: ${res.status}`)
  }, [])

  const handleReject = useCallback(async (threadId: string, incidentId: string, clientId: string, reason: string) => {
    const res = await fetch('/api/incidents/reject', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ thread_id: threadId, incident_id: incidentId, client_id: clientId, rejector: 'engineer@atos.com', reason }),
    })
    if (!res.ok) throw new Error(`Rejection failed: ${res.status}`)
  }, [])

  const handleModify = useCallback(async (threadId: string, incidentId: string, clientId: string, params: Record<string, unknown>) => {
    const res = await fetch('/api/incidents/modify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ thread_id: threadId, incident_id: incidentId, client_id: clientId, modifier: 'engineer@atos.com', modified_parameters: params }),
    })
    if (!res.ok) throw new Error(`Modification failed: ${res.status}`)
  }, [])

  // Derive health statuses and incident counts from active incident
  const healthStatuses: Record<string, ClientHealth['health_status']> = {
    [selectedClientId]: isActive ? 'incident' : 'healthy',
  }
  const incidentCounts: Record<string, number> = {
    [selectedClientId]: isActive ? 1 : 0,
  }

  return (
    <div className="flex flex-col h-screen bg-canvas text-white overflow-hidden">
      <TopBar incidentStatus={incidentStatus} activityStatus={activityStatus} />

      <div className="flex flex-1 overflow-hidden">
        {/* Left panel */}
        <ClientRoster
          selectedClientId={selectedClientId}
          onSelectClient={setSelectedClientId}
          incidentCounts={incidentCounts}
          healthStatuses={healthStatuses}
        />

        {/* Centre panel */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* View mode toggle — only shown when incident is active */}
          {isActive && !isResolved && (
            <div className="flex items-center justify-end px-4 py-2 border-b border-border shrink-0 bg-canvas">
              <div className="flex rounded-md border border-border overflow-hidden text-xs">
                {(['L1', 'L2'] as ViewMode[]).map(mode => (
                  <button
                    key={mode}
                    onClick={() => setViewMode(mode)}
                    className={`px-3 py-1.5 transition-colors ${
                      viewMode === mode
                        ? 'bg-blue-600 text-white'
                        : 'bg-surface text-zinc-400 hover:text-zinc-200'
                    }`}
                  >
                    {mode} View
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="flex-1 overflow-y-auto">
            <AnimatePresence mode="wait">
              {/* Post-resolution */}
              {isResolved && incident ? (
                <motion.div
                  key="resolved"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.3 }}
                  className="p-4"
                >
                  <PostResolution incident={incident} />
                </motion.div>
              ) : isActive && incident ? (
                /* Active incident */
                <motion.div
                  key="incident"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.3 }}
                  className="p-4"
                >
                  {viewMode === 'L1' ? (
                    <L1Interface
                      incident={incident}
                      onApprove={handleApprove}
                      onEscalate={() => setViewMode('L2')}
                    />
                  ) : (
                    <BriefingCard
                      incident={incident}
                      viewMode={viewMode}
                      onApprove={handleApprove}
                      onReject={handleReject}
                      onModify={handleModify}
                    />
                  )}
                </motion.div>
              ) : (
                /* Normal mode — log stream */
                <motion.div
                  key="logs"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.3 }}
                  className="h-full"
                >
                  <LogStream lines={logLines} clientId={selectedClientId} />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </main>

        {/* Right panel */}
        <ActivityFeed entries={activityFeed} status={activityStatus} />
      </div>
    </div>
  )
}
