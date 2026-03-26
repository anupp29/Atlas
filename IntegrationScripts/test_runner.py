import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from log_monitor import LogMonitor, LogSeverity, LogSource
from github_repo_sync import GitHubRepoSync, GitHubConfig
from integration_orchestrator import IntegrationOrchestrator, IntegrationConfig


async def test():
    os.environ["ATLAS_CLIENT_ID"] = "FINCORE_UK_001"
    
    config = IntegrationConfig(
        client_id="FINCORE_UK_001",
        log_db_path="data/test_logs.db",
        log_dir="data/test_logs",
        github_db_path="data/test_github.db",
        github_token=None,
        github_owner=None,
        github_repo=None
    )
    
    orchestrator = IntegrationOrchestrator(config)
    await orchestrator.initialize()
    
    log_id = await orchestrator.ingest_log(
        source=LogSource.JAVA,
        severity=LogSeverity.ERROR,
        service_name="PaymentAPI",
        message="Connection pool exhausted",
        raw_payload="[2024-03-26 10:15:23] ERROR HikariPool - Connection is not available",
        error_code="CONNECTION_POOL_EXHAUSTED",
        metadata={"pool_size": 40, "active_connections": 40}
    )
    
    assert log_id, "Log ID should be generated"
    await asyncio.sleep(1)
    
    logs = await orchestrator.get_log_history(source=LogSource.JAVA)
    assert len(logs) > 0, "Logs should be retrievable"
    
    stats = orchestrator.get_log_stats()
    assert stats["total_processed"] > 0, "Stats should be tracked"
    
    await orchestrator.shutdown()
    print("✓ Integration scripts operational")


if __name__ == "__main__":
    asyncio.run(test())
