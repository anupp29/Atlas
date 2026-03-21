import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { formatDistanceToNow, format } from 'date-fns'

/** Merge Tailwind classes safely */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

/** Format seconds as M:SS */
export function formatMTTR(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

/** Format seconds remaining as MM:SS */
export function formatCountdown(seconds: number): string {
  if (seconds <= 0) return '00:00'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

/** Seconds until a future ISO datetime */
export function secondsUntil(isoDatetime: string): number {
  const target = new Date(isoDatetime).getTime()
  const now = Date.now()
  return Math.max(0, Math.floor((target - now) / 1000))
}

/** "3 days ago" with exact on hover */
export function relativeTime(isoDatetime: string): string {
  try {
    return formatDistanceToNow(new Date(isoDatetime), { addSuffix: true })
  } catch {
    return isoDatetime
  }
}

/** "2026-03-18 14:23 UTC" */
export function exactTime(isoDatetime: string): string {
  try {
    return format(new Date(isoDatetime), 'yyyy-MM-dd HH:mm') + ' UTC'
  } catch {
    return isoDatetime
  }
}

/** HH:MM:SS from ISO */
export function timeOnly(isoDatetime: string): string {
  try {
    return format(new Date(isoDatetime), 'HH:mm:ss')
  } catch {
    return ''
  }
}

/** Current UTC time as HH:MM:SS */
export function nowUTC(): string {
  return format(new Date(), 'HH:mm:ss') + ' UTC'
}

/** Map activity entry type to Tailwind border colour class */
export function activityBorderClass(type: string): string {
  switch (type) {
    case 'agent_detection':  return 'border-l-orange-500'
    case 'orchestrator_node': return 'border-l-blue-500'
    case 'human_action':     return 'border-l-green-500'
    case 'veto_fired':       return 'border-l-red-500'
    case 'resolution':       return 'border-l-teal-500'
    case 'early_warning':    return 'border-l-amber-500'
    case 'execution':        return 'border-l-blue-400'
    case 'cmdb_change':      return 'border-l-yellow-500'
    case 'incident_created': return 'border-l-red-400'
    default:                 return 'border-l-zinc-600'
  }
}

/** Map severity to log line colour */
export function logSeverityClass(severity: string): string {
  switch (severity.toUpperCase()) {
    case 'FATAL': return 'text-red-400 border-l-2 border-l-red-500'
    case 'ERROR': return 'text-red-300 border-l-2 border-l-red-500'
    case 'WARN':  return 'text-amber-300 border-l-2 border-l-amber-500'
    case 'INFO':  return 'text-zinc-300'
    case 'DEBUG': return 'text-zinc-500'
    default:      return 'text-zinc-400'
  }
}

/** Map compliance framework to badge colours */
export function complianceBadgeClass(framework: string): string {
  switch (framework.toUpperCase()) {
    case 'PCI-DSS':  return 'bg-red-950 text-red-300 border border-red-800'
    case 'SOX':      return 'bg-amber-950 text-amber-300 border border-amber-800'
    case 'GDPR':     return 'bg-blue-950 text-blue-300 border border-blue-800'
    case 'ISO-27001': return 'bg-zinc-800 text-zinc-300 border border-zinc-600'
    default:         return 'bg-zinc-800 text-zinc-400 border border-zinc-700'
  }
}

/** Map action class to badge colours */
export function actionClassBadge(cls: number): { label: string; className: string } {
  switch (cls) {
    case 1: return { label: 'Class 1', className: 'bg-green-950 text-green-300 border border-green-800' }
    case 2: return { label: 'Class 2', className: 'bg-amber-950 text-amber-300 border border-amber-800' }
    case 3: return { label: 'Class 3', className: 'bg-red-950 text-red-300 border border-red-800' }
    default: return { label: `Class ${cls}`, className: 'bg-zinc-800 text-zinc-400 border border-zinc-700' }
  }
}

/** Map priority to colour */
export function priorityClass(priority: string): string {
  switch (priority) {
    case 'P1': return 'text-red-400 bg-red-950 border border-red-800'
    case 'P2': return 'text-orange-400 bg-orange-950 border border-orange-800'
    case 'P3': return 'text-amber-400 bg-amber-950 border border-amber-800'
    case 'P4': return 'text-zinc-400 bg-zinc-800 border border-zinc-700'
    default:   return 'text-zinc-400 bg-zinc-800 border border-zinc-700'
  }
}

/** SHAP bar colour by feature name */
export function shapBarColour(feature: string): string {
  const f = feature.toLowerCase()
  if (f.includes('error') || f.includes('rejection') || f.includes('fatal')) return '#EF4444'
  if (f.includes('latency') || f.includes('response_time') || f.includes('p95')) return '#F97316'
  if (f.includes('memory') || f.includes('resource') || f.includes('heap')) return '#EAB308'
  if (f.includes('connection') || f.includes('pool')) return '#EF4444'
  return '#6B7280'
}
