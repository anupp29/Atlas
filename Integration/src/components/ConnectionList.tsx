import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Trash2, Circle } from 'lucide-react'
import { useConnectionStore } from '../store/connectionStore'
import { getPlatformConfig } from '../config/platforms'
import { getStatusColor, getStatusBgColor } from '../utils/helpers'

export default function ConnectionList() {
  const connections = useConnectionStore((state) => state.connections)
  const selectedConnectionId = useConnectionStore((state) => state.selectedConnectionId)
  const selectConnection = useConnectionStore((state) => state.selectConnection)
  const removeConnection = useConnectionStore((state) => state.removeConnection)

  return (
    <div className="p-4 space-y-2">
      <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider px-2 mb-4">
        Connections ({connections.length})
      </h2>

      <AnimatePresence>
        {connections.length === 0 ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="text-center py-8 text-slate-500"
          >
            <p className="text-sm">No connections yet</p>
            <p className="text-xs mt-1">Add one to get started</p>
          </motion.div>
        ) : (
          connections.map((connection, index) => {
            const platform = getPlatformConfig(connection.platform)
            const isSelected = connection.id === selectedConnectionId

            return (
              <motion.div
                key={connection.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ delay: index * 0.05 }}
                onClick={() => selectConnection(connection.id)}
                className={`p-3 rounded-lg cursor-pointer transition-all ${
                  isSelected
                    ? 'bg-blue-600/20 border border-blue-500/50'
                    : 'bg-slate-700/30 border border-slate-600/30 hover:bg-slate-700/50'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-lg">{platform?.icon}</span>
                      <h3 className="font-semibold text-white truncate">{connection.name}</h3>
                    </div>
                    <p className="text-xs text-slate-400 truncate">{connection.url}</p>
                    <div className="flex items-center gap-2 mt-2">
                      <Circle
                        size={8}
                        className={`fill-current ${getStatusColor(connection.status)}`}
                      />
                      <span className={`text-xs font-medium ${getStatusColor(connection.status)}`}>
                        {connection.status.charAt(0).toUpperCase() + connection.status.slice(1)}
                      </span>
                    </div>
                  </div>

                  <motion.button
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                    onClick={(e) => {
                      e.stopPropagation()
                      removeConnection(connection.id)
                    }}
                    className="p-1 text-slate-400 hover:text-red-400 transition-colors"
                  >
                    <Trash2 size={16} />
                  </motion.button>
                </div>
              </motion.div>
            )
          })
        )}
      </AnimatePresence>
    </div>
  )
}
