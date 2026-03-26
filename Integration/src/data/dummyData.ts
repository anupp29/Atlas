import { Connection, LogEntry } from '../store/connectionStore'

// Dummy log entries for testing
const generateDummyLogs = (count: number, source: string): LogEntry[] => {
  const logMessages = {
    redis: [
      'Connection established to Redis cluster',
      'Cache hit for key: user_session_123',
      'Memory usage: 2.4GB / 4GB (60%)',
      'Eviction triggered: 150 keys removed',
      'Replication lag: 45ms',
      'Slow command detected: KEYS * (1.2s)',
      'Connection pool at 85% capacity',
      'Backup completed successfully',
      'AOF rewrite in progress',
      'Cluster node sync completed',
    ],
    kubernetes: [
      'Pod deployment-abc123-xyz started',
      'Service nginx-service is healthy',
      'Node memory pressure detected',
      'Pod restart count: 2',
      'Persistent volume claim bound',
      'ConfigMap updated successfully',
      'Ingress rule applied',
      'Resource quota exceeded warning',
      'Cluster autoscaler scaling up',
      'Pod eviction triggered',
    ],
    vercel: [
      'Deployment started for main branch',
      'Build completed in 45 seconds',
      'Functions deployed successfully',
      'Analytics data collected',
      'Edge config updated',
      'Preview deployment created',
      'Production deployment successful',
      'Rollback initiated',
      'Environment variables updated',
      'Domain verification completed',
    ],
    postgres: [
      'Connection pool: 45/100 active',
      'Query executed: SELECT * FROM users (234ms)',
      'Slow query log: UPDATE transactions (1.2s)',
      'Replication lag: 150ms',
      'Checkpoint completed',
      'Autovacuum running on table orders',
      'Index rebuild in progress',
      'Backup started',
      'WAL archiving: 5 files',
      'Lock detected on table products',
    ],
    mongodb: [
      'Connection established to replica set',
      'Collection users: 15,234 documents',
      'Index created on email field',
      'Aggregation pipeline executed (456ms)',
      'Replication sync completed',
      'Oplog size: 2.5GB',
      'Backup snapshot created',
      'Sharding rebalance started',
      'Query plan cache cleared',
      'Storage engine checkpoint',
    ],
    kafka: [
      'Topic orders: 1,234,567 messages',
      'Consumer group lag: 45 messages',
      'Partition rebalance completed',
      'Broker 1 is healthy',
      'Message retention: 7 days',
      'Compression ratio: 65%',
      'Producer batch size: 16KB',
      'Consumer offset committed',
      'Topic configuration updated',
      'Broker disk usage: 78%',
    ],
    elasticsearch: [
      'Index created: logs-2024-01-15',
      'Shard allocation completed',
      'Query executed in 234ms',
      'Bulk indexing: 10,000 documents',
      'Cluster health: GREEN',
      'Node memory: 8.5GB / 16GB',
      'Segment merge in progress',
      'Snapshot backup completed',
      'Index refresh completed',
      'Fielddata cache: 2.3GB',
    ],
    database: [
      'Connection established successfully',
      'Query executed: SELECT COUNT(*) (123ms)',
      'Transaction committed',
      'Backup completed',
      'Index optimization running',
      'Database size: 45.6GB',
      'Active connections: 23',
      'Slow query detected',
      'Maintenance task completed',
      'Data integrity check passed',
    ],
  }

  const messages = logMessages[source as keyof typeof logMessages] || logMessages.database
  const logs: LogEntry[] = []
  const levels: Array<'info' | 'warning' | 'error' | 'debug'> = ['info', 'warning', 'error', 'debug']

  for (let i = 0; i < count; i++) {
    logs.push({
      id: `log_${Date.now()}_${i}`,
      timestamp: new Date(Date.now() - (count - i) * 2000),
      level: levels[Math.floor(Math.random() * levels.length)],
      message: messages[Math.floor(Math.random() * messages.length)],
      source,
    })
  }

  return logs
}

