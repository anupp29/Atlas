import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from '@/components/ui/Button'
import { cn } from '@/lib/utils'
import type { AtlasState } from '@/types/atlas'

const SECONDARY_TIMEOUT_MS = 30 * 60 * 1000 // 30 minutes — matches token expiry

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
    setLoading(true)
    setError(null)
    try {
      await onApprove(incident.thread_id, incident.incident_id, incident.client_id)
      if (needsDualApproval) {
        setFlowState('awaiting_secondary')
        // Fire timeout alert after 30 minutes — matches token expiry in approval_tokens.py
        secondaryTimerRef.current = setTimeout(() => {
          setSecondaryTimedOut(true)
        }, SECONDARY_TIMEOUT_MS)
      } else {
        setFlowState('executing')
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Approval failed')
    } finally {
      setLoading(false)
    }
  }

  // Clean up secondary timer on unmount
  useEffect(() => {
    return () => {
      if (secondaryTimerRef.current) clearTimeout(secondaryTimerRef.current)
    }
  }, [])

  const handleReject = async () => {
    if (rejectReason.length < 20) return
    setLoading(true)
    setError(null)
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
    setLoading(true)
    setError(null)
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
      {/* SLA breach warning */}
      {slaBreached && (
        <div className="rounded-md border border-red-800 bg-red-950/50 px-3 py-2 text-xs text-red-300">
          ⚠ SLA already breached — this incident requires post-incident review
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-md border border-red-800 bg-red-950/50 px-3 py-2 text-xs text-red-300">
          {error}
        </div>
      )}

      <AnimatePresence mode="wait">
        {/* ── Idle: show action buttons ─────────────────────────────────── */}
        {flowState === 'idle' && (
          <motion.div
            key="idle"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className={cn('grid gap-2', viewMode === 'L1' ? 'grid-cols-2' : 'grid-cols-3')}
          >
            <Button variant="approve" size="lg" loading={loading} onClick={handleApprove} className="w-full">
              Approve
            </Button>
            {viewMode === 'L1' ? (
              <Button variant="escalate" size="lg" onClick={() => setFlowState('done')} className="w-full">
                Escalate to L2
              </Button>
            ) : (
              <>
                <Button variant="modify" size="lg" onClick={() => setFlowState('modify')} className="w-full">
                  Modify
                </Button>
                <Button variant="reject" size="lg" onClick={() => setFlowState('reject')} className="w-full">
                  Reject
                </Button>
              </>
            )}
          </motion.div>
        )}

        {/* ── Awaiting secondary approval ───────────────────────────────── */}
        {flowState === 'awaiting_secondary' && (
          <motion.div
            key="secondary"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-lg border border-blue-800 bg-blue-950/30 p-4 space-y-2"
          >
            {secondaryTimedOut ? (
              <div className="rounded-md border border-red-800 bg-red-950/50 px-3 py-2 text-xs text-red-300">
                ⚠ Secondary approval token expired after 30 minutes — re-initiate approval or escalate to L3
              </div>
            ) : (
              <>
                <div className="flex items-center gap-2 text-sm text-blue-300 font-medium">
                  <span className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
                  Awaiting secondary approval
                </div>
                <p className="text-xs text-zinc-400">
                  ✓ Primary approval recorded — Slack notification sent to secondary approver
                </p>
                <p className="text-xs text-zinc-500">Token expires in 30 minutes</p>
              </>
            )}
          </motion.div>
        )}

        {/* ── Executing ─────────────────────────────────────────────────── */}
        {flowState === 'executing' && (
          <motion.div
            key="executing"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-lg border border-blue-800 bg-blue-950/30 p-4 space-y-2"
          >
            <div className="flex items-center gap-2 text-sm text-blue-300 font-medium">
              <span className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
              Executing: {incident.recommended_action_id}
            </div>
            <div className="h-1.5 rounded-full bg-elevated overflow-hidden">
              <motion.div
                className="h-full bg-blue-500 rounded-full"
                initial={{ width: '0%' }}
                animate={{ width: '100%' }}
                transition={{ duration: 8, ease: 'linear' }}
              />
            </div>
          </motion.div>
        )}

        {/* ── Modify panel ──────────────────────────────────────────────── */}
        {flowState === 'modify' && (
          <motion.div
            key="modify"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-lg border border-amber-800 bg-amber-950/20 p-4 space-y-3"
          >
            <h4 className="text-xs font-semibold uppercase tracking-widest text-amber-400">
              Modify Parameters
            </h4>
            <div className="space-y-2">
              <div className="flex items-center justify-between gap-3">
                <label className="text-xs text-zinc-400 font-mono">maxPoolSize</label>
                <input
                  type="number"
                  defaultValue={150}
                  onChange={e => setModifyParams(p => ({ ...p, maxPoolSize: e.target.value }))}
                  className="w-24 bg-elevated border border-border rounded px-2 py-1 text-xs font-mono text-white text-right focus:outline-none focus:border-amber-600"
                />
              </div>
              {modifyParams.maxPoolSize && modifyParams.maxPoolSize !== '150' && (
                <div className="text-xs text-amber-400 font-mono">
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

        {/* ── Reject panel ──────────────────────────────────────────────── */}
        {flowState === 'reject' && (
          <motion.div
            key="reject"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-lg border border-red-800 bg-red-950/20 p-4 space-y-3"
          >
            <h4 className="text-xs font-semibold uppercase tracking-widest text-red-400">
              Rejection Reason
            </h4>
            <textarea
              value={rejectReason}
              onChange={e => setRejectReason(e.target.value)}
              placeholder="Describe why this recommendation is incorrect (minimum 20 characters)"
              rows={3}
              className="w-full bg-elevated border border-border rounded px-3 py-2 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-red-600 resize-none"
            />
            <div className="flex items-center justify-between">
              <span className={cn('text-xs font-mono', rejectReason.length >= 20 ? 'text-green-400' : 'text-zinc-500')}>
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

        {/* ── Done ──────────────────────────────────────────────────────── */}
        {flowState === 'done' && (
          <motion.div
            key="done"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-xs text-zinc-500 text-center py-2"
          >
            Action submitted
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
