import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import type { AtlasState } from '@/types/atlas'

interface GraphVizProps {
  incident: AtlasState
}

interface GNode {
  id: string
  name: string
  nodeType: 'service' | 'deployment' | 'incident'
  status: 'normal' | 'warning' | 'affected' | 'critical' | 'deploy' | 'history'
  properties: Record<string, string | number>
}

interface GLink {
  source: string
  target: string
  label: string
}

const NODE_COLOURS: Record<GNode['status'], string> = {
  normal:   '#94A3B8',
  warning:  '#D97706',
  affected: '#EA580C',
  critical: '#DC2626',
  deploy:   '#B45309',
  history:  '#7C3AED',
}

const NODE_BG: Record<GNode['status'], string> = {
  normal:   '#F1F5F9',
  warning:  '#FFFBEB',
  affected: '#FFF7ED',
  critical: '#FEF2F2',
  deploy:   '#FFFBEB',
  history:  '#F5F3FF',
}

function buildGraphData(incident: AtlasState): { nodes: GNode[]; links: GLink[] } {
  const nodes: GNode[] = []
  const links: GLink[] = []
  const seen = new Set<string>()

  const addNode = (n: GNode) => {
    if (!seen.has(n.id)) { seen.add(n.id); nodes.push(n) }
  }

  incident.blast_radius.forEach((svc, i) => {
    const status: GNode['status'] = i === 0 ? 'critical' : i === 1 ? 'affected' : 'warning'
    addNode({ id: svc.name, name: svc.name, nodeType: 'service', status, properties: { criticality: svc.criticality } })
    if (i > 0) links.push({ source: incident.blast_radius[i - 1].name, target: svc.name, label: 'DEPENDS_ON' })
  })

  incident.recent_deployments.forEach(dep => {
    addNode({
      id: dep.change_id,
      name: dep.change_id,
      nodeType: 'deployment',
      status: 'deploy',
      properties: { description: dep.change_description, deployed_by: dep.deployed_by, risk: dep.cab_risk_rating },
    })
    if (incident.blast_radius[0]) {
      links.push({ source: dep.change_id, target: incident.blast_radius[0].name, label: 'MODIFIED_CONFIG_OF' })
    }
  })

  incident.historical_graph_matches.slice(0, 1).forEach(h => {
    addNode({
      id: h.incident_id,
      name: h.incident_id,
      nodeType: 'incident',
      status: 'history',
      properties: { mttr: h.mttr_minutes, similarity: h.similarity_score },
    })
    if (incident.blast_radius[0]) {
      links.push({ source: h.incident_id, target: incident.blast_radius[0].name, label: 'AFFECTED' })
    }
  })

  return { nodes, links }
}

