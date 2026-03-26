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

### 4. integration_api.py
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

## Future Extensions

- Kafka streaming support
- Elasticsearch direct integration
- GitLab/Bitbucket support
- Webhook-based log ingestion
- Real-time metrics export
