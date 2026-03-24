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

/** Map activity entry type to left-border colour class */
export function activityBorderClass(type: string): string {
  switch (type) {
    case 'agent_detection':   return 'border-l-orange-400'
    case 'orchestrator_node': return 'border-l-blue-400'
    case 'human_action':      return 'border-l-emerald-500'
    case 'veto_fired':        return 'border-l-red-500'
    case 'resolution':        return 'border-l-teal-500'
    case 'early_warning':     return 'border-l-amber-500'
    case 'execution':         return 'border-l-blue-500'
    case 'cmdb_change':       return 'border-l-yellow-500'
    case 'incident_created':  return 'border-l-red-400'
    default:                  return 'border-l-slate-300'
  }
}

/** Map activity type to icon */
export function activityIcon(type: string): string {
  switch (type) {
    case 'agent_detection':   return '🔍'
    case 'orchestrator_node': return '⚙️'
    case 'human_action':      return '👤'
    case 'veto_fired':        return '⛔'
    case 'resolution':        return '✅'
    case 'early_warning':     return '⚠️'
    case 'execution':         return '▶️'
    case 'cmdb_change':       return '📋'
    case 'incident_created':  return '🚨'
    default:                  return '•'
  }
}

/** Map severity to log line colour — light theme */
export function logSeverityClass(severity: string): string {
  switch (severity.toUpperCase()) {
    case 'FATAL': return 'text-red-700 bg-red-50 border-l-2 border-l-red-500'
    case 'ERROR': return 'text-red-600 bg-red-50/60 border-l-2 border-l-red-400'
    case 'WARN':  return 'text-amber-700 bg-amber-50/60 border-l-2 border-l-amber-400'
    case 'INFO':  return 'text-slate-700'
    case 'DEBUG': return 'text-slate-400'
    default:      return 'text-slate-600'
  }
}

/** Map compliance framework to badge colours — light theme */
export function complianceBadgeClass(framework: string): string {
  switch (framework.toUpperCase()) {
    case 'PCI-DSS':   return 'bg-red-50 text-red-700 border border-red-200'
    case 'SOX':       return 'bg-amber-50 text-amber-700 border border-amber-200'
    case 'GDPR':      return 'bg-blue-50 text-blue-700 border border-blue-200'
    case 'ISO-27001': return 'bg-slate-100 text-slate-600 border border-slate-200'
    default:          return 'bg-slate-100 text-slate-500 border border-slate-200'
  }
}

/** Map action class to badge colours — light theme */
export function actionClassBadge(cls: number): { label: string; className: string } {
  switch (cls) {
    case 1: return { label: 'Class 1', className: 'bg-emerald-50 text-emerald-700 border border-emerald-200' }
    case 2: return { label: 'Class 2', className: 'bg-amber-50 text-amber-700 border border-amber-200' }
    case 3: return { label: 'Class 3', className: 'bg-red-50 text-red-700 border border-red-200' }
    default: return { label: `Class ${cls}`, className: 'bg-slate-100 text-slate-500 border border-slate-200' }
  }
}

/** Map priority to colour — light theme */
export function priorityClass(priority: string): string {
  switch (priority) {
    case 'P1': return 'text-red-700 bg-red-50 border border-red-200'
    case 'P2': return 'text-orange-700 bg-orange-50 border border-orange-200'
    case 'P3': return 'text-amber-700 bg-amber-50 border border-amber-200'
    case 'P4': return 'text-slate-600 bg-slate-100 border border-slate-200'
    default:   return 'text-slate-600 bg-slate-100 border border-slate-200'
  }
}

/** SHAP bar colour by feature name */
export function shapBarColour(feature: string): string {
  const f = feature.toLowerCase()
  if (f.includes('error') || f.includes('rejection') || f.includes('fatal')) return '#DC2626'
  if (f.includes('latency') || f.includes('response_time') || f.includes('p95')) return '#EA580C'
  if (f.includes('memory') || f.includes('resource') || f.includes('heap')) return '#D97706'
  if (f.includes('connection') || f.includes('pool')) return '#DC2626'
  return '#64748B'
}
