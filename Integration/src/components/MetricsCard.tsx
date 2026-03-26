import React from 'react'
import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown } from 'lucide-react'

interface MetricsCardProps {
  icon: React.ReactNode
  label: string
  value: string
  trend?: 'up' | 'down'
  color?: 'green' | 'blue' | 'red' | 'purple'
}

export default function MetricsCard({
  icon,
  label,
  value,
  trend = 'up',
  color = 'blue',
}: MetricsCardProps) {
  const colorClasses = {
    green: 'from-green-500/20 to-green-600/20 border-green-500/30',
    blue: 'from-blue-500/20 to-blue-600/20 border-blue-500/30',
    red: 'from-red-500/20 to-red-600/20 border-red-500/30',
    purple: 'from-purple-500/20 to-purple-600/20 border-purple-500/30',
  }

  const iconColorClasses = {
    green: 'text-green-400',
    blue: 'text-blue-400',
    red: 'text-red-400',
    purple: 'text-purple-400',
  }

  const trendColorClasses = {
    green: 'text-green-400',
    blue: 'text-blue-400',
    red: 'text-red-400',
    purple: 'text-purple-400',
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ scale: 1.02 }}
      className={`bg-gradient-to-br ${colorClasses[color]} border rounded-lg p-6 backdrop-blur-sm`}
    >
      <div className="flex items-start justify-between mb-4">
        <div className={`p-2 rounded-lg bg-white/5 ${iconColorClasses[color]}`}>{icon}</div>
        <motion.div
          animate={{ y: [0, -2, 0] }}
          transition={{ duration: 2, repeat: Infinity }}
          className={`${trendColorClasses[color]}`}
        >
          {trend === 'up' ? <TrendingUp size={18} /> : <TrendingDown size={18} />}
        </motion.div>
      </div>

      <p className="text-slate-400 text-sm font-medium mb-1">{label}</p>
      <p className="text-2xl font-bold text-white">{value}</p>
    </motion.div>
  )
}
