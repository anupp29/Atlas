import json
from datetime import datetime
import structlog
import httpx

logger = structlog.get_logger()


class PrometheusAdapter:
    def __init__(self, client_id: str, config: dict):
        if not client_id:
            raise ValueError("client_id is mandatory")
        self.client_id = client_id
        self.config = config
    
    async def fetch_logs(self) -> list:
        prometheus_url = self.config.get("url", "http://localhost:9090")
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{prometheus_url}/api/v1/targets")
                response.raise_for_status()
                
                targets_data = response.json()
                logs = []
                
                for target in targets_data.get("data", {}).get("activeTargets", []):
                    logs.append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "target",
                        "data": target
                    })
                
                logger.info("prometheus_logs_fetched", count=len(logs))
                return logs
        except Exception as e:
            logger.error("prometheus_fetch_failed", error=str(e))
            return []
    
    def parse_log(self, raw_log: dict) -> dict:
        data = raw_log.get("data", {})
        
        labels = data.get("labels", {})
        health = data.get("health", "unknown")
        
        severity = "CRITICAL" if health == "down" else "INFO"
        
        return {
            "source": "prometheus",
            "severity": severity,
            "service_name": f"Prometheus-{labels.get('job', 'unknown')}",
            "message": f"Target {labels.get('instance', 'unknown')}: {health}",
            "error_code": "PROMETHEUS_TARGET_DOWN" if health == "down" else None,
            "raw_payload": json.dumps(data),
            "metadata": {
                "job": labels.get("job"),
                "instance": labels.get("instance"),
                "health": health,
                "labels": labels
            }
        }