// Dummy connections for testing
export const DUMMY_CONNECTIONS: Connection[] = [
  {
    id: 'conn_redis_prod',
    name: 'Production Redis',
    platform: 'redis',
    url: 'redis://redis-prod.example.com:6379',
    credentials: {
      host: 'redis-prod.example.com',
      port: '6379',
      password: '••••••••',
      database: '0',
    },
    status: 'connected',
    lastConnected: new Date(Date.now() - 5 * 60000),
    metrics: {
      uptime: 99.8,
      requestsPerSecond: 1250,
      errorRate: 0.2,
      latency: 2,
    },
    logs: generateDummyLogs(15, 'redis'),
  },
  {
    id: 'conn_k8s_staging',
    name: 'Staging Kubernetes',
    platform: 'kubernetes',
    url: 'https://k8s-staging.example.com:6443',
    credentials: {
      apiServer: 'https://k8s-staging.example.com:6443',
      token: '••••••••••••••••',
      namespace: 'staging',
      caCert: '••••••••',
    },
    status: 'connected',
    lastConnected: new Date(Date.now() - 10 * 60000),
    metrics: {
      uptime: 98.5,
      requestsPerSecond: 450,
      errorRate: 0.5,
      latency: 45,
    },
    logs: generateDummyLogs(12, 'kubernetes'),
  },
  {
    id: 'conn_vercel_main',
    name: 'Vercel Production',
    platform: 'vercel',
    url: 'https://api.vercel.com',
    credentials: {
      apiToken: '••••••••••••••••',
      teamId: 'team_abc123',
      projectId: 'prj_xyz789',
    },
    status: 'connected',
    lastConnected: new Date(Date.now() - 2 * 60000),
    metrics: {
      uptime: 99.95,
      requestsPerSecond: 2340,
      errorRate: 0.1,
      latency: 12,
    },
    logs: generateDummyLogs(18, 'vercel'),
  },
  {
    id: 'conn_postgres_main',
    name: 'Main PostgreSQL',
    platform: 'postgres',
    url: 'postgresql://db-prod.example.com:5432/maindb',
    credentials: {
      host: 'db-prod.example.com',
      port: '5432',
      username: 'postgres',
      password: '••••••••',
      database: 'maindb',
    },
    status: 'connected',
    lastConnected: new Date(Date.now() - 1 * 60000),
    metrics: {
      uptime: 99.9,
      requestsPerSecond: 890,
      errorRate: 0.3,
      latency: 8,
    },
    logs: generateDummyLogs(20, 'postgres'),
  },
  {
    id: 'conn_mongodb_analytics',
    name: 'Analytics MongoDB',
    platform: 'mongodb',
    url: 'mongodb+srv://analytics.example.com',
    credentials: {
      connectionString: '••••••••••••••••••••••••••••••••',
      database: 'analytics',
      collections: 'events,sessions,users',
    },
    status: 'connected',
    lastConnected: new Date(Date.now() - 3 * 60000),
    metrics: {
      uptime: 99.7,
      requestsPerSecond: 567,
      errorRate: 0.4,
      latency: 15,
    },
    logs: generateDummyLogs(14, 'mongodb'),
  },
  {
    id: 'conn_kafka_events',
    name: 'Event Kafka Cluster',
    platform: 'kafka',
    url: 'kafka-broker-1.example.com:9092',
    credentials: {
      brokers: 'kafka-broker-1.example.com:9092,kafka-broker-2.example.com:9092',
      groupId: 'atlas-monitoring',
      topics: 'events,logs,metrics',
      saslUsername: 'kafka_user',
      saslPassword: '••••••••',
    },
    status: 'connected',
    lastConnected: new Date(Date.now() - 7 * 60000),
    metrics: {
      uptime: 99.6,
      requestsPerSecond: 3450,
      errorRate: 0.2,
      latency: 5,
    },
    logs: generateDummyLogs(16, 'kafka'),
  },
  {
    id: 'conn_elasticsearch_logs',
    name: 'Elasticsearch Logs',
    platform: 'elasticsearch',
    url: 'https://es-prod.example.com:9200',
    credentials: {
      host: 'es-prod.example.com',
      port: '9200',
      username: 'elastic',
      password: '••••••••',
      indices: 'logs-*,metrics-*',
    },
    status: 'connected',
    lastConnected: new Date(Date.now() - 4 * 60000),
    metrics: {
      uptime: 99.8,
      requestsPerSecond: 1890,
      errorRate: 0.15,
      latency: 18,
    },
    logs: generateDummyLogs(17, 'elasticsearch'),
  },
  {
    id: 'conn_db_backup',
    name: 'Backup Database',
    platform: 'database',
    url: 'mysql://backup-db.example.com:3306/backups',
    credentials: {
      type: 'mysql',
      host: 'backup-db.example.com',
      port: '3306',
      username: 'backup_user',
      password: '••••••••',
      database: 'backups',
    },
    status: 'connected',
    lastConnected: new Date(Date.now() - 6 * 60000),
    metrics: {
      uptime: 99.5,
      requestsPerSecond: 234,
      errorRate: 0.6,
      latency: 25,
    },
    logs: generateDummyLogs(13, 'database'),
  },
]

