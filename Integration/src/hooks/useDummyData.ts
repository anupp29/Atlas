import { useEffect } from 'react'
import { useConnectionStore } from '../store/connectionStore'
import { loadDummyData, generateRandomMetrics, generateRandomLog } from '../data/dummyData'

/**
 * Hook to load and manage dummy data for testing
 * Usage: useDummyData() in your component
 */
export const useDummyData = () => {
  const addConnection = useConnectionStore((state) => state.addConnection)
  const updateConnection = useConnectionStore((state) => state.updateConnection)
  const addLog = useConnectionStore((state) => state.addLog)

  // Load dummy data on mount
  useEffect(() => {
    const dummyConnections = loadDummyData()
    dummyConnections.forEach((conn) => {
      addConnection({
        name: conn.name,
        platform: conn.platform,
        url: conn.url,
        credentials: conn.credentials,
      })
    })
  }, [])

  // Simulate real-time metrics updates
  useEffect(() => {
    const connections = useConnectionStore.getState().connections
    const interval = setInterval(() => {
      connections.forEach((conn) => {
        if (conn.status === 'connected') {
          const newMetrics = generateRandomMetrics()
          updateConnection(conn.id, { metrics: newMetrics })
        }
      })
    }, 3000)

    return () => clearInterval(interval)
  }, [])

  // Simulate real-time log generation
  useEffect(() => {
    const connections = useConnectionStore.getState().connections
    const interval = setInterval(() => {
      connections.forEach((conn) => {
        if (conn.status === 'connected') {
          const newLog = generateRandomLog(conn.name)
          addLog(conn.id, newLog)
        }
      })
    }, 2000)

    return () => clearInterval(interval)
  }, [])

  return {
    loadDummyData,
    generateRandomMetrics,
    generateRandomLog,
  }
}

/**
 * Hook to load dummy data on demand
 * Usage: const { loadData } = useDummyDataOnDemand()
 */
export const useDummyDataOnDemand = () => {
  const addConnection = useConnectionStore((state) => state.addConnection)

  const loadData = () => {
    const dummyConnections = loadDummyData()
    dummyConnections.forEach((conn) => {
      addConnection({
        name: conn.name,
        platform: conn.platform,
        url: conn.url,
        credentials: conn.credentials,
      })
    })
  }

  return { loadData }
}
