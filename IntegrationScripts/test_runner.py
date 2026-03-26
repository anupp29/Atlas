import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from log_monitor import LogMonitor, LogSeverity, LogSource, LogMonitorDB
from github_repo_sync import GitHubRepoSync, GitHubConfig, GitHubRepoSyncDB
from integration_orchestrator import IntegrationOrchestrator, IntegrationConfig
from adapters import get_adapter, ADAPTERS
from platform_integration import PlatformIntegrationManager, load_platforms_config_from_env


async def test_log_monitor():
    print("\n[TEST] LogMonitor...")
    monitor = LogMonitor("TEST_CLIENT", "data/test_logs.db", "data/test_logs")
    
    log_id = await monitor.ingest_log(
        source=LogSource.JAVA,
        severity=LogSeverity.ERROR,
        service_name="PaymentAPI",
        message="Connection pool exhausted",
        raw_payload="[2024-03-26 10:15:23] ERROR HikariPool",
        error_code="CONNECTION_POOL_EXHAUSTED",
        metadata={"pool_size": 40}
    )
    assert log_id, "Log ID generated"
    
    await monitor._flush_buffer()
    logs = await monitor.db.query_logs("TEST_CLIENT", source=LogSource.JAVA)
    assert len(logs) > 0, "Logs persisted"
    
    stats = monitor.get_stats()
    assert stats["total_processed"] == 1, "Stats tracked"
    
    await monitor.stop()
    print("✓ LogMonitor passed")


async def test_log_monitor_db():
    print("\n[TEST] LogMonitorDB...")
    import uuid
    db = LogMonitorDB("data/test_logs_db.db")
    
    from log_monitor import MonitoredLogEntry
    entry = MonitoredLogEntry(
        log_id=str(uuid.uuid4())[:16],
        client_id="TEST_CLIENT",
        timestamp="2024-03-26T10:15:23Z",
        source=LogSource.POSTGRES,
        severity=LogSeverity.WARNING,
        service_name="TransactionDB",
        message="Slow query detected",
        error_code="DB_SLOW_QUERY",
        raw_payload="SELECT * FROM transactions WHERE...",
        metadata={"duration_ms": 5000}
    )
    
    await db.insert_log(entry)
    logs = await db.query_logs("TEST_CLIENT", severity=LogSeverity.WARNING)
    assert len(logs) > 0, "DB query works"
    print("✓ LogMonitorDB passed")


async def test_github_repo_sync_db():
    print("\n[TEST] GitHubRepoSyncDB...")
    import uuid
    db = GitHubRepoSyncDB("data/test_github_db.db")
    
    from github_repo_sync import ChangeAuditRecord
    record = ChangeAuditRecord(
        change_id=str(uuid.uuid4())[:16],
        client_id="TEST_CLIENT",
        timestamp="2024-03-26T10:15:23Z",
        file_path="src/config.py",
        operation="update",
        old_content="old_config",
        new_content="new_config",
        commit_sha="abc123def456",
        pr_number=None,
        status="success",
        error_message=None
    )
    
    await db.insert_change(record)
    changes = await db.query_changes("TEST_CLIENT", status="success")
    assert len(changes) > 0, "Change recorded"
    print("✓ GitHubRepoSyncDB passed")


async def test_orchestrator():
    print("\n[TEST] IntegrationOrchestrator...")
    os.environ["ATLAS_CLIENT_ID"] = "FINCORE_UK_001"
    
    config = IntegrationConfig(
        client_id="FINCORE_UK_001",
        log_db_path="data/test_orch_logs.db",
        log_dir="data/test_orch_logs",
        github_db_path="data/test_orch_github.db",
        github_token=None,
        github_owner=None,
        github_repo=None
    )
    
    orchestrator = IntegrationOrchestrator(config)
    await orchestrator.initialize()
    
    log_id = await orchestrator.ingest_log(
        source=LogSource.NODEJS,
        severity=LogSeverity.ERROR,
        service_name="APIGateway",
        message="Unhandled rejection",
        raw_payload="UnhandledPromiseRejectionWarning: Error",
        error_code="NODE_UNHANDLED_REJECTION"
    )
    assert log_id, "Orchestrator ingest works"
    
    if orchestrator.log_monitor:
        await orchestrator.log_monitor._flush_buffer()
    
    logs = await orchestrator.get_log_history(source=LogSource.NODEJS)
    assert len(logs) > 0, "Orchestrator query works"
    
    stats = orchestrator.get_log_stats()
    assert stats["total_processed"] > 0, "Orchestrator stats work"
    
    await orchestrator.shutdown()
    print("✓ IntegrationOrchestrator passed")


