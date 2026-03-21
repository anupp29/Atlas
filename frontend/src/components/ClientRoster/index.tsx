import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { cn, complianceBadgeClass } from '@/lib/utils'
import { StatusDot } from '@/components/ui/StatusDot'
import { Badge } from '@/components/ui/Badge'
import type { ClientHealth } from '@/types/atlas'

// Static client definitions — health status is overridden by WebSocket
const CLIENTS: ClientHealth[] = [
  {
    client_id: 'FINCORE_UK_001',
    client_name: 'FinanceCore Ltd',
    region: 'United Kingdom',
    health_status: 'healthy',
    active_incident_count: 0,
    sla_uptime_percent: 99.94,
    trust_level: 1,
    trust_stage_name: 'L1 Assistance',
    incidents_to_next_stage: 12,
    compliance_frameworks: ['PCI-DSS', 'SOX', 'ISO-27001'],
    tech_stack: ['Java', 'PostgreSQL', 'Redis'],
  },
  {
    client_id: 'RETAILMAX_EU_002',
    client_name: 'RetailMax EU',
    region: 'European Union',
    health_status: 'healthy',
    active_incident_count: 0,
    sla_uptime_percent: 99.97,
    trust_level: 2,
    trust_stage_name: 'L1 Automation',
    incidents_to_next_stage: 0,
    compliance_frameworks: ['GDPR'],
    tech_stack: ['Node.js', 'Redis', 'MongoDB'],
  },
]

const TRUST_STAGE_LABELS: Record<number, string> = {
  0: 'Observation',
  1: 'L1 Assistance',
  2: 'L1 Automation',
  3: 'L2 Assistance',
  4: 'L2 Automation',
}

interface ClientRosterProps {
  selectedClientId: string
  onSelectClient: (clientId: string) => void
  incidentCounts: Record<string, number>
  healthStatuses: Record<string, ClientHealth['health_status']>
}

export function ClientRoster({
  selectedClientId,
  onSelectClient,
  incidentCounts,
  healthStatuses,
}: ClientRosterProps) {
  const [trustData, setTrustData] = useState<Record<string, { trust_level: number; progression_metrics: { incident_count: number; accuracy_rate: number } }>>({})

  useEffect(() => {
    CLIENTS.forEach(c => {
      fetch(`/api/trust/${c.client_id}`)
        .then(r => r.json())
        .then(data => setTrustData(prev => ({ ...prev, [c.client_id]: data })))
        .catch(() => {/* non-fatal */})
    })
  }, [])

  return (
    <aside className="w-72 shrink-0 border-r border-border bg-canvas flex flex-col overflow-y-auto">
      <div className="px-4 py-3 border-b border-border">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-500">
          Client Roster
        </h2>
      </div>

      <div className="flex flex-col gap-2 p-3">
        {CLIENTS.map(client => {
          const health = healthStatuses[client.client_id] ?? client.health_status
          const incidentCount = incidentCounts[client.client_id] ?? 0
          const trust = trustData[client.client_id]
          const trustLevel = trust?.trust_level ?? client.trust_level
          const stageName = TRUST_STAGE_LABELS[trustLevel] ?? client.trust_stage_name
          const isSelected = selectedClientId === client.client_id
          const progressPct = trustLevel >= 4 ? 100 : Math.min(
            ((trust?.progression_metrics?.incident_count ?? 0) / 30) * 100,
            100,
          )

          return (
            <motion.button
              key={client.client_id}
              onClick={() => onSelectClient(client.client_id)}
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
              transition={{ duration: 0.12 }}
              className={cn(
                'w-full text-left rounded-lg border p-3.5 transition-colors duration-200',
                isSelected
                  ? 'border-blue-600 bg-blue-950/30 shadow-[0_0_16px_rgba(59,130,246,0.12)]'
                  : 'border-border bg-surface hover:border-zinc-600 hover:bg-elevated',
              )}
            >
              {/* Header row */}
              <div className="flex items-start justify-between mb-2.5">
                <div>
                  <div className="flex items-center gap-2">
                    <StatusDot status={health} size="md" />
                    <span className="text-sm font-semibold text-white leading-tight">
                      {client.client_name}
                    </span>
                  </div>
                  <span className="text-xs text-zinc-500 mt-0.5 block">{client.region}</span>
                </div>
                {incidentCount > 0 && (
                  <motion.span
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="flex items-center justify-center w-5 h-5 rounded-full bg-incident text-white text-xs font-bold"
                  >
                    {incidentCount}
                  </motion.span>
                )}
              </div>

              {/* Tech stack */}
              <div className="flex flex-wrap gap-1 mb-2">
                {client.tech_stack.map(t => (
                  <span
                    key={t}
                    className="px-1.5 py-0.5 rounded text-xs bg-elevated text-zinc-300 border border-border"
                  >
                    {t}
                  </span>
                ))}
              </div>

              {/* Compliance badges */}
              <div className="flex flex-wrap gap-1 mb-3">
                {client.compliance_frameworks.map(f => (
                  <Badge key={f} className={complianceBadgeClass(f)}>
                    {f}
                  </Badge>
                ))}
              </div>

              {/* SLA uptime */}
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-zinc-500">SLA Uptime</span>
                <span className="font-mono text-xs text-healthy font-medium">
                  {client.sla_uptime_percent.toFixed(2)}%
                </span>
              </div>

              {/* Trust progress */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-zinc-500">
                    Stage {trustLevel} — {stageName}
                  </span>
                  {trustLevel < 4 && (
                    <span className="text-xs text-zinc-600">→ Stage {trustLevel + 1}</span>
                  )}
                </div>
                <div className="h-1 rounded-full bg-elevated overflow-hidden">
                  <motion.div
                    className="h-full rounded-full bg-healthy"
                    initial={{ width: 0 }}
                    animate={{ width: `${trustLevel >= 4 ? 100 : progressPct}%` }}
                    transition={{ duration: 0.8, ease: 'easeOut' }}
                  />
                </div>
              </div>
            </motion.button>
          )
        })}
      </div>

      {/* Footer */}
      <div className="mt-auto px-4 py-3 border-t border-border">
        <p className="text-xs text-zinc-600 text-center">
          {CLIENTS.length} clients monitored
        </p>
      </div>
    </aside>
  )
}
