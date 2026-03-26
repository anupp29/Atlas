# ATLAS Integration Scripts

Production-grade integration scripts for log monitoring and GitHub repository synchronization.

## Components

### 1. log_monitor.py
Structured log ingestion and monitoring with SQLite persistence.

**Features:**
- Async log ingestion with buffering
- Per-client log isolation
- Structured JSON logging via structlog
- SQLite persistence with indexed queries
- JSONL file export for monitoring systems
- Configurable buffer size and flush intervals

**Environment Variables:**
- `ATLAS_CLIENT_ID` (mandatory): Client identifier
- `ATLAS_LOG_DB`: SQLite database path (default: `data/atlas_logs.db`)
- `ATLAS_LOG_DIR`: Log file directory (default: `data/logs`)

**Usage:**
```python
from log_monitor import LogMonitor, LogSeverity, LogSource

monitor = LogMonitor(
    client_id="FINCORE_UK_001",
    db_path="data/atlas_logs.db",
    log_dir="data/logs"
)

log_id = await monitor.ingest_log(
    source=LogSource.JAVA,
    severity=LogSeverity.ERROR,
    service_name="PaymentAPI",
    message="Connection pool exhausted",
    raw_payload="[2024-03-26 10:15:23] ERROR HikariPool - Connection is not available",
    error_code="CONNECTION_POOL_EXHAUSTED",
    metadata={"pool_size": 40, "active_connections": 40}
)
```

### 2. github_repo_sync.py
GitHub repository file modification with full audit trail.

**Features:**
- Async GitHub API integration
- File read/write/update operations
- Batch file updates
- Pull request creation
- Complete change audit trail in SQLite
- Automatic SHA tracking for concurrent updates

**Environment Variables:**
- `ATLAS_CLIENT_ID` (mandatory): Client identifier
- `GITHUB_TOKEN` (mandatory): GitHub personal access token
- `GITHUB_OWNER` (mandatory): Repository owner
- `GITHUB_REPO` (mandatory): Repository name
- `ATLAS_GITHUB_DB`: SQLite database path (default: `data/atlas_github.db`)

**Usage:**
```python
from github_repo_sync import GitHubRepoSync, GitHubConfig

config = GitHubConfig(
    token="ghp_...",
    owner="myorg",
    repo="myrepo"
)

sync = GitHubRepoSync(
    client_id="FINCORE_UK_001",
    config=config,
    db_path="data/atlas_github.db"
)

commit_sha = await sync.update_file(
    file_path="src/config.py",
    new_content="new_config_content",
    commit_message="ATLAS: Update configuration"
)
```

### 3. integration_orchestrator.py
Unified orchestrator managing both log monitoring and GitHub sync.

**Features:**
- Single entry point for all integrations
- Async task management
- Graceful shutdown
- Unified error handling
- Environment-based configuration

**Environment Variables:**
All variables from log_monitor.py and github_repo_sync.py, plus:
- `ATLAS_LOG_BUFFER_SIZE`: Log buffer size (default: 100)
- `ATLAS_LOG_FLUSH_INTERVAL`: Flush interval in seconds (default: 5.0)

**Usage:**
```python
from integration_orchestrator import IntegrationOrchestrator, IntegrationConfig

config = IntegrationConfig(
    client_id="FINCORE_UK_001",
    log_db_path="data/atlas_logs.db",
    log_dir="data/logs",
    github_db_path="data/atlas_github.db",
    github_token="ghp_...",
    github_owner="myorg",
    github_repo="myrepo"
)

orchestrator = IntegrationOrchestrator(config)
await orchestrator.initialize()

log_id = await orchestrator.ingest_log(...)
commit_sha = await orchestrator.update_repository_file(...)
```

### 4. platform_adapters.py
Platform-specific log adapters for multi-cloud and infrastructure monitoring.

**Supported Platforms:**
- Redis - Memory, clients, eviction metrics
- Kubernetes - Pod status, restarts, conditions
- Kafka - Cluster health, broker status, topics
- Vercel - Deployment status, build state
- Docker - Container status, memory, CPU
- Prometheus - Target health, scrape status
- Elasticsearch - Cluster health, shard status
- Datadog - Monitor state, alert status

