import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, ChevronRight } from 'lucide-react'
import { useConnectionStore } from '../store/connectionStore'
import { getAllPlatforms, getPlatformConfig } from '../config/platforms'
import PlatformSelector from './PlatformSelector'
import CredentialsForm from './CredentialsForm'

interface AddConnectionModalProps {
  onClose: () => void
}

type Step = 'platform' | 'credentials' | 'confirm'

export default function AddConnectionModal({ onClose }: AddConnectionModalProps) {
  const [step, setStep] = useState<Step>('platform')
  const [selectedPlatform, setSelectedPlatform] = useState<string | null>(null)
  const [connectionName, setConnectionName] = useState('')
  const [connectionUrl, setConnectionUrl] = useState('')
  const [credentials, setCredentials] = useState<Record<string, string>>({})
  const addConnection = useConnectionStore((state) => state.addConnection)

  const handlePlatformSelect = (platformId: string) => {
    setSelectedPlatform(platformId)
    setStep('credentials')
  }

  const handleCredentialsSubmit = (creds: Record<string, string>, name: string, url: string) => {
    setCredentials(creds)
    setConnectionName(name)
    setConnectionUrl(url)
    setStep('confirm')
  }

  const handleConfirm = () => {
    if (selectedPlatform && connectionName && connectionUrl) {
      addConnection({
        name: connectionName,
        platform: selectedPlatform as any,
        url: connectionUrl,
        credentials,
      })
      onClose()
    }
  }

  const handleBack = () => {
    if (step === 'credentials') {
      setStep('platform')
      setSelectedPlatform(null)
    } else if (step === 'confirm') {
      setStep('credentials')
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-secondary rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col"
      >
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 px-8 py-6 flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white">Add New Connection</h2>
            <p className="text-blue-100 text-sm mt-1">
              {step === 'platform' && 'Select a platform to connect'}
              {step === 'credentials' && 'Enter your credentials'}
              {step === 'confirm' && 'Review and confirm'}
            </p>
          </div>
          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            onClick={onClose}
            className="p-2 hover:bg-white/20 rounded-lg transition-colors"
          >
            <X size={24} className="text-white" />
          </motion.button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-8">
          <AnimatePresence mode="wait">
            {step === 'platform' && (
              <motion.div
                key="platform"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
              >
                <PlatformSelector onSelect={handlePlatformSelect} />
              </motion.div>
            )}

            {step === 'credentials' && selectedPlatform && (
              <motion.div
                key="credentials"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
              >
                <CredentialsForm
                  platform={selectedPlatform}
                  onSubmit={handleCredentialsSubmit}
                  onBack={handleBack}
                />
              </motion.div>
            )}

            {step === 'confirm' && (
              <motion.div
                key="confirm"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
              >
                <ConfirmStep
                  platform={selectedPlatform!}
                  name={connectionName}
                  url={connectionUrl}
                  credentials={credentials}
                  onConfirm={handleConfirm}
                  onBack={handleBack}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </motion.div>
  )
}

function ConfirmStep({
  platform,
  name,
  url,
  credentials,
  onConfirm,
  onBack,
}: {
  platform: string
  name: string
  url: string
  credentials: Record<string, string>
  onConfirm: () => void
  onBack: () => void
}) {
  const platformConfig = getPlatformConfig(platform)

  return (
    <div className="space-y-6">
      <div className="bg-slate-700/30 border border-slate-600/50 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Connection Details</h3>

        <div className="space-y-4">
          <div>
            <label className="text-sm text-slate-400">Platform</label>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-2xl">{platformConfig?.icon}</span>
              <p className="text-white font-semibold">{platformConfig?.name}</p>
            </div>
          </div>

          <div>
            <label className="text-sm text-slate-400">Connection Name</label>
            <p className="text-white font-semibold mt-1">{name}</p>
          </div>

          <div>
            <label className="text-sm text-slate-400">URL</label>
            <p className="text-white font-mono text-sm mt-1 break-all">{url}</p>
          </div>

          <div>
            <label className="text-sm text-slate-400 mb-2 block">Credentials</label>
            <div className="space-y-2">
              {Object.entries(credentials).map(([key, value]) => (
                <div key={key} className="flex justify-between items-center text-sm">
                  <span className="text-slate-400 capitalize">{key}:</span>
                  <span className="text-white font-mono">
                    {key.toLowerCase().includes('password') ? '••••••••' : value}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
        <p className="text-sm text-blue-200">
          ✓ Your credentials are encrypted and stored securely. ATLAS will now start monitoring this platform.
        </p>
      </div>

      <div className="flex gap-3">
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={onBack}
          className="flex-1 px-4 py-2 border border-slate-600 rounded-lg text-white hover:bg-slate-700/50 transition-colors"
        >
          Back
        </motion.button>
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={onConfirm}
          className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg text-white font-semibold transition-colors flex items-center justify-center gap-2"
        >
          Connect & Monitor
          <ChevronRight size={18} />
        </motion.button>
      </div>
    </div>
  )
}