// Additional dummy connections with different statuses
export const ADDITIONAL_DUMMY_CONNECTIONS: Connection[] = [
  {
    id: 'conn_redis_dev',
    name: 'Development Redis',
    platform: 'redis',
    url: 'redis://localhost:6379',
    credentials: {
      host: 'localhost',
      port: '6379',
      password: '',
      database: '0',
    },
    status: 'disconnected',
    logs: [],
  },
  {
    id: 'conn_k8s_dev',
    name: 'Local Kubernetes',
    platform: 'kubernetes',
    url: 'https://localhost:6443',
    credentials: {
      apiServer: 'https://localhost:6443',
      token: 'dev_token_xxx',
      namespace: 'default',
      caCert: '',
    },
    status: 'error',
    logs: [
      {
        id: 'log_error_1',
        timestamp: new Date(),
        level: 'error',
        message: 'Connection refused: Unable to connect to API server',
        source: 'Kubernetes',
      },
    ],
  },
]

// Function to load dummy data into store
export const loadDummyData = () => {
  return DUMMY_CONNECTIONS
}

// Function to get a specific dummy connection
export const getDummyConnection = (id: string): Connection | undefined => {
  return DUMMY_CONNECTIONS.find((conn) => conn.id === id)
}

// Function to get all dummy connections
export const getAllDummyConnections = (): Connection[] => {
  return DUMMY_CONNECTIONS
}

// Function to generate random metrics
export const generateRandomMetrics = () => {
  return {
    uptime: Math.floor(Math.random() * 5) + 95,
    requestsPerSecond: Math.floor(Math.random() * 3000) + 100,
    errorRate: Math.random() * 2,
    latency: Math.floor(Math.random() * 100) + 1,
  }
}

// Function to generate random log
export const generateRandomLog = (source: string): LogEntry => {
  const levels: Array<'info' | 'warning' | 'error' | 'debug'> = ['info', 'warning', 'error', 'debug']
  const messages = [
    'Operation completed successfully',
    'Resource utilization at 85%',
    'Connection pool updated',
    'Cache invalidated',
    'Backup in progress',
    'Replication lag detected',
    'Performance degradation warning',
    'Maintenance task started',
    'Configuration updated',
    'Health check passed',
  ]

  return {
    id: `log_${Date.now()}`,
    timestamp: new Date(),
    level: levels[Math.floor(Math.random() * levels.length)],
    message: messages[Math.floor(Math.random() * messages.length)],
    source,
  }
}