export function GraphViz({ incident }: GraphVizProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [ForceGraph, setForceGraph] = useState<React.ComponentType<unknown> | null>(null)
  const [loadError, setLoadError] = useState(false)
  const [tooltip, setTooltip] = useState<{ node: GNode; x: number; y: number } | null>(null)
  const [animStep, setAnimStep] = useState(0)

  const { nodes, links } = useMemo(() => buildGraphData(incident), [incident])

  useEffect(() => {
    import('react-force-graph-2d')
      .then(mod => setForceGraph(() => mod.default as React.ComponentType<unknown>))
      .catch(() => setLoadError(true))
  }, [])

  useEffect(() => {
    if (nodes.length === 0) return
    const steps = nodes.length + links.length
    let step = 0
    const id = setInterval(() => {
      step += 1
      setAnimStep(step)
      if (step >= steps) clearInterval(id)
    }, 600)
    return () => clearInterval(id)
  }, [nodes.length, links.length])

  const visibleNodes = useMemo(() => nodes.slice(0, Math.max(1, animStep)), [nodes, animStep])
  const visibleLinks = useMemo(() => links.slice(0, Math.max(0, animStep - nodes.length)), [links, nodes.length, animStep])

  const nodeCanvasObject = useCallback(
    (node: unknown, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const n = node as GNode & { x: number; y: number }
      const colour = NODE_COLOURS[n.status]
      const bg = NODE_BG[n.status]
      const r = n.status === 'critical' ? 11 : n.status === 'deploy' ? 10 : 8

      // Shadow
      ctx.shadowColor = colour + '40'
      ctx.shadowBlur = 8

      // Node circle with fill
      ctx.beginPath()
      ctx.arc(n.x, n.y, r, 0, 2 * Math.PI)
      ctx.fillStyle = bg
      ctx.fill()
      ctx.strokeStyle = colour
      ctx.lineWidth = 2
      ctx.stroke()
      ctx.shadowBlur = 0

      // Label
      const label = n.name.length > 14 ? n.name.slice(0, 13) + '…' : n.name
      const fontSize = Math.max(9, 11 / globalScale)
      ctx.font = `600 ${fontSize}px Inter, system-ui, sans-serif`
      ctx.fillStyle = '#0F172A'
      ctx.textAlign = 'center'
      ctx.fillText(label, n.x, n.y + r + fontSize + 3)
    },
    [],
  )

  if (loadError) {
    return <FallbackGraph nodes={nodes} links={links} />
  }

  if (!ForceGraph) {
    return (
      <div className="flex items-center justify-center h-64 text-faint text-xs gap-2">
        <span className="w-4 h-4 border-2 border-blue-300 border-t-blue-600 rounded-full animate-spin" />
        Loading graph…
      </div>
    )
  }

  const FG = ForceGraph as React.ComponentType<{
    graphData: { nodes: unknown[]; links: unknown[] }
    nodeCanvasObject: typeof nodeCanvasObject
    nodeCanvasObjectMode: () => string
    linkColor: (link: unknown) => string
    linkWidth: (link: unknown) => number
    linkDirectionalArrowLength: number
    linkDirectionalArrowRelPos: number
    onNodeHover: (node: unknown, prevNode: unknown) => void
    width: number
    height: number
    backgroundColor: string
    linkLabel: (link: unknown) => string
  }>

  return (
    <div ref={containerRef} className="relative rounded-xl overflow-hidden bg-slate-50 border border-border">
      <FG
        graphData={{ nodes: visibleNodes, links: visibleLinks }}
        nodeCanvasObject={nodeCanvasObject}
        nodeCanvasObjectMode={() => 'replace'}
        linkColor={(link: unknown) => {
          const l = link as GLink
          if (l.label === 'MODIFIED_CONFIG_OF') return '#D97706'
          if (l.label === 'AFFECTED') return '#DC2626'
          return '#CBD5E1'
        }}
        linkWidth={(link: unknown) => {
          const l = link as GLink
          return l.label === 'MODIFIED_CONFIG_OF' ? 2.5 : 1.5
        }}
        linkDirectionalArrowLength={5}
        linkDirectionalArrowRelPos={1}
        linkLabel={(link: unknown) => (link as GLink).label}
        onNodeHover={(node: unknown) => {
          if (!node) { setTooltip(null); return }
          const n = node as GNode & { x: number; y: number }
          setTooltip({ node: n, x: n.x ?? 0, y: n.y ?? 0 })
        }}
        width={containerRef.current?.clientWidth ?? 560}
        height={300}
        backgroundColor="#F8FAFC"
      />

      {tooltip && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="absolute top-3 right-3 bg-white border border-border rounded-xl p-3 text-xs max-w-[200px] pointer-events-none z-10 shadow-card-md"
        >
          <div className="font-mono font-semibold text-ink mb-1.5">{tooltip.node.name}</div>
          {Object.entries(tooltip.node.properties).map(([k, v]) => (
            <div key={k} className="flex justify-between gap-3">
              <span className="text-faint">{k}</span>
              <span className="text-subtle font-mono">{String(v)}</span>
            </div>
          ))}
        </motion.div>
      )}

      {/* Legend */}
      <div className="absolute bottom-2 left-3 flex items-center gap-3 text-xs bg-white/80 backdrop-blur-sm rounded-lg px-2 py-1 border border-border/50">
        {([['deploy', 'Deployment'], ['critical', 'Affected'], ['warning', 'At Risk'], ['history', 'Historical']] as [GNode['status'], string][]).map(([s, label]) => (
          <div key={s} className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full border-2" style={{ borderColor: NODE_COLOURS[s], background: NODE_BG[s] }} />
            <span className="text-subtle">{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function FallbackGraph({ nodes, links }: { nodes: GNode[]; links: GLink[] }) {
  const [videoFailed, setVideoFailed] = useState(false)

  if (!videoFailed) {
    return (
      <div className="rounded-xl border border-border bg-slate-50 overflow-hidden">
        <video
          src="/fallback/graph_animation.mp4"
          autoPlay loop muted playsInline
          onError={() => setVideoFailed(true)}
          className="w-full"
          style={{ maxHeight: 300 }}
        />
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-border bg-slate-50 p-4">
      <p className="text-xs text-faint mb-3 font-medium">Dependency Graph (static view)</p>
      <div className="flex flex-wrap gap-2 mb-3">
        {nodes.map(n => (
          <div
            key={n.id}
            className="px-2.5 py-1 rounded-lg border text-xs font-mono font-medium"
            style={{ borderColor: NODE_COLOURS[n.status], color: NODE_COLOURS[n.status], background: NODE_BG[n.status] }}
          >
            {n.name}
          </div>
        ))}
      </div>
      <div className="space-y-1">
        {links.map((l, i) => (
          <div key={i} className="text-xs text-subtle font-mono">
            {l.source} <span className="text-faint mx-1">—{l.label}→</span> {l.target}
          </div>
        ))}
      </div>
    </div>
  )
}
