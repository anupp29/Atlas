import json
from datetime import datetime
import structlog
import httpx

logger = structlog.get_logger()


class NewRelicAdapter:
    def __init__(self, client_id: str, config: dict):
        if not client_id:
            raise ValueError("client_id is mandatory")
        self.client_id = client_id
        self.config = config
    
    async def fetch_logs(self) -> list:
        api_key = self.config.get("api_key")
        account_id = self.config.get("account_id")
        
        if not api_key or not account_id:
            logger.error("newrelic_missing_credentials")
            return []
        
        try:
            headers = {"X-Api-Key": api_key}
            logs = []
            
            async with httpx.AsyncClient(timeout=10) as client:
                incidents_url = f"https://api.newrelic.com/v2/incidents.json?filter[states]=open"
                response = await client.get(incidents_url, headers=headers)
                response.raise_for_status()
                
                incidents = response.json().get("incidents", [])
                for incident in incidents:
                    logs.append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "incident",
                        "data": incident
                    })
                
                alerts_url = f"https://api.newrelic.com/v2/alerts_policies.json"
                response = await client.get(alerts_url, headers=headers)
                response.raise_for_status()
                
                policies = response.json().get("policies", [])
                for policy in policies[:10]:
                    logs.append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "alert_policy",
                        "data": policy
                    })
                
                logger.info("newrelic_logs_fetched", count=len(logs))
                return logs
        except Exception as e:
            logger.error("newrelic_fetch_failed", error=str(e))
            return []
    
    def parse_log(self, raw_log: dict) -> dict:
        log_type = raw_log.get("type", "unknown")
        data = raw_log.get("data", {})
        
        if log_type == "incident":
            incident_id = data.get("id", "unknown")
            title = data.get("title", "unknown")
            severity = data.get("severity", "unknown")
            
            severity_map = "CRITICAL" if severity == "critical" else "WARNING" if severity == "warning" else "INFO"
            
            return {
                "source": "newrelic",
                "severity": severity_map,
                "service_name": f"NewRelic-Incident-{incident_id}",
                "message": f"Incident: {title}",
                "error_code": "NEWRELIC_INCIDENT" if severity == "critical" else None,
                "raw_payload": json.dumps(data),
                "metadata": {
                    "incident_id": incident_id,
                    "title": title,
                    "severity": severity,
                    "opened_at": data.get("opened_at")
                }
            }
        
        elif log_type == "alert_policy":
            policy_id = data.get("id", "unknown")
            policy_name = data.get("name", "unknown")
            
            return {
                "source": "newrelic",
                "severity": "INFO",
                "service_name": f"NewRelic-Policy-{policy_id}",
                "message": f"Alert policy: {policy_name}",
                "error_code": None,
                "raw_payload": json.dumps(data),
                "metadata": {
                    "policy_id": policy_id,
                    "policy_name": policy_name,
                    "enabled": data.get("enabled")
                }
            }
        
        return {
            "source": "newrelic",
            "severity": "INFO",
            "service_name": "NewRelic",
            "message": "NewRelic status",
            "error_code": None,
            "raw_payload": json.dumps(data),
            "metadata": {}
        }
