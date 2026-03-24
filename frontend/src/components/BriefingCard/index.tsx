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
  const actionClass = (() => {
    const id = incident.recommended_action_id ?? ''
    if (id.includes('redeploy') || id.includes('scale') || id.includes('infra')) return 2
    return 1
  })()
  const { label: classLabel } = actionClassBadge(actionClass)

  const routingConfig = {
    AUTO_EXECUTE:      { bg: 'bg-emerald-50 border-emerald-200 text-emerald-700', label: 'AUTO EXECUTE' },
    L1_HUMAN_REVIEW:   { bg: 'bg-blue-50 border-blue-200 text-blue-700',          label: 'L1 HUMAN REVIEW' },
    L2_L3_ESCALATION:  { bg: 'bg-amber-50 border-amber-200 text-amber-700',       label: 'L2/L3 ESCALATION' },
    '':                { bg: 'bg-slate-100 border-slate-200 text-subtle',          label: 'ROUTING…' },
  }[incident.routing_decision ?? ''] ?? { bg: 'bg-slate-100 border-slate-200 text-subtle', label: incident.routing_decision }

  return (
    <div className="space-y-3 animate-fade-in max-w-3xl mx-auto">

      {/* ── Incident banner ─────────────────────────────────────────────── */}
      <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-3">
          <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse" />
          <span className="text-sm font-bold text-red-800">INCIDENT ACTIVE</span>
          <span className="font-mono text-sm text-red-600 font-semibold">
            {incident.servicenow_ticket_id || incident.incident_id}
          </span>
          <Badge className={priorityClass(priority)}>{priority}</Badge>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <span className="text-subtle">
            Confidence:{' '}
            <span className="font-mono text-ink font-bold text-sm">
              {incident.composite_confidence_score?.toFixed(2) ?? '—'}
            </span>
          </span>
          <span className={cn('px-2.5 py-1 rounded-full text-xs font-semibold border', routingConfig.bg)}>
            {routingConfig.label}
          </span>
        </div>
      </div>

      {/* ── Situation Summary ───────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>Situation Summary</CardTitle>
          {incident.sla_breach_time && (
            <SLATimer slaBreachTime={incident.sla_breach_time} ticketId={incident.servicenow_ticket_id} />
          )}
        </CardHeader>
        <CardBody className="space-y-3">
          <div>
            <span className="text-xs text-faint block mb-1.5 font-medium">Affected Services</span>
            <div className="flex flex-wrap gap-1.5">
              {incident.blast_radius.slice(0, 5).map(svc => (
                <span
                  key={svc.name}
                  className={cn(
                    'px-2.5 py-1 rounded-lg text-xs font-mono font-medium border',
                    svc.criticality === 'P1' ? 'border-red-200 text-red-700 bg-red-50' :
                    svc.criticality === 'P2' ? 'border-orange-200 text-orange-700 bg-orange-50' :
                    'border-amber-200 text-amber-700 bg-amber-50',
                  )}
                >
                  {svc.name} <span className="opacity-60">({svc.criticality})</span>
                </span>
              ))}
            </div>
          </div>
          {(incident.situation_summary || topEvidence?.preliminary_hypothesis) && (
            <p className="text-sm text-ink leading-relaxed bg-slate-50 rounded-lg p-3 border border-border">
              {incident.situation_summary ?? topEvidence?.preliminary_hypothesis}
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

      {/* ── Blast Radius ────────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>Blast Radius — Dependency Graph</CardTitle>
          <span className="text-xs text-faint font-medium">
            {incident.correlation_type?.replace('_', ' ')}
          </span>
        </CardHeader>
        <CardBody className="space-y-3">
          <GraphViz incident={incident} />
          <div className="space-y-1.5 mt-1">
            {incident.blast_radius.map((svc, i) => {
              const earlyWarn = incident.early_warning_signals?.find(s => s.service_name === svc.name)
              return (
                <div key={svc.name} className="flex items-center justify-between text-xs py-1.5 px-3 rounded-lg bg-slate-50 border border-border">
                  <div className="flex items-center gap-2">
                    <span className={cn(
                      'w-2 h-2 rounded-full',
                      i === 0 ? 'bg-red-500' : i === 1 ? 'bg-orange-500' : 'bg-amber-400',
                    )} />
                    <span className="text-ink font-medium">{svc.name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className={priorityClass(svc.criticality)}>{svc.criticality}</Badge>
                    {earlyWarn && (
                      <span className="text-amber-600 font-mono font-semibold">
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

      {/* ── Deployment Correlation ──────────────────────────────────────── */}
      <Card glow={topDeploy ? 'amber' : 'none'}>
        <CardHeader>
          <CardTitle>Deployment Correlation</CardTitle>
        </CardHeader>
        <CardBody>
          {topDeploy ? (
            <div className="space-y-3 text-sm">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <span className="text-xs text-faint block mb-0.5 font-medium">Change ID</span>
                  <span className="font-mono text-amber-700 font-bold text-base">
                    {topDeploy.change_id}
                  </span>
                </div>
                <Badge className={cn(
                  'text-xs',
                  topDeploy.cab_risk_rating === 'LOW'  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
                  topDeploy.cab_risk_rating === 'HIGH' ? 'bg-red-50 text-red-700 border border-red-200' :
                  'bg-amber-50 text-amber-700 border border-amber-200',
                )}>
                  {topDeploy.cab_risk_rating}
                </Badge>
              </div>
              <div className="bg-amber-50 rounded-lg p-3 border border-amber-100">
                <span className="text-xs text-amber-600 block mb-0.5 font-medium">Description</span>
                <span className="text-ink text-sm">{topDeploy.change_description}</span>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-slate-50 rounded-lg p-2.5 border border-border">
                  <span className="text-xs text-faint block mb-0.5">Deployed by</span>
                  <span className="text-ink font-mono text-xs font-medium">{topDeploy.deployed_by}</span>
                </div>
                <div className="bg-slate-50 rounded-lg p-2.5 border border-border">
                  <span className="text-xs text-faint block mb-0.5">Timestamp</span>
                  <span
                    className="text-ink text-xs font-medium cursor-default"
                    title={exactTime(topDeploy.timestamp)}
                  >
                    {relativeTime(topDeploy.timestamp)}
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-xs text-faint">No recent deployments found in last 7 days</p>
          )}
        </CardBody>
      </Card>

      {/* ── Historical Match ────────────────────────────────────────────── */}
      <Card glow={topMatch ? 'green' : 'none'}>
        <CardHeader>
          <CardTitle>Historical Match</CardTitle>
        </CardHeader>
        <CardBody>
          {topMatch ? (
            <div className="space-y-3">
              <div className="flex items-start gap-4">
                <div className="flex flex-col items-center justify-center w-16 h-16 rounded-xl bg-emerald-50 border border-emerald-200 shrink-0">
                  <span className="font-mono text-xl font-bold text-emerald-700 leading-none">
                    {Math.round((topMatch.similarity_score ?? 0) * 100)}%
                  </span>
                  <span className="text-xs text-emerald-500 mt-0.5 font-medium">MATCH</span>
                </div>
                <div className="space-y-1.5 text-sm">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-ink font-semibold">{topMatch.incident_id}</span>
                    {topMatch.double_confirmed && (
                      <Badge className="bg-emerald-50 text-emerald-700 border border-emerald-200">
                        ✓ Double-confirmed
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-subtle leading-relaxed">{topMatch.root_cause}</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="bg-slate-50 rounded-lg p-2.5 border border-border">
                  <span className="text-faint block mb-0.5">Resolution</span>
                  <span className="text-ink font-medium">{topMatch.resolution}</span>
                </div>
                <div className="bg-slate-50 rounded-lg p-2.5 border border-border">
                  <span className="text-faint block mb-0.5">MTTR</span>
                  <span className="font-mono text-ink font-semibold">{topMatch.mttr_minutes} min</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-xs text-amber-700 bg-amber-50 rounded-lg p-3 border border-amber-200">
              <span>⚠</span>
              <span>No historical precedent found — cold-start veto active</span>
            </div>
          )}
        </CardBody>
      </Card>

      {/* ── Alternative Hypotheses ──────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>Alternative Hypotheses</CardTitle>
          <button
            onClick={() => setHypothesesOpen(o => !o)}
            className="text-xs text-blue-600 hover:text-blue-700 font-medium transition-colors"
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
              <CardBody className="space-y-2.5">
                {incident.alternative_hypotheses.length === 0 ? (
                  <p className="text-xs text-faint">No alternative hypotheses available</p>
                ) : (
                  incident.alternative_hypotheses.map((h, i) => (
                    <div key={i} className="border border-border rounded-xl p-3 space-y-2 bg-slate-50">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-ink font-medium">{h.hypothesis}</span>
                        <span className="font-mono text-xs text-subtle bg-white border border-border rounded-full px-2 py-0.5">
                          {Math.round(h.confidence * 100)}%
                        </span>
                      </div>
                      {h.evidence_for && (
                        <p className="text-xs text-emerald-700 bg-emerald-50 rounded px-2 py-1">✓ {h.evidence_for}</p>
                      )}
                      {h.evidence_against && (
                        <p className="text-xs text-red-700 bg-red-50 rounded px-2 py-1">✗ {h.evidence_against}</p>
                      )}
                    </div>
                  ))
                )}
              </CardBody>
            </motion.div>
          )}
        </AnimatePresence>
      </Card>

      {/* ── Recommended Action ──────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>Recommended Action</CardTitle>
          <Badge className={actionClassBadge(actionClass).className}>{classLabel}</Badge>
        </CardHeader>
        <CardBody>
          <div className="flex items-center justify-between bg-blue-50 rounded-xl p-3 border border-blue-100">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-blue-500" />
              <span className="font-mono text-blue-700 font-semibold text-sm">
                {incident.recommended_action_id || '—'}
              </span>
            </div>
            <span className="text-xs text-emerald-600 font-medium bg-emerald-50 border border-emerald-200 rounded-full px-2 py-0.5">
              ✓ Auto-rollback available
            </span>
          </div>
        </CardBody>
      </Card>

      {/* ── Veto panel ──────────────────────────────────────────────────── */}
      {incident.active_veto_conditions.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-xl border border-red-200 bg-red-50 p-4"
        >
          <div className="flex items-center gap-2 mb-3">
            <span className="text-red-500 text-base">⛔</span>
            <h4 className="text-xs font-bold uppercase tracking-widest text-red-700">
              Active Veto Conditions — Auto-Execute Blocked
            </h4>
          </div>
          <div className="space-y-2">
            {incident.active_veto_conditions.map((veto, i) => (
              <div key={i} className="flex items-start gap-2 text-xs text-red-700 bg-white/60 rounded-lg px-3 py-2 border border-red-100">
                <span className="shrink-0 mt-0.5">•</span>
                <span className="leading-relaxed">{veto}</span>
              </div>
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
        <CardHeader>
          <CardTitle>Engineer Decision</CardTitle>
          <span className="text-xs text-faint">
            {incident.routing_decision?.replace(/_/g, ' ')}
          </span>
        </CardHeader>
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
