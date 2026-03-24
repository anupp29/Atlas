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
import { useDemoTrigger } from '@/hooks/useDemoTrigger'
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

  const { demoRunning, triggerDemo } = useDemoTrigger(setSelectedClientId)

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

  const healthStatuses: Record<string, ClientHealth['health_status']> = {
    [selectedClientId]: isActive ? 'incident' : 'healthy',
  }
  const incidentCounts: Record<string, number> = {
    [selectedClientId]: isActive ? 1 : 0,
  }

  return (
    <div className="flex flex-col h-screen bg-canvas text-ink overflow-hidden">
      <TopBar
        incidentStatus={incidentStatus}
        activityStatus={activityStatus}
        onTriggerDemo={triggerDemo}
        demoRunning={demoRunning}
      />

      <div className="flex flex-1 overflow-hidden">
        {/* Left panel */}
        <ClientRoster
          selectedClientId={selectedClientId}
          onSelectClient={setSelectedClientId}
          incidentCounts={incidentCounts}
          healthStatuses={healthStatuses}
        />

        {/* Centre panel */}
        <main className="flex-1 flex flex-col overflow-hidden bg-canvas">
          {/* View mode toggle */}
          {isActive && !isResolved && (
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-border shrink-0 bg-white">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                <span className="text-xs font-semibold text-red-700">Incident Active</span>
                <span className="text-xs text-faint font-mono">{incident?.incident_id}</span>
              </div>
              <div className="flex rounded-lg border border-border overflow-hidden text-xs shadow-sm">
                {(['L1', 'L2'] as ViewMode[]).map(mode => (
                  <button
                    key={mode}
                    onClick={() => setViewMode(mode)}
                    className={`px-4 py-1.5 font-medium transition-colors ${
                      viewMode === mode
                        ? 'bg-blue-600 text-white'
                        : 'bg-white text-subtle hover:text-ink hover:bg-slate-50'
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
              {isResolved && incident ? (
                <motion.div
                  key="resolved"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.3 }}
                  className="p-5"
                >
                  <PostResolution incident={incident} />
                </motion.div>
              ) : isActive && incident ? (
                <motion.div
                  key="incident"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.3 }}
                  className="p-5"
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
