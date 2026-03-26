import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { ChevronRight, AlertCircle } from 'lucide-react'
import { getPlatformConfig } from '../config/platforms'

interface CredentialsFormProps {
  platform: string
  onSubmit: (credentials: Record<string, string>, name: string, url: string) => void
  onBack: () => void
}

export default function CredentialsForm({ platform, onSubmit, onBack }: CredentialsFormProps) {
  const platformConfig = getPlatformConfig(platform)
  const [connectionName, setConnectionName] = useState(`${platformConfig?.name} Connection`)
  const [connectionUrl, setConnectionUrl] = useState('')
  const [credentials, setCredentials] = useState<Record<string, string>>({})
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [isValidating, setIsValidating] = useState(false)

  const handleCredentialChange = (fieldName: string, value: string) => {
    setCredentials((prev) => ({
      ...prev,
      [fieldName]: value,
    }))
    // Clear error for this field
    if (errors[fieldName]) {
      setErrors((prev) => {
        const newErrors = { ...prev }
        delete newErrors[fieldName]
        return newErrors
      })
    }
  }

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!connectionName.trim()) {
      newErrors.name = 'Connection name is required'
    }

    if (!connectionUrl.trim()) {
      newErrors.url = 'Connection URL is required'
    }

    if (platformConfig) {
      platformConfig.credentials.forEach((field) => {
        if (field.required && !credentials[field.name]?.trim()) {
          newErrors[field.name] = `${field.label} is required`
        }
      })
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateForm()) {
      return
    }

    setIsValidating(true)
    // Simulate connection validation
    await new Promise((resolve) => setTimeout(resolve, 1500))
    setIsValidating(false)

    onSubmit(credentials, connectionName, connectionUrl)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Platform Info */}
      <div className="flex items-center gap-3 p-4 bg-slate-700/30 border border-slate-600/50 rounded-lg">
        <span className="text-3xl">{platformConfig?.icon}</span>
        <div>
          <h3 className="font-semibold text-white">{platformConfig?.name}</h3>
          <p className="text-sm text-slate-400">{platformConfig?.description}</p>
        </div>
      </div>

      {/* Connection Name */}
      <div>
        <label className="block text-sm font-semibold text-white mb-2">Connection Name</label>
        <input
          type="text"
          value={connectionName}
          onChange={(e) => setConnectionName(e.target.value)}
          placeholder="e.g., Production Redis"
          className={`w-full px-4 py-2 bg-slate-700/50 border rounded-lg text-white placeholder-slate-400 focus:outline-none transition-colors ${
            errors.name ? 'border-red-500' : 'border-slate-600 focus:border-blue-500'
          }`}
        />
        {errors.name && <p className="text-red-400 text-sm mt-1">{errors.name}</p>}
      </div>

      {/* Connection URL */}
      <div>
        <label className="block text-sm font-semibold text-white mb-2">Connection URL</label>
        <input
          type="text"
          value={connectionUrl}
          onChange={(e) => setConnectionUrl(e.target.value)}
          placeholder={platformConfig?.urlPattern || 'e.g., redis://localhost:6379'}
          className={`w-full px-4 py-2 bg-slate-700/50 border rounded-lg text-white placeholder-slate-400 focus:outline-none transition-colors ${
            errors.url ? 'border-red-500' : 'border-slate-600 focus:border-blue-500'
          }`}
        />
        {errors.url && <p className="text-red-400 text-sm mt-1">{errors.url}</p>}
        <p className="text-xs text-slate-400 mt-1">
          {platformConfig?.urlPattern && `Format: ${platformConfig.urlPattern}`}
        </p>
      </div>

      {/* Credentials */}
      <div className="space-y-4">
        <h3 className="font-semibold text-white">Credentials</h3>

        {platformConfig?.credentials.map((field, index) => (
          <motion.div
            key={field.name}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
          >
            <label className="block text-sm font-medium text-white mb-2">
              {field.label}
              {field.required && <span className="text-red-400 ml-1">*</span>}
            </label>
            <input
              type={field.type}
              value={credentials[field.name] || ''}
              onChange={(e) => handleCredentialChange(field.name, e.target.value)}
              placeholder={field.placeholder}
              className={`w-full px-4 py-2 bg-slate-700/50 border rounded-lg text-white placeholder-slate-400 focus:outline-none transition-colors ${
                errors[field.name] ? 'border-red-500' : 'border-slate-600 focus:border-blue-500'
              }`}
            />
            {field.help && <p className="text-xs text-slate-400 mt-1">{field.help}</p>}
            {errors[field.name] && <p className="text-red-400 text-sm mt-1">{errors[field.name]}</p>}
          </motion.div>
        ))}
      </div>

      {/* Security Notice */}
      <div className="flex gap-3 p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
        <AlertCircle size={20} className="text-blue-400 flex-shrink-0 mt-0.5" />
        <p className="text-sm text-blue-200">
          Your credentials are encrypted and stored securely. They are never logged or exposed.
        </p>
      </div>

      {/* Actions */}
      <div className="flex gap-3 pt-4">
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          type="button"
          onClick={onBack}
          className="flex-1 px-4 py-2 border border-slate-600 rounded-lg text-white hover:bg-slate-700/50 transition-colors"
        >
          Back
        </motion.button>
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          type="submit"
          disabled={isValidating}
          className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 rounded-lg text-white font-semibold transition-colors flex items-center justify-center gap-2"
        >
          {isValidating ? (
            <>
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Validating...
            </>
          ) : (
            <>
              Next
              <ChevronRight size={18} />
            </>
          )}
        </motion.button>
      </div>
    </form>
  )
}
