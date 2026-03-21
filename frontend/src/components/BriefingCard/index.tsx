import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Card, CardBody, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { SLATimer } from '@/components/SLATimer'
import { GraphViz } from '@/components/GraphViz'
import { SHAPChart } from '@/components/SHAPChart'
import { EarlyWarning } from '@/components/EarlyWarning'
import { ApprovalFlow } from '@/components/ApprovalFlow'
import { cn, relativeTime, exactTime, priorityClass, actionClassBadge } from '@/lib/utils'
import type { AtlasState } from '@/types/atlas'

interface BriefingCardProps {
  incident: AtlasState
  viewMode: 'L1' | 'L2'
  onApprove: (threadId: string, incidentId: string, clientId: string) => Promise<void>
  onReject: (threadId: string, incidentId: string, clientId: string, reason: string) => Promise<void>
  onModify: (threadId: string, incidentId: string, clientId: string, params: Record<string, unknown>) => Promise<void>
}

export function BriefingCard({ incident, viewMode, onApprove, onReject, onModify }: BriefingCardProps) {
  const [hypothesesOpen, setHypothesesOpen] = useState(false)

  const topEvidence = incident.evidence_packages[0]
  const shapValues = topEvidence?.shap_feature_values ?? {}
  const topDeploy = incident.recent_deployments[0]
  const topMatch = incident.semantic_matches[0] ?? incident.historical_graph_matches[0]
  const priority = incident.incident_priority ?? 'P2'
  // Derive action class from playbook ID: pool/cache/config = Class 1, redeploy/scale = Class 2
  const actionClass = (() => {
    const id = incident.recommended_action_id ?? ''
    if (id.includes('redeploy') || id.includes('scale') || id.includes('infra')) return 2
    return 1
  })()
  const { label: classLabel } = actionClassBadge(actionClass)

  return (
    <div className="space-y-3 animate-fade-in">
      {/* ── Incident banner ─────────────────────────────────────────────── */}
      <div className="rounded-lg border border-red-900 bg-[#1F0A0A] px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="w-2 h-2 rounded-full bg-incident animate-pulse" />
          <span className="text-sm font-semibold text-white">
            INCIDENT ACTIVE
          </span>
          <span className="font-mono text-sm text-red-300">
            {incident.servicenow_ticket_id || incident.incident_id}
          </span>
          <Badge className={priorityClass(priority)}>{priority}</Badge>
        </div>
        <div className="flex items-center gap-4 text-xs text-zinc-400">
          <span>
            Confidence:{' '}
            <span className="font-mono text-white font-semibold">
              {incident.composite_confidence_score?.toFixed(2) ?? '—'}
            </span>
          </span>
          <span className={cn(
            'px-2 py-0.5 rounded text-xs font-medium',
            incident.routing_decision === 'AUTO_EXECUTE' ? 'bg-green-950 text-green-300' :
            incident.routing_decision === 'L1_HUMAN_REVIEW' ? 'bg-blue-950 text-blue-300' :
            'bg-amber-950 text-amber-300',
          )}>
            {incident.routing_decision?.replace(/_/g, ' ') ?? 'ROUTING…'}
          </span>
        </div>
      </div>

      {/* ── Section 1: Situation Summary ────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>Situation Summary</CardTitle>
          {incident.sla_breach_time && (
            <SLATimer
              slaBreachTime={incident.sla_breach_time}
              ticketId={incident.servicenow_ticket_id}
            />
          )}
        </CardHeader>
        <CardBody className="space-y-3">
          <div>
            <span className="text-xs text-zinc-500 block mb-1">Affected Services</span>
            <div className="flex flex-wrap gap-1.5">
              {incident.blast_radius.slice(0, 5).map(svc => (
                <span
                  key={svc.name}
                  className={cn(
                    'px-2 py-0.5 rounded text-xs font-mono border',
                    svc.criticality === 'P1' ? 'border-red-800 text-red-300 bg-red-950/30' :
                    svc.criticality === 'P2' ? 'border-orange-800 text-orange-300 bg-orange-950/30' :
                    'border-amber-800 text-amber-300 bg-amber-950/30',
                  )}
                >
                  {svc.name} ({svc.criticality})
                </span>
              ))}
            </div>
          </div>
          {incident.situation_summary && (
            <p className="text-sm text-zinc-300 leading-relaxed">{incident.situation_summary}</p>
          )}
          {topEvidence && (
            <p className="text-sm text-zinc-300 leading-relaxed">
              {topEvidence.preliminary_hypothesis}
            </p>
          )}
        </CardBody>
      </Card>

      {/* ── SHAP Chart ──────────────────────────────────────────────────── */}
      {Object.keys(shapValues).length > 0 && (
        <Card>
          <CardBody>
            <SHAPChart shapValues={shapValues} />
          </CardBody>
        </Card>
      )}

      {/* ── Section 2: Blast Radius ─────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>Blast Radius — Dependency Graph</CardTitle>
          <span className="text-xs text-zinc-500">
            {incident.correlation_type?.replace('_', ' ')}
          </span>
        </CardHeader>
        <CardBody className="space-y-3">
          <GraphViz incident={incident} />
          <div className="space-y-1.5 mt-2">
            {incident.blast_radius.map((svc, i) => {
              const earlyWarn = incident.early_warning_signals?.find(s => s.service_name === svc.name)
              return (
                <div key={svc.name} className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className={cn(
                      'w-1.5 h-1.5 rounded-full',
                      i === 0 ? 'bg-incident' : i === 1 ? 'bg-orange-500' : 'bg-warning',
                    )} />
                    <span className="text-zinc-300 font-medium">{svc.name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className={priorityClass(svc.criticality)}>{svc.criticality}</Badge>
                    {earlyWarn && (
                      <span className="text-amber-400 font-mono text-xs">
                        ⚠ {earlyWarn.deviation_sigma.toFixed(1)}σ
                      </span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </CardBody>
      </Card>

      {/* ── Section 3: Deployment Correlation ──────────────────────────── */}
      <Card glow={topDeploy ? 'amber' : 'none'}>
        <CardHeader>
          <CardTitle>Deployment Correlation</CardTitle>
        </CardHeader>
        <CardBody>
          {topDeploy ? (
            <div className="space-y-2 text-sm">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <span className="text-xs text-zinc-500 block mb-0.5">Change ID</span>
                  <span className="font-mono text-warning font-semibold text-base">
                    {topDeploy.change_id}
                  </span>
                </div>
                <Badge className={cn(
                  'text-xs',
                  topDeploy.cab_risk_rating === 'LOW' ? 'bg-green-950 text-green-300 border border-green-800' :
                  topDeploy.cab_risk_rating === 'HIGH' ? 'bg-red-950 text-red-300 border border-red-800' :
                  'bg-amber-950 text-amber-300 border border-amber-800',
                )}>
                  {topDeploy.cab_risk_rating}
                </Badge>
              </div>
              <div>
                <span className="text-xs text-zinc-500 block mb-0.5">Description</span>
                <span className="text-zinc-300">{topDeploy.change_description}</span>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <span className="text-xs text-zinc-500 block mb-0.5">Deployed by</span>
                  <span className="text-zinc-300 font-mono text-xs">{topDeploy.deployed_by}</span>
                </div>
                <div>
                  <span className="text-xs text-zinc-500 block mb-0.5">Timestamp</span>
                  <span
                    className="text-zinc-300 text-xs cursor-default"
                    title={exactTime(topDeploy.timestamp)}
                  >
                    {relativeTime(topDeploy.timestamp)}
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-xs text-zinc-500">No recent deployments found in last 7 days</p>
          )}
        </CardBody>
      </Card>

      {/* ── Section 4: Historical Match ─────────────────────────────────── */}
      <Card glow={topMatch ? 'green' : 'none'}>
        <CardHeader>
          <CardTitle>Historical Match</CardTitle>
        </CardHeader>
        <CardBody>
          {topMatch ? (
            <div className="space-y-3">
              <div className="flex items-start gap-4">
                {/* Similarity badge */}
                <div className="flex flex-col items-center justify-center w-16 h-16 rounded-lg bg-green-950 border border-green-800 shrink-0">
                  <span className="font-mono text-xl font-bold text-healthy leading-none">
                    {Math.round((topMatch.similarity_score ?? 0) * 100)}%
                  </span>
                  <span className="text-xs text-green-600 mt-0.5">MATCH</span>
                </div>
                <div className="space-y-1 text-sm">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-zinc-300 font-medium">{topMatch.incident_id}</span>
                    {topMatch.double_confirmed && (
                      <Badge className="bg-green-950 text-green-300 border border-green-800">
                        ✓ Double-confirmed
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-zinc-400">{topMatch.root_cause}</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <span className="text-zinc-500 block mb-0.5">Resolution</span>
                  <span className="text-zinc-300">{topMatch.resolution}</span>
                </div>
                <div>
                  <span className="text-zinc-500 block mb-0.5">MTTR</span>
                  <span className="font-mono text-zinc-300">{topMatch.mttr_minutes} min</span>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-xs text-zinc-500">No historical precedent found — cold-start veto active</p>
          )}
        </CardBody>
      </Card>

      {/* ── Section 5: Alternative Hypotheses ──────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>Alternative Hypotheses</CardTitle>
          <button
            onClick={() => setHypothesesOpen(o => !o)}
            className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            {hypothesesOpen ? '▲ Collapse' : '▼ Expand'}
          </button>
        </CardHeader>
        <AnimatePresence>
          {hypothesesOpen && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25 }}
              className="overflow-hidden"
            >
              <CardBody className="space-y-3">
                {incident.alternative_hypotheses.length === 0 ? (
                  <p className="text-xs text-zinc-500">No alternative hypotheses available</p>
                ) : (
                  incident.alternative_hypotheses.map((h, i) => (
                    <div key={i} className="border border-border rounded-md p-3 space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-zinc-200">{h.hypothesis}</span>
                        <span className="font-mono text-xs text-zinc-400">
                          {Math.round(h.confidence * 100)}%
                        </span>
                      </div>
                      {h.evidence_for && (
                        <p className="text-xs text-green-400">✓ {h.evidence_for}</p>
                      )}
                      {h.evidence_against && (
                        <p className="text-xs text-red-400">✗ {h.evidence_against}</p>
                      )}
                    </div>
                  ))
                )}
              </CardBody>
            </motion.div>
          )}
        </AnimatePresence>
      </Card>

      {/* ── Section 6: Recommended Action ──────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>Recommended Action</CardTitle>
          <Badge className={actionClassBadge(actionClass).className}>{classLabel}</Badge>
        </CardHeader>
        <CardBody className="space-y-2 text-sm">
          <div className="flex items-center gap-2">
            <span className="font-mono text-blue-300 font-medium">
              {incident.recommended_action_id || '—'}
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs text-zinc-400">
            <span className="text-green-400">✓ Auto-rollback available</span>
          </div>
        </CardBody>
      </Card>

      {/* ── Veto panel ──────────────────────────────────────────────────── */}
      {incident.active_veto_conditions.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-lg border border-red-900 bg-[#1F0A0A] p-4"
        >
          <div className="flex items-center gap-2 mb-2">
            <span className="text-red-400 text-sm">⛔</span>
            <h4 className="text-xs font-semibold uppercase tracking-widest text-red-400">
              Active Veto Conditions — Auto-Execute Blocked
            </h4>
          </div>
          <div className="space-y-1.5">
            {incident.active_veto_conditions.map((veto, i) => (
              <p key={i} className="text-xs text-red-300 leading-relaxed">{veto}</p>
            ))}
          </div>
        </motion.div>
      )}

      {/* ── Early Warning ───────────────────────────────────────────────── */}
      {incident.early_warning_signals?.length > 0 && (
        <EarlyWarning signals={incident.early_warning_signals} />
      )}

      {/* ── Approval Flow ───────────────────────────────────────────────── */}
      <Card>
        <CardBody>
          <ApprovalFlow
            incident={incident}
            viewMode={viewMode}
            onApprove={onApprove}
            onReject={onReject}
            onModify={onModify}
          />
        </CardBody>
      </Card>
    </div>
  )
}