**Features:**
- Async platform API integration
- Automatic log parsing and normalization
- Severity classification per platform
- Error code mapping to ATLAS taxonomy
- Metadata extraction and enrichment

**Usage:**
```python
from platform_adapters import get_adapter

adapter = get_adapter(
    platform="redis",
    client_id="FINCORE_UK_001",
    config={"host": "localhost", "port": 6379}
)

logs = await adapter.fetch_logs()
for raw_log in logs:
    parsed = adapter.parse_log(raw_log)
```

### 5. platform_integration.py
Unified platform integration manager with polling orchestration.

**Features:**
- Multi-platform concurrent polling
- Automatic log ingestion from all platforms
- Configurable poll intervals per platform
- Graceful error handling and recovery
- Platform availability reporting

**Environment Variables:**
- `{PLATFORM}_ENABLED`: Enable platform (true/false)
- `{PLATFORM}_*`: Platform-specific credentials and config
- `{PLATFORM}_POLL_INTERVAL`: Poll interval in seconds

**Usage:**
```python
from platform_integration import PlatformIntegrationManager

platforms_config = {
    "redis": {"host": "localhost", "port": 6379, "poll_interval": 30},
    "kubernetes": {"api_url": "https://k8s.local", "poll_interval": 60},
    "kafka": {"bootstrap_servers": ["localhost:9092"], "poll_interval": 60}
}

manager = PlatformIntegrationManager(
    client_id="FINCORE_UK_001",
    log_db_path="data/atlas_logs.db",
    log_dir="data/logs",
    platforms_config=platforms_config
)

await manager.start()
```

### 6. integration_api.py
FastAPI endpoints for integration operations.

**Endpoints:**

#### Log Ingestion
- `POST /api/integrations/logs/ingest` - Ingest a single log
- `GET /api/integrations/logs/history` - Query log history
- `GET /api/integrations/logs/stats` - Get ingestion statistics

#### Repository Operations
- `POST /api/integrations/repository/file/update` - Update a file
- `GET /api/integrations/repository/file/get` - Read a file
- `POST /api/integrations/repository/files/batch-update` - Batch update files
- `POST /api/integrations/repository/pull-request` - Create pull request
- `GET /api/integrations/repository/changes` - Get change history

#### Health
- `POST /api/integrations/health` - Health check

**Integration with FastAPI:**
```python
from fastapi import FastAPI
from backend.integrations.integration_api import router

app = FastAPI()
app.include_router(router)
```

## Database Schema

### monitored_logs
```sql
log_id TEXT PRIMARY KEY
client_id TEXT NOT NULL
timestamp TEXT NOT NULL
source TEXT NOT NULL
severity TEXT NOT NULL
service_name TEXT NOT NULL
message TEXT NOT NULL
error_code TEXT
raw_payload TEXT NOT NULL
metadata TEXT NOT NULL
created_at TEXT NOT NULL
```

### github_changes
```sql
change_id TEXT PRIMARY KEY
client_id TEXT NOT NULL
timestamp TEXT NOT NULL
file_path TEXT NOT NULL
operation TEXT NOT NULL
old_content TEXT
new_content TEXT NOT NULL
commit_sha TEXT
pr_number INTEGER
status TEXT NOT NULL
error_message TEXT
created_at TEXT NOT NULL
```

## Platform Adapters Configuration

### Redis
```python
config = {
    "host": "localhost",
    "port": 6379,
    "password": None,
    "poll_interval": 30
}
```

### Kubernetes
```python
config = {
    "api_url": "https://kubernetes.default.svc",
    "namespace": "default",
    "token": "k8s_token",
    "poll_interval": 60
}
```

### Kafka
```python
config = {
    "bootstrap_servers": ["localhost:9092"],
    "poll_interval": 60
}
```

### Vercel
```python
config = {
    "api_token": "vercel_token",
    "team_id": "team_id",
    "project_id": "project_id",
    "poll_interval": 300
}
```

### Docker
```python
config = {
    "socket_path": "/var/run/docker.sock",
    "poll_interval": 30
}
```

