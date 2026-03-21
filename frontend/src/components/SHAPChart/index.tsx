import { useMemo } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { shapBarColour } from '@/lib/utils'

interface SHAPChartProps {
  shapValues: Record<string, number>
}

export function SHAPChart({ shapValues }: SHAPChartProps) {
  const data = useMemo(() => {
    return Object.entries(shapValues)
      .sort(([, a], [, b]) => b - a)
      .map(([feature, value]) => ({
        feature: feature.replace(/_/g, ' '),
        rawFeature: feature,
        value: Math.round(value * 10) / 10,
      }))
  }, [shapValues])

  const total = useMemo(
    () => Object.values(shapValues).reduce((s, v) => s + v, 0),
    [shapValues],
  )

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-24 text-xs text-zinc-500">
        Feature attribution unavailable — SHAP calculation failed
      </div>
    )
  }

  const sumOk = Math.abs(total - 100) <= 1.5

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold uppercase tracking-widest text-zinc-500">
          Detection Feature Attribution (SHAP)
        </span>
        {!sumOk && (
          <span className="text-xs text-amber-400 bg-amber-950 border border-amber-800 px-2 py-0.5 rounded">
            ⚠ Values sum to {total.toFixed(1)}%
          </span>
        )}
      </div>

      <ResponsiveContainer width="100%" height={data.length * 32 + 16}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 0, right: 48, left: 0, bottom: 0 }}
        >
          <XAxis type="number" domain={[0, 100]} hide />
          <YAxis
            type="category"
            dataKey="feature"
            width={140}
            tick={{ fill: '#9CA3AF', fontSize: 11, fontFamily: 'JetBrains Mono, monospace' }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            cursor={{ fill: 'rgba(255,255,255,0.03)' }}
            contentStyle={{
              background: '#1F2937',
              border: '1px solid #374151',
              borderRadius: 6,
              fontSize: 11,
              fontFamily: 'JetBrains Mono, monospace',
              color: '#F9FAFB',
            }}
            formatter={(value: number) => [`${value}%`, 'Contribution']}
          />
          <Bar dataKey="value" radius={[0, 3, 3, 0]} label={{ position: 'right', fill: '#9CA3AF', fontSize: 11, fontFamily: 'monospace', formatter: (v: number) => `${v}%` }}>
            {data.map(entry => (
              <Cell key={entry.rawFeature} fill={shapBarColour(entry.rawFeature)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
