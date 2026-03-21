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
    <div className="max-w-xl mx-auto space-y-5 py-4">
      {/* Header */}
      <div className="rounded-lg border border-red-900 bg-[#1F0A0A] px-4 py-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-semibold text-white">
            INCIDENT — {incident.client_id.replace('_', ' ')}
          </span>
          <span className="text-xs text-zinc-400">
            Priority: <span className="text-white font-mono">{incident.incident_priority ?? 'P2'}</span>
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
      <div className="rounded-lg border border-border bg-surface p-4">
        <h3 className="text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-2">
          What Is Happening
        </h3>
        <p className="text-sm text-zinc-300 leading-relaxed">
          {incident.situation_summary ?? topEvidence?.preliminary_hypothesis ?? 'Incident detected — see L2 view for full details.'}
        </p>
      </div>

      {/* Checklist */}
      <div className="rounded-lg border border-border bg-surface p-4">
        <h3 className="text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-3">
          ATLAS Recommends
        </h3>
        <ol className="space-y-2">
          {steps.map((step, i) => (
            <li key={i} className="flex items-start gap-3 text-sm text-zinc-300">
              <span className="w-5 h-5 rounded-full bg-elevated border border-border text-xs flex items-center justify-center shrink-0 mt-0.5 text-zinc-400">
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
          Approve
        </Button>
        <Button
          variant="escalate"
          size="lg"
          className="w-full"
          onClick={onEscalate}
        >
          Escalate to L2
        </Button>
      </div>
    </div>
  )
}