### Prometheus
```python
config = {
    "url": "http://localhost:9090",
    "poll_interval": 60
}
```

### Elasticsearch
```python
config = {
    "url": "http://localhost:9200",
    "username": "elastic",
    "password": "password",
    "poll_interval": 60
}
```

### Datadog
```python
config = {
    "api_key": "datadog_api_key",
    "app_key": "datadog_app_key",
    "site": "datadoghq.com",
    "poll_interval": 300
}
```

## Logging

All components use structlog with JSON output. Logs include:
- Timestamp (ISO-8601)
- Log level
- Logger name
- Event type
- Contextual key-value pairs
- Error traces (when applicable)

Example log output:
```json
{
  "timestamp": "2024-03-26T10:15:23.123456Z",
  "level": "info",
  "logger": "log_monitor",
  "event": "log_ingested",
  "log_id": "abc123def456",
  "client_id": "FINCORE_UK_001",
  "source": "java",
  "severity": "ERROR"
}
```

## Error Handling

All components implement:
- Explicit exception handling (no bare except)
- Structured error logging
- Graceful degradation
- Timeout enforcement (10s default for HTTP calls)
- Async-safe resource cleanup

## Multi-Tenancy

- `client_id` is mandatory on all operations
- Per-client data isolation enforced at database level
- No cross-client data leakage possible
- Audit trail includes client_id on every record

## Performance Considerations

- Log buffering reduces database writes
- Async I/O prevents blocking
- SQLite indexes on frequently queried columns
- GitHub API calls timeout after 10 seconds
- Batch operations reduce API round-trips

## Security

- GitHub token from environment only (never hardcoded)
- No credentials in logs
- SQLite database file permissions should be restricted
- All external API calls use HTTPS
- Input validation on all endpoints

## Monitoring Integration

Log files are written in JSONL format for easy ingestion into:
- ELK Stack
- Splunk
- Datadog
- CloudWatch
- Any JSONL-compatible log aggregator

File path: `{ATLAS_LOG_DIR}/{client_id}_logs_{timestamp}.jsonl`

## Platform Polling

Each platform adapter runs in a separate async task with configurable poll intervals:

```python
os.environ["REDIS_ENABLED"] = "true"
os.environ["REDIS_HOST"] = "localhost"
os.environ["REDIS_PORT"] = "6379"
os.environ["REDIS_POLL_INTERVAL"] = "30"

os.environ["KUBERNETES_ENABLED"] = "true"
os.environ["K8S_API_URL"] = "https://kubernetes.default.svc"
os.environ["K8S_POLL_INTERVAL"] = "60"

os.environ["KAFKA_ENABLED"] = "true"
os.environ["KAFKA_BOOTSTRAP_SERVERS"] = "localhost:9092"
os.environ["KAFKA_POLL_INTERVAL"] = "60"

os.environ["VERCEL_ENABLED"] = "true"
os.environ["VERCEL_API_TOKEN"] = "token"
os.environ["VERCEL_POLL_INTERVAL"] = "300"

os.environ["DOCKER_ENABLED"] = "true"
os.environ["DOCKER_SOCKET"] = "/var/run/docker.sock"
os.environ["DOCKER_POLL_INTERVAL"] = "30"

os.environ["PROMETHEUS_ENABLED"] = "true"
os.environ["PROMETHEUS_URL"] = "http://localhost:9090"
os.environ["PROMETHEUS_POLL_INTERVAL"] = "60"

os.environ["ELASTICSEARCH_ENABLED"] = "true"
os.environ["ELASTICSEARCH_URL"] = "http://localhost:9200"
os.environ["ELASTICSEARCH_POLL_INTERVAL"] = "60"

os.environ["DATADOG_ENABLED"] = "true"
os.environ["DATADOG_API_KEY"] = "key"
os.environ["DATADOG_APP_KEY"] = "key"
os.environ["DATADOG_POLL_INTERVAL"] = "300"
```

## Future Extensions

- GitLab/Bitbucket support
- Webhook-based log ingestion
- Real-time metrics export
- Custom platform adapter framework
- Multi-region deployment support
