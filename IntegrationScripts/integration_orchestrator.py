import asyncio
import os
import sys
from datetime import datetime
from typing import Optional
import structlog
from dataclasses import dataclass
import json

from log_monitor import LogMonitor, LogSeverity, LogSource, monitor_context
from github_repo_sync import GitHubRepoSync, GitHubConfig, repo_sync_context

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@dataclass
class IntegrationConfig:
    client_id: str
    log_db_path: str
    log_dir: str
    github_db_path: str
    github_token: Optional[str]
    github_owner: Optional[str]
    github_repo: Optional[str]
    log_buffer_size: int = 100
    log_flush_interval: float = 5.0


class IntegrationOrchestrator:
    def __init__(self, config: IntegrationConfig):
        if not config.client_id:
            raise ValueError("client_id is mandatory")
        
        self.config = config
        self.log_monitor: Optional[LogMonitor] = None
        self.repo_sync: Optional[GitHubRepoSync] = None
        self._tasks: list[asyncio.Task] = []
    
    async def initialize(self) -> None:
        logger.info("orchestrator_initializing", client_id=self.config.client_id)
        
        self.log_monitor = LogMonitor(
            client_id=self.config.client_id,
            db_path=self.config.log_db_path,
            log_dir=self.config.log_dir,
            buffer_size=self.config.log_buffer_size,
            flush_interval=self.config.log_flush_interval
        )
        
        if all([self.config.github_token, self.config.github_owner, self.config.github_repo]):
            github_config = GitHubConfig(
                token=self.config.github_token,
                owner=self.config.github_owner,
                repo=self.config.github_repo
            )
            self.repo_sync = GitHubRepoSync(
                client_id=self.config.client_id,
                config=github_config,
                db_path=self.config.github_db_path
            )
            logger.info("github_sync_initialized", owner=self.config.github_owner, repo=self.config.github_repo)
        else:
            logger.warning("github_sync_disabled", reason="missing_credentials")
        
        logger.info("orchestrator_initialized", client_id=self.config.client_id)
    
    async def start(self) -> None:
        logger.info("orchestrator_starting", client_id=self.config.client_id)
        
        if self.log_monitor:
            task = asyncio.create_task(self.log_monitor.start())
            self._tasks.append(task)
            logger.info("log_monitor_started")
        
        try:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        except asyncio.CancelledError:
            logger.info("orchestrator_cancelled")
            await self.shutdown()
        except Exception as e:
            logger.error("orchestrator_error", error=str(e))
            await self.shutdown()
            raise
    
    async def shutdown(self) -> None:
        logger.info("orchestrator_shutting_down", client_id=self.config.client_id)
        
        if self.log_monitor:
            await self.log_monitor.stop()
        
        for task in self._tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("orchestrator_shutdown_complete", client_id=self.config.client_id)
    
    async def ingest_log(
        self,
        source: LogSource,
        severity: LogSeverity,
        service_name: str,
        message: str,
        raw_payload: str,
        error_code: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        if not self.log_monitor:
            raise RuntimeError("Log monitor not initialized")
        
        return await self.log_monitor.ingest_log(
            source=source,
            severity=severity,
            service_name=service_name,
            message=message,
            raw_payload=raw_payload,
            error_code=error_code,
            metadata=metadata
        )
    
    async def update_repository_file(
        self,
        file_path: str,
        new_content: str,
        commit_message: str
    ) -> Optional[str]:
        if not self.repo_sync:
            logger.warning("github_sync_not_available")
            return None
        
        return await self.repo_sync.update_file(
            file_path=file_path,
            new_content=new_content,
            commit_message=commit_message
        )
    
    async def batch_update_repository_files(
        self,
        updates: list[dict]
    ) -> dict:
        if not self.repo_sync:
            logger.warning("github_sync_not_available")
            return {"successful": [], "failed": updates}
        
        return await self.repo_sync.batch_update_files(updates)
    
    async def get_repository_file(self, file_path: str) -> Optional[str]:
        if not self.repo_sync:
            logger.warning("github_sync_not_available")
            return None
        
        return await self.repo_sync.get_file_content(file_path)
    
    async def create_pull_request(
        self,
        title: str,
        body: str,
        head_branch: str
    ) -> Optional[int]:
        if not self.repo_sync:
            logger.warning("github_sync_not_available")
            return None
        
        return await self.repo_sync.create_pull_request(title, body, head_branch)
    
    def get_log_stats(self) -> dict:
        if not self.log_monitor:
            return {}
        return self.log_monitor.get_stats()
    
    async def get_log_history(
        self,
        source: Optional[LogSource] = None,
        severity: Optional[LogSeverity] = None,
        limit: int = 100
    ) -> list[dict]:
        if not self.log_monitor:
            return []
        
        return await self.log_monitor.db.query_logs(
            client_id=self.config.client_id,
            source=source,
            severity=severity,
            limit=limit
        )
    
    async def get_repository_change_history(self, limit: int = 50) -> list[dict]:
        if not self.repo_sync:
            return []
        
        return await self.repo_sync.get_change_history(limit=limit)


def load_config_from_env() -> IntegrationConfig:
    client_id = os.getenv("ATLAS_CLIENT_ID")
    if not client_id:
        raise ValueError("ATLAS_CLIENT_ID environment variable is mandatory")
    
    return IntegrationConfig(
        client_id=client_id,
        log_db_path=os.getenv("ATLAS_LOG_DB", "data/atlas_logs.db"),
        log_dir=os.getenv("ATLAS_LOG_DIR", "data/logs"),
        github_db_path=os.getenv("ATLAS_GITHUB_DB", "data/atlas_github.db"),
        github_token=os.getenv("GITHUB_TOKEN"),
        github_owner=os.getenv("GITHUB_OWNER"),
        github_repo=os.getenv("GITHUB_REPO"),
        log_buffer_size=int(os.getenv("ATLAS_LOG_BUFFER_SIZE", "100")),
        log_flush_interval=float(os.getenv("ATLAS_LOG_FLUSH_INTERVAL", "5.0"))
    )


async def main():
    try:
        config = load_config_from_env()
        orchestrator = IntegrationOrchestrator(config)
        
        await orchestrator.initialize()
        
        await orchestrator.ingest_log(
            source=LogSource.JAVA,
            severity=LogSeverity.ERROR,
            service_name="PaymentAPI",
            message="Connection pool exhausted",
            raw_payload="[2024-03-26 10:15:23] ERROR HikariPool - Connection is not available",
            error_code="CONNECTION_POOL_EXHAUSTED",
            metadata={"pool_size": 40, "active_connections": 40}
        )
        
        await asyncio.sleep(2)
        
        logs = await orchestrator.get_log_history(source=LogSource.JAVA)
        logger.info("logs_retrieved", count=len(logs))
        
        stats = orchestrator.get_log_stats()
        logger.info("orchestrator_stats", stats=stats)
        
        await orchestrator.shutdown()
    except Exception as e:
        logger.error("orchestrator_main_error", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
