import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Activity, TrendingUp, AlertCircle, Zap } from 'lucide-react'
import { Connection } from '../store/connectionStore'
import { getPlatformConfig } from '../config/platforms'
import { useConnectionStore } from '../store/connectionStore'
import { generateMockMetrics, generateMockLog, formatTime, getLogLevelColor, getLogLevelBgColor } from '../utils/helpers'
import MetricsCard from './MetricsCard'
import LogStream from './LogStream'

interface MonitoringDashboardProps {
  connection: Connection
}

export default function MonitoringDashboard({ connection }: MonitoringDashboardProps) {
  const [isConnecting, setIsConnecting] = useState(false)
  const [metrics, setMetrics] = useState(connection.metrics || generateMockMetrics())
  const updateConnectionStatus = useConnectionStore((state) => state.updateConnectionStatus)
  const addLog = useConnectionStore((state) => state.addLog)
  const updateConnection = useConnectionStore((state) => state.updateConnection)
  const platformConfig = getPlatformConfig(connection.platform)

  // Simulate connection
  useEffect(() => {
    if (connection.status === 'disconnected') {
      setIsConnecting(true)
      const timer = setTimeout(() => {
        updateConnectionStatus(connection.id, 'connected')
        setIsConnecting(false)
        // Add initial log
        addLog(connection.id, generateMockLog(connection.name))
      }, 2000)
      return () => clearTimeout(timer)
    }
  }, [connection.id, connection.status])

  // Simulate metrics updates
  useEffect(() => {
    if (connection.status === 'connected') {
      const interval = setInterval(() => {
        const newMetrics = generateMockMetrics()
        setMetrics(newMetrics)
        updateConnection(connection.id, { metrics: newMetrics })
      }, 3000)

      return () => clearInterval(interval)
    }
  }, [connection.id, connection.status])

  // Simulate log generation
  useEffect(() => {
    if (connection.status === 'connected') {
      const interval = setInterval(() => {
        addLog(connection.id, generateMockLog(connection.name))
      }, 2000)

      return () => clearInterval(interval)
    }
  }, [connection.id, connection.status])

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 bg-gradient-to-br from-blue-500/20 to-purple-500/20 border border-blue-500/30 rounded-lg flex items-center justify-center">
            <span className="text-3xl">{platformConfig?.icon}</span>
          </div>
          <div>
            <h1 className="text-3xl font-bold text-white">{connection.name}</h1>
            <p className="text-slate-400 text-sm mt-1">{connection.url}</p>
          </div>
        </div>

        <div className="text-right">
          <div className="flex items-center gap-2 justify-end mb-2">
            <div
              className={`w-3 h-3 rounded-full ${
                connection.status === 'connected'
                  ? 'bg-green-500 animate-pulse'
                  : connection.status === 'connecting'
                    ? 'bg-yellow-500 animate-pulse'
                    : 'bg-gray-500'
              }`}
            />
            <span className="text-sm font-semibold capitalize">
              {connection.status === 'connecting' ? 'Connecting...' : connection.status}
            </span>
          </div>
          {connection.lastConnected && (
            <p className="text-xs text-slate-400">
              Last connected: {formatTime(connection.lastConnected)}
            </p>
          )}
        </div>
      </motion.div>

      {/* Connection Status */}
      {isConnecting && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4 flex items-center gap-3"
        >
          <div className="w-4 h-4 border-2 border-yellow-500/30 border-t-yellow-500 rounded-full animate-spin" />
          <p className="text-yellow-200 text-sm">Establishing connection to {connection.name}...</p>
        </motion.div>
      )}

      {connection.status === 'connected' && (
        <>
          {/* Metrics Grid */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="grid grid-cols-4 gap-4"
          >
            <MetricsCard
              icon={<Activity size={24} />}
              label="Uptime"
              value={`${metrics.uptime}%`}
              trend="up"
              color="green"
            />
            <MetricsCard
              icon={<Zap size={24} />}
              label="Requests/sec"
              value={metrics.requestsPerSecond.toString()}
              trend="up"
              color="blue"
            />
            <MetricsCard
              icon={<AlertCircle size={24} />}
              label="Error Rate"
              value={`${metrics.errorRate}%`}
              trend={parseFloat(metrics.errorRate) > 2 ? 'down' : 'up'}
              color={parseFloat(metrics.errorRate) > 2 ? 'red' : 'green'}
            />
            <MetricsCard
              icon={<TrendingUp size={24} />}
              label="Latency"
              value={`${metrics.latency}ms`}
              trend="up"
              color="purple"
            />
          </motion.div>

          {/* Logs Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-slate-700/30 border border-slate-600/50 rounded-lg overflow-hidden"
          >
            <div className="px-6 py-4 border-b border-slate-600/50 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white">Live Logs</h2>
              <span className="text-xs bg-blue-500/20 text-blue-300 px-3 py-1 rounded-full">
                {connection.logs.length} logs
              </span>
            </div>

            <LogStream logs={connection.logs} />
          </motion.div>
        </>
      )}

      {connection.status === 'error' && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="bg-red-500/10 border border-red-500/30 rounded-lg p-6 text-center"
        >
          <AlertCircle size={32} className="text-red-400 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-red-300 mb-2">Connection Failed</h3>
          <p className="text-red-200 text-sm">
            Unable to connect to {connection.name}. Please check your credentials and try again.
          </p>
        </motion.div>
      )}
    </div>
  )
}
