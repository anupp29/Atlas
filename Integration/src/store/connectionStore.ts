import { create } from 'zustand'

export interface Connection {
  id: string
  name: string
  platform: 'redis' | 'kubernetes' | 'vercel' | 'database' | 'kafka' | 'elasticsearch' | 'mongodb' | 'postgres'
  url: string
  credentials: Record<string, string>
  status: 'connected' | 'disconnected' | 'connecting' | 'error'
  lastConnected?: Date
  metrics?: {
    uptime: number
    requestsPerSecond: number
    errorRate: number
    latency: number
  }
  logs: LogEntry[]
}

export interface LogEntry {
  id: string
  timestamp: Date
  level: 'info' | 'warning' | 'error' | 'debug'
  message: string
  source: string
}

interface ConnectionStore {
  connections: Connection[]
  selectedConnectionId: string | null
  addConnection: (connection: Omit<Connection, 'id' | 'status' | 'logs'>) => void
  removeConnection: (id: string) => void
  updateConnection: (id: string, updates: Partial<Connection>) => void
  selectConnection: (id: string) => void
  addLog: (connectionId: string, log: Omit<LogEntry, 'id'>) => void
  updateConnectionStatus: (id: string, status: Connection['status']) => void
  getSelectedConnection: () => Connection | undefined
}

export const useConnectionStore = create<ConnectionStore>((set, get) => ({
  connections: [],
  selectedConnectionId: null,

  addConnection: (connection) => {
    const newConnection: Connection = {
      ...connection,
      id: `conn_${Date.now()}`,
      status: 'disconnected',
      logs: [],
    }
    set((state) => ({
      connections: [...state.connections, newConnection],
      selectedConnectionId: newConnection.id,
    }))
  },

  removeConnection: (id) => {
    set((state) => ({
      connections: state.connections.filter((c) => c.id !== id),
      selectedConnectionId: state.selectedConnectionId === id ? null : state.selectedConnectionId,
    }))
  },

  updateConnection: (id, updates) => {
    set((state) => ({
      connections: state.connections.map((c) =>
        c.id === id ? { ...c, ...updates } : c
      ),
    }))
  },

  selectConnection: (id) => {
    set({ selectedConnectionId: id })
  },

  addLog: (connectionId, log) => {
    set((state) => ({
      connections: state.connections.map((c) =>
        c.id === connectionId
          ? {
              ...c,
              logs: [
                { ...log, id: `log_${Date.now()}` },
                ...c.logs.slice(0, 999), // Keep last 1000 logs
              ],
            }
          : c
      ),
    }))
  },

  updateConnectionStatus: (id, status) => {
    set((state) => ({
      connections: state.connections.map((c) =>
        c.id === id
          ? {
              ...c,
              status,
              lastConnected: status === 'connected' ? new Date() : c.lastConnected,
            }
          : c
      ),
    }))
  },

  getSelectedConnection: () => {
    const state = get()
    return state.connections.find((c) => c.id === state.selectedConnectionId)
  },
}))
