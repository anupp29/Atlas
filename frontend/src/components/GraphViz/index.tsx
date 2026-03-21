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
  normal:   '#6B7280',
  warning:  '#F59E0B',
  affected: '#F97316',
  critical: '#EF4444',
  deploy:   '#EAB308',
  history:  '#8B5CF6',
}

function buildGraphData(incident: AtlasState): { nodes: GNode[]; links: GLink[] } {
  const nodes: GNode[] = []
  const links: GLink[] = []
  const seen = new Set<string>()

  const addNode = (n: GNode) => {
    if (!seen.has(n.id)) { seen.add(n.id); nodes.push(n) }
  }

  // Blast radius services
  incident.blast_radius.forEach((svc, i) => {
    const status: GNode['status'] = i === 0 ? 'critical' : i === 1 ? 'affected' : 'warning'
    addNode({ id: svc.name, name: svc.name, nodeType: 'service', status, properties: { criticality: svc.criticality } })
    if (i > 0) links.push({ source: incident.blast_radius[i - 1].name, target: svc.name, label: 'DEPENDS_ON' })
  })

  // Deployment nodes
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

  // Historical incident nodes
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

/**
 * GraphViz renders the Neo4j traversal graph using react-force-graph-2d.
 * Falls back to a static SVG diagram if the dynamic library fails to load.
 */
export function GraphViz({ incident }: GraphVizProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [ForceGraph, setForceGraph] = useState<React.ComponentType<unknown> | null>(null)
  const [loadError, setLoadError] = useState(false)
  const [tooltip, setTooltip] = useState<{ node: GNode; x: number; y: number } | null>(null)
  const [animStep, setAnimStep] = useState(0)

  const { nodes, links } = useMemo(() => buildGraphData(incident), [incident])

  // Lazy-load react-force-graph-2d
  useEffect(() => {
    import('react-force-graph-2d')
      .then(mod => setForceGraph(() => mod.default as React.ComponentType<unknown>))
      .catch(() => setLoadError(true))
  }, [])

  // Drive animation steps
  useEffect(() => {
    if (nodes.length === 0) return
    const steps = nodes.length + links.length
    let step = 0
    const id = setInterval(() => {
      step += 1
      setAnimStep(step)
      if (step >= steps) clearInterval(id)
    }, 800)
    return () => clearInterval(id)
  }, [nodes.length, links.length])

  const visibleNodes = useMemo(
    () => nodes.slice(0, Math.max(1, animStep)),
    [nodes, animStep],
  )
  const visibleLinks = useMemo(
    () => links.slice(0, Math.max(0, animStep - nodes.length)),
    [links, nodes.length, animStep],
  )

  const nodeCanvasObject = useCallback(
    (node: unknown, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const n = node as GNode & { x: number; y: number }
      const colour = NODE_COLOURS[n.status]
      const r = n.status === 'critical' ? 10 : n.status === 'deploy' ? 9 : 7

      // Glow
      if (n.status !== 'normal') {
        ctx.beginPath()
        ctx.arc(n.x, n.y, r + 4, 0, 2 * Math.PI)
        ctx.fillStyle = colour + '33'
        ctx.fill()
      }

      // Node circle
      ctx.beginPath()
      ctx.arc(n.x, n.y, r, 0, 2 * Math.PI)
      ctx.fillStyle = colour
      ctx.fill()
      ctx.strokeStyle = colour + 'AA'
      ctx.lineWidth = 1.5
      ctx.stroke()

      // Label
      const label = n.name.length > 14 ? n.name.slice(0, 13) + '…' : n.name
      const fontSize = Math.max(9, 11 / globalScale)
      ctx.font = `${fontSize}px JetBrains Mono, monospace`
      ctx.fillStyle = '#D1D5DB'
      ctx.textAlign = 'center'
      ctx.fillText(label, n.x, n.y + r + fontSize + 2)
    },
    [],
  )

  if (loadError) {
    return <FallbackGraph nodes={nodes} links={links} />
  }

  if (!ForceGraph) {
    return (
      <div className="flex items-center justify-center h-64 text-zinc-600 text-xs">
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
    <div ref={containerRef} className="relative rounded-lg overflow-hidden bg-[#080C14] border border-border">
      <FG
        graphData={{ nodes: visibleNodes, links: visibleLinks }}
        nodeCanvasObject={nodeCanvasObject}
        nodeCanvasObjectMode={() => 'replace'}
        linkColor={(link: unknown) => {
          const l = link as GLink
          if (l.label === 'MODIFIED_CONFIG_OF') return '#EAB308'
          if (l.label === 'AFFECTED') return '#EF4444'
          return '#4B5563'
        }}
        linkWidth={(link: unknown) => {
          const l = link as GLink
          return l.label === 'MODIFIED_CONFIG_OF' ? 2 : 1.5
        }}
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={1}
        linkLabel={(link: unknown) => (link as GLink).label}
        onNodeHover={(node: unknown) => {
          if (!node) { setTooltip(null); return }
          const n = node as GNode & { x: number; y: number }
          setTooltip({ node: n, x: n.x ?? 0, y: n.y ?? 0 })
        }}
        width={containerRef.current?.clientWidth ?? 560}
        height={320}
        backgroundColor="#080C14"
      />

      {/* Tooltip */}
      {tooltip && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="absolute top-3 right-3 bg-elevated border border-border rounded-lg p-3 text-xs max-w-[200px] pointer-events-none z-10"
        >
          <div className="font-mono font-semibold text-white mb-1">{tooltip.node.name}</div>
          {Object.entries(tooltip.node.properties).map(([k, v]) => (
            <div key={k} className="flex justify-between gap-3">
              <span className="text-zinc-500">{k}</span>
              <span className="text-zinc-300 font-mono">{String(v)}</span>
            </div>
          ))}
        </motion.div>
      )}

      {/* Legend */}
      <div className="absolute bottom-2 left-3 flex items-center gap-3 text-xs">
        {([['deploy', 'Deployment'], ['critical', 'Affected'], ['warning', 'At Risk'], ['history', 'Historical']] as [GNode['status'], string][]).map(([s, label]) => (
          <div key={s} className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full" style={{ background: NODE_COLOURS[s] }} />
            <span className="text-zinc-500">{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/** Static SVG fallback when react-force-graph-2d fails — also plays pre-recorded video if available */
function FallbackGraph({ nodes, links }: { nodes: GNode[]; links: GLink[] }) {
  // Attempt to load pre-recorded animation video (recorded during testing per PLAN.md Task 6.3)
  const videoSrc = '/fallback/graph_animation.mp4'
  const [videoFailed, setVideoFailed] = useState(false)

  if (!videoFailed) {
    return (
      <div className="rounded-lg border border-border bg-[#080C14] overflow-hidden">
        <video
          src={videoSrc}
          autoPlay
          loop
          muted
          playsInline
          onError={() => setVideoFailed(true)}
          className="w-full"
          style={{ maxHeight: 320 }}
        />
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-border bg-[#080C14] p-4">
      <p className="text-xs text-zinc-500 mb-3">Graph (static view)</p>
      <div className="flex flex-wrap gap-2">
        {nodes.map(n => (
          <div
            key={n.id}
            className="px-2 py-1 rounded border text-xs font-mono"
            style={{ borderColor: NODE_COLOURS[n.status], color: NODE_COLOURS[n.status] }}
          >
            {n.name}
          </div>
        ))}
      </div>
      <div className="mt-2 space-y-1">
        {links.map((l, i) => (
          <div key={i} className="text-xs text-zinc-500 font-mono">
            {l.source} →<span className="text-zinc-600 mx-1">{l.label}</span>→ {l.target}
          </div>
        ))}
      </div>
    </div>
  )
}
