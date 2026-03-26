import React from 'react'
import { motion } from 'framer-motion'
import { Plus, Settings, HelpCircle } from 'lucide-react'

interface SidebarProps {
  onAddConnection: () => void
}

export default function Sidebar({ onAddConnection }: SidebarProps) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -50 }}
      animate={{ opacity: 1, x: 0 }}
      className="w-64 bg-secondary border-r border-slate-700 flex flex-col"
    >
      {/* Logo */}
      <div className="p-6 border-b border-slate-700">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-lg">A</span>
          </div>
          <div>
            <h1 className="font-bold text-white">ATLAS</h1>
            <p className="text-xs text-slate-400">Integration Hub</p>
          </div>
        </div>
      </div>

      {/* Main Navigation */}
      <div className="flex-1 overflow-y-auto p-4">
        <nav className="space-y-2">
          <motion.button
            whileHover={{ x: 4 }}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-lg bg-blue-600/20 border border-blue-500/30 text-blue-400 hover:bg-blue-600/30 transition-colors"
          >
            <span className="text-lg">🔌</span>
            <span className="font-semibold">Connections</span>
          </motion.button>

          <motion.button
            whileHover={{ x: 4 }}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-slate-400 hover:bg-slate-700/50 transition-colors"
          >
            <span className="text-lg">📊</span>
            <span className="font-semibold">Analytics</span>
          </motion.button>

          <motion.button
            whileHover={{ x: 4 }}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-slate-400 hover:bg-slate-700/50 transition-colors"
          >
            <span className="text-lg">⚙️</span>
            <span className="font-semibold">Settings</span>
          </motion.button>
        </nav>
      </div>

      {/* Bottom Actions */}
      <div className="border-t border-slate-700 p-4 space-y-2">
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={onAddConnection}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-semibold transition-colors"
        >
          <Plus size={18} />
          New Connection
        </motion.button>

        <div className="flex gap-2">
          <motion.button
            whileHover={{ scale: 1.05 }}
            className="flex-1 flex items-center justify-center p-2 rounded-lg text-slate-400 hover:bg-slate-700/50 transition-colors"
          >
            <Settings size={18} />
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.05 }}
            className="flex-1 flex items-center justify-center p-2 rounded-lg text-slate-400 hover:bg-slate-700/50 transition-colors"
          >
            <HelpCircle size={18} />
          </motion.button>
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-slate-700 p-4 text-center text-xs text-slate-500">
        <p>v1.0.0</p>
        <p className="mt-1">© 2024 ATLAS</p>
      </div>
    </motion.div>
  )
}
