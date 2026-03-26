export interface PlatformConfig {
  id: string
  name: string
  icon: string
  color: string
  description: string
  credentials: CredentialField[]
  defaultPort?: number
  urlPattern?: string
}

export interface CredentialField {
  name: string
  label: string
  type: 'text' | 'password' | 'number'
  required: boolean
  placeholder?: string
  help?: string
}

export const PLATFORMS: Record<string, PlatformConfig> = {
  redis: {
    id: 'redis',
    name: 'Redis',
    icon: '⚡',
    color: '#DC382D',
    description: 'In-memory data structure store',
    defaultPort: 6379,
    urlPattern: 'redis://host:port',
    credentials: [
      {
        name: 'host',
        label: 'Host',
        type: 'text',
        required: true,
        placeholder: 'localhost',
        help: 'Redis server hostname or IP',
      },
      {
        name: 'port',
        label: 'Port',
        type: 'number',
        required: true,
        placeholder: '6379',
        help: 'Redis server port',
      },
      {
        name: 'password',
        label: 'Password',
        type: 'password',
        required: false,
        placeholder: 'Leave empty if no auth',
        help: 'Redis password (optional)',
      },
      {
        name: 'database',
        label: 'Database',
        type: 'number',
        required: false,
        placeholder: '0',
        help: 'Database number (0-15)',
      },
    ],
  },
  kubernetes: {
    id: 'kubernetes',
    name: 'Kubernetes',
    icon: '☸️',
    color: '#326CE5',
    description: 'Container orchestration platform',
    credentials: [
      {
        name: 'apiServer',
        label: 'API Server URL',
        type: 'text',
        required: true,
        placeholder: 'https://kubernetes.default.svc',
        help: 'Kubernetes API server endpoint',
      },
      {
        name: 'token',
        label: 'Bearer Token',
        type: 'password',
        required: true,
        placeholder: 'Your service account token',
        help: 'Kubernetes service account token',
      },
      {
        name: 'namespace',
        label: 'Namespace',
        type: 'text',
        required: false,
        placeholder: 'default',
        help: 'Kubernetes namespace to monitor',
      },
      {
        name: 'caCert',
        label: 'CA Certificate',
        type: 'text',
        required: false,
        placeholder: 'Base64 encoded CA cert',
        help: 'CA certificate for TLS verification',
      },
    ],
  },
  vercel: {
    id: 'vercel',
    name: 'Vercel',
    icon: '▲',
    color: '#000000',
    description: 'Serverless platform for frontend',
    credentials: [
      {
        name: 'apiToken',
        label: 'API Token',
        type: 'password',
        required: true,
        placeholder: 'Your Vercel API token',
        help: 'Get from https://vercel.com/account/tokens',
      },
      {
        name: 'teamId',
        label: 'Team ID',
        type: 'text',
        required: false,
        placeholder: 'Optional team ID',
        help: 'Vercel team ID (optional)',
      },
      {
        name: 'projectId',
        label: 'Project ID',
        type: 'text',
        required: false,
        placeholder: 'Project ID to monitor',
        help: 'Specific project to monitor',
      },
    ],
  },
  database: {
    id: 'database',
    name: 'Database',
    icon: '🗄️',
    color: '#336791',
    description: 'SQL/NoSQL database connection',
    credentials: [
      {
        name: 'type',
        label: 'Database Type',
        type: 'text',
        required: true,
        placeholder: 'postgres, mysql, mongodb',
        help: 'Type of database',
      },
      {
        name: 'host',
        label: 'Host',
        type: 'text',
        required: true,
        placeholder: 'localhost',
        help: 'Database server hostname',
      },
      {
        name: 'port',
        label: 'Port',
        type: 'number',
        required: true,
        placeholder: '5432',
        help: 'Database server port',
      },
      {
        name: 'username',
        label: 'Username',
        type: 'text',
        required: true,
        placeholder: 'admin',
        help: 'Database username',
      },
      {
        name: 'password',
        label: 'Password',
        type: 'password',
        required: true,
        placeholder: 'Your password',
        help: 'Database password',
      },
      {
        name: 'database',
        label: 'Database Name',
        type: 'text',
        required: true,
        placeholder: 'mydb',
        help: 'Database name to connect to',
      },
    ],
  },
  kafka: {
    id: 'kafka',
    name: 'Apache Kafka',
    icon: '📨',
    color: '#231F20',
    description: 'Event streaming platform',
    defaultPort: 9092,
    credentials: [
      {
        name: 'brokers',
        label: 'Brokers',
        type: 'text',
        required: true,
        placeholder: 'localhost:9092,localhost:9093',
        help: 'Comma-separated list of broker addresses',
      },
      {
        name: 'groupId',
        label: 'Consumer Group ID',
        type: 'text',
        required: true,
        placeholder: 'atlas-monitoring',
        help: 'Kafka consumer group ID',
      },
      {
        name: 'topics',
        label: 'Topics',
        type: 'text',
        required: false,
        placeholder: 'topic1,topic2',
        help: 'Comma-separated topics to monitor',
      },
      {
        name: 'saslUsername',
        label: 'SASL Username',
        type: 'text',
        required: false,
        placeholder: 'Optional SASL username',
        help: 'For SASL authentication',
      },
      {
        name: 'saslPassword',
        label: 'SASL Password',
        type: 'password',
        required: false,
        placeholder: 'Optional SASL password',
        help: 'For SASL authentication',
      },
    ],
  },
  elasticsearch: {
    id: 'elasticsearch',
    name: 'Elasticsearch',
    icon: '🔍',
    color: '#005571',
    description: 'Search and analytics engine',
    defaultPort: 9200,
    credentials: [
      {
        name: 'host',
        label: 'Host',
        type: 'text',
        required: true,
        placeholder: 'localhost',
        help: 'Elasticsearch server hostname',
      },
      {
        name: 'port',
        label: 'Port',
        type: 'number',
        required: true,
        placeholder: '9200',
        help: 'Elasticsearch server port',
      },
      {
        name: 'username',
        label: 'Username',
        type: 'text',
        required: false,
        placeholder: 'elastic',
        help: 'Elasticsearch username',
      },
      {
        name: 'password',
        label: 'Password',
        type: 'password',
        required: false,
        placeholder: 'Your password',
        help: 'Elasticsearch password',
      },
      {
        name: 'indices',
        label: 'Indices',
        type: 'text',
        required: false,
        placeholder: 'index1,index2',
        help: 'Comma-separated indices to monitor',
      },
    ],
  },
  mongodb: {
    id: 'mongodb',
    name: 'MongoDB',
    icon: '🍃',
    color: '#13AA52',
    description: 'NoSQL document database',
    credentials: [
      {
        name: 'connectionString',
        label: 'Connection String',
        type: 'password',
        required: true,
        placeholder: 'mongodb://user:pass@host:port/db',
        help: 'MongoDB connection string',
      },
      {
        name: 'database',
        label: 'Database Name',
        type: 'text',
        required: true,
        placeholder: 'mydb',
        help: 'Database to monitor',
      },
      {
        name: 'collections',
        label: 'Collections',
        type: 'text',
        required: false,
        placeholder: 'collection1,collection2',
        help: 'Comma-separated collections to monitor',
      },
    ],
  },
  postgres: {
    id: 'postgres',
    name: 'PostgreSQL',
    icon: '🐘',
    color: '#336791',
    description: 'Advanced open-source database',
    defaultPort: 5432,
    credentials: [
      {
        name: 'host',
        label: 'Host',
        type: 'text',
        required: true,
        placeholder: 'localhost',
        help: 'PostgreSQL server hostname',
      },
      {
        name: 'port',
        label: 'Port',
        type: 'number',
        required: true,
        placeholder: '5432',
        help: 'PostgreSQL server port',
      },
      {
        name: 'username',
        label: 'Username',
        type: 'text',
        required: true,
        placeholder: 'postgres',
        help: 'PostgreSQL username',
      },
      {
        name: 'password',
        label: 'Password',
        type: 'password',
        required: true,
        placeholder: 'Your password',
        help: 'PostgreSQL password',
      },
      {
        name: 'database',
        label: 'Database Name',
        type: 'text',
        required: true,
        placeholder: 'mydb',
        help: 'Database name to connect to',
      },
    ],
  },
}

export const getPlatformConfig = (platformId: string): PlatformConfig | undefined => {
  return PLATFORMS[platformId]
}

export const getAllPlatforms = (): PlatformConfig[] => {
  return Object.values(PLATFORMS)
}
