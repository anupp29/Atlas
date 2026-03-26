import asyncio
import os
from datetime import datetime
from typing import Optional
import structlog
from log_monitor import LogMonitor, LogSeverity, LogSource

from platform_adapters import get_adapter, PLATFORM_ADAPTERS

logger = structlog.get_logger()


class PlatformIntegrationManager:
    def __init__(
        self,
        client_id: str,
        log_db_path: str,
        log_dir: str,
        platforms_config: dict
    ):
        if not client_id:
            raise ValueError("client_id is mandatory")
        
        self.client_id = client_id
        self.log_monitor = LogMonitor(client_id, log_db_path, log_dir)
        self.platforms_config = platforms_config
        self.adapters: dict = {}
        self._running = False
        self._tasks: list = []
        
        self._initialize_adapters()
    
    def _initialize_adapters(self) -> None:
        for platform, config in self.platforms_config.items():
            adapter = get_adapter(platform, self.client_id, config)
            if adapter:
                self.adapters[platform] = adapter
                logger.info("adapter_initialized", platform=platform)
            else:
                logger.warning("adapter_initialization_failed", platform=platform)
    
    async def start(self) -> None:
        self._running = True
        logger.info("platform_integration_starting", client_id=self.client_id)
        
        log_task = asyncio.create_task(self.log_monitor.start())
        self._tasks.append(log_task)
        
        for platform in self.adapters:
            task = asyncio.create_task(self._platform_polling_loop(platform))
            self._tasks.append(task)
        
        try:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        except asyncio.CancelledError:
            logger.info("platform_integration_cancelled")
            await self.shutdown()
        except Exception as e:
            logger.error("platform_integration_error", error=str(e))
            await self.shutdown()
            raise
    
    async def _platform_polling_loop(self, platform: str) -> None:
        adapter = self.adapters[platform]
        poll_interval = self.platforms_config[platform].get("poll_interval", 60)
        
        while self._running:
            try:
                logs = await adapter.fetch_logs()
                
                for raw_log in logs:
                    parsed = adapter.parse_log(raw_log)
                    
                    await self.log_monitor.ingest_log(
                        source=LogSource[parsed["source"].upper()] if parsed["source"].upper() in LogSource.__members__ else LogSource.SYSTEM,
                        severity=LogSeverity[parsed["severity"]],
                        service_name=parsed["service_name"],
                        message=parsed["message"],
                        raw_payload=parsed["raw_payload"],
                        error_code=parsed.get("error_code"),
                        metadata=parsed.get("metadata", {})
                    )
                
                logger.info("platform_logs_processed", platform=platform, count=len(logs))
            except Exception as e:
                logger.error("platform_polling_error", platform=platform, error=str(e))
            
            await asyncio.sleep(poll_interval)
    
    async def shutdown(self) -> None:
        logger.info("platform_integration_shutting_down", client_id=self.client_id)
        
        self._running = False
        await self.log_monitor.stop()
        
        for task in self._tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("platform_integration_shutdown_complete", client_id=self.client_id)
    
    async def get_platform_logs(
        self,
        platform: str,
        limit: int = 50
    ) -> list:
        if platform.upper() not in LogSource.__members__:
            return []
        
        source = LogSource[platform.upper()]
        return await self.log_monitor.db.query_logs(
            client_id=self.client_id,
            source=source,
            limit=limit
        )
    
    def get_available_platforms(self) -> list:
        return list(PLATFORM_ADAPTERS.keys())
    
    def get_configured_platforms(self) -> list:
        return list(self.adapters.keys())
    
    def get_stats(self) -> dict:
        return {
            "client_id": self.client_id,
            "log_monitor_stats": self.log_monitor.get_stats(),
            "configured_platforms": self.get_configured_platforms(),
            "available_platforms": self.get_available_platforms()
        }


def load_platforms_config_from_env() -> dict:
    platforms_config = {}
    
    if os.getenv("REDIS_ENABLED") == "true":
        platforms_config["redis"] = {
            "host": os.getenv("REDIS_HOST", "localhost"),
            "port": int(os.getenv("REDIS_PORT", "6379")),
            "password": os.getenv("REDIS_PASSWORD"),
            "poll_interval": int(os.getenv("REDIS_POLL_INTERVAL", "30"))
        }
    
    if os.getenv("KUBERNETES_ENABLED") == "true":
        platforms_config["kubernetes"] = {
            "api_url": os.getenv("K8S_API_URL", "https://kubernetes.default.svc"),
            "namespace": os.getenv("K8S_NAMESPACE", "default"),
            "token": os.getenv("K8S_TOKEN"),
            "poll_interval": int(os.getenv("K8S_POLL_INTERVAL", "60"))
        }
    
    if os.getenv("KAFKA_ENABLED") == "true":
        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(",")
        platforms_config["kafka"] = {
            "bootstrap_servers": bootstrap_servers,
            "poll_interval": int(os.getenv("KAFKA_POLL_INTERVAL", "60"))
        }
    
    if os.getenv("VERCEL_ENABLED") == "true":
        platforms_config["vercel"] = {
            "api_token": os.getenv("VERCEL_API_TOKEN"),
            "team_id": os.getenv("VERCEL_TEAM_ID"),
            "project_id": os.getenv("VERCEL_PROJECT_ID"),
            "poll_interval": int(os.getenv("VERCEL_POLL_INTERVAL", "300"))
        }
    
    if os.getenv("DOCKER_ENABLED") == "true":
        platforms_config["docker"] = {
            "socket_path": os.getenv("DOCKER_SOCKET", "/var/run/docker.sock"),
            "poll_interval": int(os.getenv("DOCKER_POLL_INTERVAL", "30"))
        }
    
    if os.getenv("PROMETHEUS_ENABLED") == "true":
        platforms_config["prometheus"] = {
            "url": os.getenv("PROMETHEUS_URL", "http://localhost:9090"),
            "poll_interval": int(os.getenv("PROMETHEUS_POLL_INTERVAL", "60"))
        }
    
    if os.getenv("ELASTICSEARCH_ENABLED") == "true":
        platforms_config["elasticsearch"] = {
            "url": os.getenv("ELASTICSEARCH_URL", "http://localhost:9200"),
            "username": os.getenv("ELASTICSEARCH_USERNAME"),
            "password": os.getenv("ELASTICSEARCH_PASSWORD"),
            "poll_interval": int(os.getenv("ELASTICSEARCH_POLL_INTERVAL", "60"))
        }
    
    if os.getenv("DATADOG_ENABLED") == "true":
        platforms_config["datadog"] = {
            "api_key": os.getenv("DATADOG_API_KEY"),
            "app_key": os.getenv("DATADOG_APP_KEY"),
            "site": os.getenv("DATADOG_SITE", "datadoghq.com"),
            "poll_interval": int(os.getenv("DATADOG_POLL_INTERVAL", "300"))
        }
    
    return platforms_config
