import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from '@/components/ui/Button'
import { cn } from '@/lib/utils'
import type { AtlasState } from '@/types/atlas'

const SECONDARY_TIMEOUT_MS = 30 * 60 * 1000

interface ApprovalFlowProps {
  incident: AtlasState
  viewMode: 'L1' | 'L2'
  onApprove: (threadId: string, incidentId: string, clientId: string) => Promise<void>
  onReject: (threadId: string, incidentId: string, clientId: string, reason: string) => Promise<void>
  onModify: (threadId: string, incidentId: string, clientId: string, params: Record<string, unknown>) => Promise<void>
}

type FlowState = 'idle' | 'awaiting_secondary' | 'executing' | 'done' | 'modify' | 'reject'

export function ApprovalFlow({ incident, viewMode, onApprove, onReject, onModify }: ApprovalFlowProps) {
  const [flowState, setFlowState] = useState<FlowState>('idle')
  const [rejectReason, setRejectReason] = useState('')
  const [modifyParams, setModifyParams] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [secondaryTimedOut, setSecondaryTimedOut] = useState(false)
  const secondaryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const needsDualApproval = incident.active_veto_conditions.some(v =>
    v.toLowerCase().includes('pci') || v.toLowerCase().includes('sox'),
  )
  const slaBreached = incident.sla_breach_time
    ? new Date(incident.sla_breach_time).getTime() < Date.now()
    : false

  const handleApprove = async () => {
    setLoading(true); setError(null)
    try {
      await onApprove(incident.thread_id, incident.incident_id, incident.client_id)
      if (needsDualApproval) {
        setFlowState('awaiting_secondary')
        secondaryTimerRef.current = setTimeout(() => setSecondaryTimedOut(true), SECONDARY_TIMEOUT_MS)
      } else {
        setFlowState('executing')
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Approval failed')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    return () => { if (secondaryTimerRef.current) clearTimeout(secondaryTimerRef.current) }
  }, [])

  const handleReject = async () => {
    if (rejectReason.length < 20) return
    setLoading(true); setError(null)
    try {
      await onReject(incident.thread_id, incident.incident_id, incident.client_id, rejectReason)
      setFlowState('done')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Rejection failed')
    } finally {
      setLoading(false)
    }
  }

  const handleModify = async () => {
    setLoading(true); setError(null)
    try {
      await onModify(incident.thread_id, incident.incident_id, incident.client_id, modifyParams)
      setFlowState('executing')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Modification failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-3">
      {slaBreached && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700 font-medium">
          ⚠ SLA already breached — post-incident review required
        </div>
      )}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          {error}
        </div>
      )}

      <AnimatePresence mode="wait">
        {flowState === 'idle' && (
          <motion.div
            key="idle"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className={cn('grid gap-2', viewMode === 'L1' ? 'grid-cols-2' : 'grid-cols-3')}
          >
            <Button variant="approve" size="lg" loading={loading} onClick={handleApprove} className="w-full">
              ✓ Approve
            </Button>
            {viewMode === 'L1' ? (
              <Button variant="escalate" size="lg" onClick={() => setFlowState('done')} className="w-full">
                ↑ Escalate to L2
              </Button>
            ) : (
              <>
                <Button variant="modify" size="lg" onClick={() => setFlowState('modify')} className="w-full">
                  ✎ Modify
                </Button>
                <Button variant="reject" size="lg" onClick={() => setFlowState('reject')} className="w-full">
                  ✕ Reject
                </Button>
              </>
            )}
          </motion.div>
        )}

        {flowState === 'awaiting_secondary' && (
          <motion.div
            key="secondary"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-xl border border-blue-200 bg-blue-50 p-4 space-y-2"
          >
            {secondaryTimedOut ? (
              <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                ⚠ Secondary approval token expired — re-initiate or escalate to L3
              </div>
            ) : (
              <>
                <div className="flex items-center gap-2 text-sm text-blue-700 font-semibold">
                  <span className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
                  Awaiting secondary approval
                </div>
                <p className="text-xs text-blue-600">✓ Primary approval recorded — Slack notification sent</p>
                <p className="text-xs text-blue-400">Token expires in 30 minutes</p>
              </>
            )}
          </motion.div>
        )}

        {flowState === 'executing' && (
          <motion.div
            key="executing"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-xl border border-blue-200 bg-blue-50 p-4 space-y-3"
          >
            <div className="flex items-center gap-2 text-sm text-blue-700 font-semibold">
              <span className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
              Executing: {incident.recommended_action_id}
            </div>
            <div className="h-2 rounded-full bg-blue-100 overflow-hidden">
              <motion.div
                className="h-full bg-blue-500 rounded-full"
                initial={{ width: '0%' }}
                animate={{ width: '100%' }}
                transition={{ duration: 8, ease: 'linear' }}
              />
            </div>
          </motion.div>
        )}

        {flowState === 'modify' && (
          <motion.div
            key="modify"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-xl border border-amber-200 bg-amber-50 p-4 space-y-3"
          >
            <h4 className="text-xs font-semibold uppercase tracking-widest text-amber-700">
              Modify Parameters
            </h4>
            <div className="space-y-2">
              <div className="flex items-center justify-between gap-3">
                <label className="text-xs text-subtle font-mono">maxPoolSize</label>
                <input
                  type="number"
                  defaultValue={150}
                  onChange={e => setModifyParams(p => ({ ...p, maxPoolSize: e.target.value }))}
                  className="w-24 bg-white border border-amber-200 rounded-lg px-2 py-1.5 text-xs font-mono text-ink text-right focus:outline-none focus:ring-2 focus:ring-amber-300"
                />
              </div>
              {modifyParams.maxPoolSize && modifyParams.maxPoolSize !== '150' && (
                <div className="text-xs text-amber-700 font-mono bg-amber-100 rounded px-2 py-1">
                  Diff: maxPoolSize 150 → {modifyParams.maxPoolSize}
                </div>
              )}
            </div>
            <div className="flex gap-2">
              <Button variant="modify" size="sm" loading={loading} onClick={handleModify}>
                Submit Modification
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setFlowState('idle')}>
                Cancel
              </Button>
            </div>
          </motion.div>
        )}

        {flowState === 'reject' && (
          <motion.div
            key="reject"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-xl border border-red-200 bg-red-50 p-4 space-y-3"
          >
            <h4 className="text-xs font-semibold uppercase tracking-widest text-red-700">
              Rejection Reason
            </h4>
            <textarea
              value={rejectReason}
              onChange={e => setRejectReason(e.target.value)}
              placeholder="Describe why this recommendation is incorrect (minimum 20 characters)"
              rows={3}
              className="w-full bg-white border border-red-200 rounded-lg px-3 py-2 text-xs text-ink placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-red-300 resize-none"
            />
            <div className="flex items-center justify-between">
              <span className={cn('text-xs font-mono', rejectReason.length >= 20 ? 'text-emerald-600' : 'text-faint')}>
                {rejectReason.length}/20 minimum
              </span>
              <div className="flex gap-2">
                <Button
                  variant="reject"
                  size="sm"
                  loading={loading}
                  disabled={rejectReason.length < 20}
                  onClick={handleReject}
                >
                  Submit Rejection
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setFlowState('idle')}>
                  Cancel
                </Button>
              </div>
            </div>
          </motion.div>
        )}

        {flowState === 'done' && (
          <motion.div
            key="done"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-xs text-emerald-700 text-center py-3 font-medium bg-emerald-50 rounded-xl border border-emerald-200"
          >
            ✓ Action submitted successfully
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
