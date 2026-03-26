import json
from datetime import datetime
import structlog

logger = structlog.get_logger()


class DockerAdapter:
    def __init__(self, client_id: str, config: dict):
        if not client_id:
            raise ValueError("client_id is mandatory")
        self.client_id = client_id
        self.config = config
    
    async def fetch_logs(self) -> list:
        socket_path = self.config.get("socket_path", "/var/run/docker.sock")
        
        try:
            import docker
            
            client = docker.DockerClient(base_url=f"unix://{socket_path}")
            containers = client.containers.list()
            logs = []
            
            for container in containers:
                logs.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "container",
                    "data": {
                        "id": container.id,
                        "name": container.name,
                        "status": container.status,
                        "stats": container.stats(stream=False)
                    }
                })
            
            logger.info("docker_logs_fetched", count=len(logs))
            return logs
        except Exception as e:
            logger.error("docker_fetch_failed", error=str(e))
            return []
    
    def parse_log(self, raw_log: dict) -> dict:
        data = raw_log.get("data", {})
        
        container_name = data.get("name", "unknown")
        status = data.get("status", "unknown")
        stats = data.get("stats", {})
        
        memory_usage = stats.get("memory_stats", {}).get("usage", 0)
        memory_limit = stats.get("memory_stats", {}).get("limit", 1)
        memory_percent = (memory_usage / memory_limit * 100) if memory_limit > 0 else 0
        
        severity = "CRITICAL" if status == "exited" else "WARNING" if memory_percent > 80 else "INFO"
        
        return {
            "source": "docker",
            "severity": severity,
            "service_name": f"Docker-{container_name}",
            "message": f"Container {container_name}: {status}",
            "error_code": "DOCKER_CONTAINER_EXITED" if status == "exited" else None,
            "raw_payload": json.dumps(data),
            "metadata": {
                "container_id": data.get("id"),
                "container_name": container_name,
                "status": status,
                "memory_usage_mb": memory_usage / 1024 / 1024,
                "memory_percent": memory_percent,
                "cpu_percent": stats.get("cpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0)
            }
        }