async def test_multiple_sources():
    print("\n[TEST] Multiple log sources...")
    monitor = LogMonitor("MULTI_TEST", "data/test_multi.db", "data/test_multi")
    
    sources = [
        (LogSource.JAVA, LogSeverity.ERROR, "JavaService"),
        (LogSource.POSTGRES, LogSeverity.WARNING, "PostgresDB"),
        (LogSource.NODEJS, LogSeverity.INFO, "NodeService"),
        (LogSource.REDIS, LogSeverity.CRITICAL, "RedisCache"),
    ]
    
    for source, severity, service in sources:
        await monitor.ingest_log(
            source=source,
            severity=severity,
            service_name=service,
            message=f"Test message from {source.value}",
            raw_payload=f"Raw payload {source.value}"
        )
    
    await monitor._flush_buffer()
    
    for source, _, _ in sources:
        logs = await monitor.db.query_logs("MULTI_TEST", source=source)
        assert len(logs) > 0, f"Logs for {source.value} found"
    
    all_logs = await monitor.db.query_logs("MULTI_TEST")
    assert len(all_logs) >= 4, "All logs retrieved"
    
    await monitor.stop()
    print("✓ Multiple sources passed")


async def test_log_file_export():
    print("\n[TEST] Log file export...")
    monitor = LogMonitor("FILE_TEST", "data/test_file.db", "data/test_file_logs")
    
    for i in range(5):
        await monitor.ingest_log(
            source=LogSource.JAVA,
            severity=LogSeverity.ERROR,
            service_name="TestService",
            message=f"Error {i}",
            raw_payload=f"Payload {i}"
        )
    
    await monitor._flush_buffer()
    
    log_files = list(Path("data/test_file_logs").glob("*.jsonl"))
    assert len(log_files) > 0, "JSONL files created"
    
    with open(log_files[0]) as f:
        lines = f.readlines()
        assert len(lines) == 5, "All logs in file"
    
    await monitor.stop()
    print("✓ Log file export passed")


async def test_platform_adapters():
    print("\n[TEST] Platform adapters...")
    
    adapters_to_test = [
        ("redis", {"host": "localhost", "port": 6379}),
        ("prometheus", {"url": "http://localhost:9090"}),
        ("elasticsearch", {"url": "http://localhost:9200"}),
    ]
    
    for platform, config in adapters_to_test:
        adapter = get_adapter(platform, "TEST_CLIENT", config)
        assert adapter is not None, f"Adapter for {platform} created"
        
        parsed = adapter.parse_log({
            "timestamp": "2024-03-26T10:15:23Z",
            "type": "test",
            "data": {}
        })
        
        assert "source" in parsed, f"{platform} parse includes source"
        assert "severity" in parsed, f"{platform} parse includes severity"
        assert "message" in parsed, f"{platform} parse includes message"
    
    print("✓ Platform adapters passed")


async def test_platform_integration_manager():
    print("\n[TEST] PlatformIntegrationManager...")
    
    platforms_config = {
        "redis": {
            "host": "localhost",
            "port": 6379,
            "poll_interval": 30
        },
        "prometheus": {
            "url": "http://localhost:9090",
            "poll_interval": 60
        }
    }
    
    manager = PlatformIntegrationManager(
        client_id="PLATFORM_TEST",
        log_db_path="data/test_platform.db",
        log_dir="data/test_platform_logs",
        platforms_config=platforms_config
    )
    
    configured = manager.get_configured_platforms()
    assert len(configured) > 0, "Platforms configured"
    
    available = manager.get_available_platforms()
    assert "redis" in available, "Redis in available platforms"
    assert "kubernetes" in available, "Kubernetes in available platforms"
    assert "kafka" in available, "Kafka in available platforms"
    
    stats = manager.get_stats()
    assert stats["client_id"] == "PLATFORM_TEST", "Stats include client_id"
    
    await manager.shutdown()
    print("✓ PlatformIntegrationManager passed")


async def test_all_platform_adapters():
    print("\n[TEST] All platform adapters instantiation...")
    
    for platform_name in ADAPTERS.keys():
        adapter = get_adapter(platform_name, "TEST_CLIENT", {})
        assert adapter is not None, f"{platform_name} adapter instantiated"
    
    print(f"✓ All {len(ADAPTERS)} platform adapters passed")


async def main():
    print("=" * 60)
    print("ATLAS INTEGRATION SCRIPTS TEST SUITE")
    print("=" * 60)
    
    try:
        await test_log_monitor()
        await test_log_monitor_db()
        await test_github_repo_sync_db()
        await test_orchestrator()
        await test_multiple_sources()
        await test_log_file_export()
        await test_platform_adapters()
        await test_platform_integration_manager()
        await test_all_platform_adapters()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
