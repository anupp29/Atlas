import json
from datetime import datetime
import structlog
import httpx

logger = structlog.get_logger()


class DatadogAdapter:
    def __init__(self, client_id: str, config: dict):
        if not client_id:
            raise ValueError("client_id is mandatory")
        self.client_id = client_id
        self.config = config
    
    async def fetch_logs(self) -> list:
        api_key = self.config.get("api_key")
        app_key = self.config.get("app_key")
        site = self.config.get("site", "datadoghq.com")
        
        if not api_key or not app_key:
            logger.error("datadog_missing_keys")
            return []
        
        try:
            headers = {
                "DD-API-KEY": api_key,
                "DD-APPLICATION-KEY": app_key
            }
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"https://api.{site}/api/v1/monitor",
                    headers=headers
                )
                response.raise_for_status()
                
                monitors = response.json()
                logs = []
                
                for monitor in monitors[:10]:
                    logs.append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "monitor",
                        "data": monitor
                    })
                
                logger.info("datadog_logs_fetched", count=len(logs))
                return logs
        except Exception as e:
            logger.error("datadog_fetch_failed", error=str(e))
            return []
    
    def parse_log(self, raw_log: dict) -> dict:
        data = raw_log.get("data", {})
        
        monitor_id = data.get("id", "unknown")
        name = data.get("name", "unknown")
        state = data.get("overall_state", "unknown")
        
        severity = "CRITICAL" if state == "alert" else "WARNING" if state == "warn" else "INFO"
        
        return {
            "source": "datadog",
            "severity": severity,
            "service_name": f"Datadog-{name}",
            "message": f"Monitor {monitor_id}: {state}",
            "error_code": "DATADOG_ALERT" if state == "alert" else None,
            "raw_payload": json.dumps(data),
            "metadata": {
                "monitor_id": monitor_id,
                "name": name,
                "state": state,
                "type": data.get("type")
            }
        }
