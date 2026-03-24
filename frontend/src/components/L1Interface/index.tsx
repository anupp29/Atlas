import { Button } from '@/components/ui/Button'
import { SLATimer } from '@/components/SLATimer'
import type { AtlasState } from '@/types/atlas'

interface L1InterfaceProps {
  incident: AtlasState
  onApprove: (threadId: string, incidentId: string, clientId: string) => Promise<void>
  onEscalate: () => void
}

export function L1Interface({ incident, onApprove, onEscalate }: L1InterfaceProps) {
  const topEvidence = incident.evidence_packages[0]

  const steps = [
    `Verify ${incident.blast_radius[0]?.name ?? 'primary service'} health endpoint`,
    incident.recommended_action_id
      ? `Execute playbook: ${incident.recommended_action_id}`
      : 'Follow recommended action',
    'Monitor primary metric for recovery over next 5 minutes',
  ]

  return (
    <div className="max-w-xl mx-auto space-y-4 py-4">
      {/* Header */}
      <div className="rounded-xl border border-red-200 bg-red-50 px-5 py-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse" />
            <span className="text-sm font-bold text-red-800">
              INCIDENT — {incident.client_id.replace(/_/g, ' ')}
            </span>
          </div>
          <span className="text-xs text-red-600 font-mono font-medium">
            Priority: {incident.incident_priority ?? 'P2'}
          </span>
        </div>
        {incident.sla_breach_time && (
          <SLATimer
            slaBreachTime={incident.sla_breach_time}
            ticketId={incident.servicenow_ticket_id}
          />
        )}
      </div>

      {/* What is happening */}
      <div className="rounded-xl border border-border bg-white p-4 shadow-card">
        <h3 className="text-xs font-semibold uppercase tracking-widest text-subtle mb-2">
          What Is Happening
        </h3>
        <p className="text-sm text-ink leading-relaxed">
          {incident.situation_summary ?? topEvidence?.preliminary_hypothesis ?? 'Incident detected — see L2 view for full details.'}
        </p>
      </div>

      {/* Checklist */}
      <div className="rounded-xl border border-border bg-white p-4 shadow-card">
        <h3 className="text-xs font-semibold uppercase tracking-widest text-subtle mb-3">
          ATLAS Recommends
        </h3>
        <ol className="space-y-2.5">
          {steps.map((step, i) => (
            <li key={i} className="flex items-start gap-3 text-sm text-ink">
              <span className="w-6 h-6 rounded-full bg-blue-50 border border-blue-200 text-xs flex items-center justify-center shrink-0 mt-0.5 text-blue-700 font-semibold">
                {i + 1}
              </span>
              {step}
            </li>
          ))}
        </ol>
      </div>

      {/* Action buttons */}
      <div className="grid grid-cols-2 gap-3">
        <Button
          variant="approve"
          size="lg"
          className="w-full"
          onClick={() => onApprove(incident.thread_id, incident.incident_id, incident.client_id)}
        >
          ✓ Approve
        </Button>
        <Button
          variant="escalate"
          size="lg"
          className="w-full"
          onClick={onEscalate}
        >
          ↑ Escalate to L2
        </Button>
      </div>
    </div>
  )
}
