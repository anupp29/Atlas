import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { Search } from 'lucide-react'
import { getAllPlatforms } from '../config/platforms'

interface PlatformSelectorProps {
  onSelect: (platformId: string) => void
}

export default function PlatformSelector({ onSelect }: PlatformSelectorProps) {
  const [searchTerm, setSearchTerm] = useState('')
  const platforms = getAllPlatforms()

  const filteredPlatforms = platforms.filter(
    (p) =>
      p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.description.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <div className="space-y-6">
      <div className="relative">
        <Search className="absolute left-3 top-3 text-slate-400" size={20} />
        <input
          type="text"
          placeholder="Search platforms..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full pl-10 pr-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-blue-500 transition-colors"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        {filteredPlatforms.map((platform, index) => (
          <motion.button
            key={platform.id}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: index * 0.05 }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => onSelect(platform.id)}
            className="p-4 rounded-lg border border-slate-600/50 bg-slate-700/30 hover:bg-slate-700/50 hover:border-blue-500/50 transition-all group"
          >
            <div className="text-4xl mb-3 group-hover:scale-110 transition-transform">{platform.icon}</div>
            <h3 className="font-semibold text-white text-left">{platform.name}</h3>
            <p className="text-xs text-slate-400 text-left mt-1">{platform.description}</p>
          </motion.button>
        ))}
      </div>

      {filteredPlatforms.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-12"
        >
          <p className="text-slate-400">No platforms found matching "{searchTerm}"</p>
        </motion.div>
      )}
    </div>
  )
}
