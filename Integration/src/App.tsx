import { useState } from 'react'
import { motion } from 'framer-motion'
import Sidebar from './components/Sidebar'
import ConnectionList from './components/ConnectionList'
import AddConnectionModal from './components/AddConnectionModal'
import MonitoringDashboard from './components/MonitoringDashboard'
import { useConnectionStore } from './store/connectionStore'
import { useDummyData } from './hooks/useDummyData'

export default function App() {
  const [showAddModal, setShowAddModal] = useState(false)
  const selectedConnection = useConnectionStore((state) => state.getSelectedConnection())
  
  // Load dummy data on app initialization
  useDummyData()

  return (
    <div className="flex h-screen bg-primary text-slate-100">
      {/* Sidebar */}
      <Sidebar onAddConnection={() => setShowAddModal(true)} />

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-secondary border-b border-slate-700 px-8 py-6"
        >
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-white">ATLAS Integration</h1>
              <p className="text-slate-400 mt-1">Connect and monitor your platforms in real-time</p>
            </div>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setShowAddModal(true)}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-semibold transition-colors"
            >
              + Add Connection
            </motion.button>
          </div>
        </motion.div>

        {/* Content Area */}
        <div className="flex-1 overflow-hidden flex">
          {/* Connections List */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="w-80 border-r border-slate-700 bg-primary overflow-y-auto"
          >
            <ConnectionList />
          </motion.div>

          {/* Monitoring Dashboard or Empty State */}
          <div className="flex-1 overflow-y-auto">
            {selectedConnection ? (
              <MonitoringDashboard connection={selectedConnection} />
            ) : (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="h-full flex items-center justify-center"
              >
                <div className="text-center">
                  <div className="text-6xl mb-4">🔌</div>
                  <h2 className="text-2xl font-bold text-white mb-2">No Connection Selected</h2>
                  <p className="text-slate-400 mb-6">
                    Add a new connection or select one from the list to start monitoring
                  </p>
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => setShowAddModal(true)}
                    className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-semibold transition-colors"
                  >
                    Add Your First Connection
                  </motion.button>
                </div>
              </motion.div>
            )}
          </div>
        </div>
      </div>

      {/* Add Connection Modal */}
      {showAddModal && (
        <AddConnectionModal onClose={() => setShowAddModal(false)} />
      )}
    </div>
  )
}
