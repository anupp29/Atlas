import { useMemo } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Cell, Tooltip, ResponsiveContainer,
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
      <div className="flex items-center justify-center h-24 text-xs text-faint">
        Feature attribution unavailable
      </div>
    )
  }

  const sumOk = Math.abs(total - 100) <= 1.5

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold uppercase tracking-widest text-subtle">
          Detection Feature Attribution (SHAP)
        </span>
        {!sumOk && (
          <span className="text-xs text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full">
            ⚠ Sum: {total.toFixed(1)}%
          </span>
        )}
      </div>

      <ResponsiveContainer width="100%" height={data.length * 34 + 16}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 0, right: 52, left: 0, bottom: 0 }}
        >
          <XAxis type="number" domain={[0, 100]} hide />
          <YAxis
            type="category"
            dataKey="feature"
            width={148}
            tick={{ fill: '#475569', fontSize: 11, fontFamily: 'JetBrains Mono, monospace' }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            cursor={{ fill: 'rgba(0,0,0,0.04)' }}
            contentStyle={{
              background: '#FFFFFF',
              border: '1px solid #E2E8F0',
              borderRadius: 8,
              fontSize: 11,
              fontFamily: 'JetBrains Mono, monospace',
              color: '#0F172A',
              boxShadow: '0 4px 6px -1px rgba(0,0,0,0.07)',
            }}
            formatter={(value: number) => [`${value}%`, 'Contribution']}
          />
          <Bar
            dataKey="value"
            radius={[0, 4, 4, 0]}
            label={{
              position: 'right',
              fill: '#475569',
              fontSize: 11,
              fontFamily: 'monospace',
              formatter: (v: number) => `${v}%`,
            }}
          >
            {data.map(entry => (
              <Cell key={entry.rawFeature} fill={shapBarColour(entry.rawFeature)} fillOpacity={0.85} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
