export const formatDate = (date: Date): string => {
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(date)
}

export const formatTime = (date: Date): string => {
  return new Intl.DateTimeFormat('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(date)
}

export const getStatusColor = (status: string): string => {
  switch (status) {
    case 'connected':
      return 'text-green-400'
    case 'connecting':
      return 'text-yellow-400'
    case 'disconnected':
      return 'text-gray-400'
    case 'error':
      return 'text-red-400'
    default:
      return 'text-gray-400'
  }
}

export const getStatusBgColor = (status: string): string => {
  switch (status) {
    case 'connected':
      return 'bg-green-500/10 border-green-500/30'
    case 'connecting':
      return 'bg-yellow-500/10 border-yellow-500/30'
    case 'disconnected':
      return 'bg-gray-500/10 border-gray-500/30'
    case 'error':
      return 'bg-red-500/10 border-red-500/30'
    default:
      return 'bg-gray-500/10 border-gray-500/30'
  }
}

export const getLogLevelColor = (level: string): string => {
  switch (level) {
    case 'error':
      return 'text-red-400'
    case 'warning':
      return 'text-yellow-400'
    case 'info':
      return 'text-blue-400'
    case 'debug':
      return 'text-gray-400'
    default:
      return 'text-gray-400'
  }
}

export const getLogLevelBgColor = (level: string): string => {
  switch (level) {
    case 'error':
      return 'bg-red-500/10'
    case 'warning':
      return 'bg-yellow-500/10'
    case 'info':
      return 'bg-blue-500/10'
    case 'debug':
      return 'bg-gray-500/10'
    default:
      return 'bg-gray-500/10'
  }
}

export const truncateString = (str: string, length: number): string => {
  return str.length > length ? str.substring(0, length) + '...' : str
}

export const generateMockMetrics = () => {
  return {
    uptime: Math.floor(Math.random() * 99) + 1,
    requestsPerSecond: Math.floor(Math.random() * 1000) + 100,
    errorRate: (Math.random() * 5).toFixed(2),
    latency: Math.floor(Math.random() * 500) + 10,
  }
}

export const generateMockLog = (source: string) => {
  const levels: Array<'info' | 'warning' | 'error' | 'debug'> = ['info', 'warning', 'error', 'debug']
  const messages = [
    'Request processed successfully',
    'Cache hit for key: user_123',
    'Connection pool at 85% capacity',
    'Slow query detected: 2.5s',
    'Memory usage: 2.4GB / 4GB',
    'Replication lag: 150ms',
    'Index rebuild in progress',
    'Backup completed successfully',
    'Connection timeout detected',
    'Authentication failed for user',
  ]

  return {
    timestamp: new Date(),
    level: levels[Math.floor(Math.random() * levels.length)],
    message: messages[Math.floor(Math.random() * messages.length)],
    source,
  }
}
