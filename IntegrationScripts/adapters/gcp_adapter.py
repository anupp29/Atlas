import json
from datetime import datetime
import structlog
import httpx

logger = structlog.get_logger()


class GCPAdapter:
    def __init__(self, client_id: str, config: dict):
        if not client_id:
            raise ValueError("client_id is mandatory")
        self.client_id = client_id
        self.config = config
    
    async def fetch_logs(self) -> list:
        project_id = self.config.get("project_id")
        access_token = self.config.get("access_token")
        
        if not project_id or not access_token:
            logger.error("gcp_missing_credentials")
            return []
        
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            logs = []
            
            async with httpx.AsyncClient(timeout=10) as client:
                compute_url = f"https://www.googleapis.com/compute/v1/projects/{project_id}/global/instances"
                response = await client.get(compute_url, headers=headers)
                response.raise_for_status()
                
                instances = response.json().get("items", [])
                for instance in instances:
                    logs.append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "compute_instance",
                        "data": instance
                    })
                
                monitoring_url = f"https://monitoring.googleapis.com/v3/projects/{project_id}/alertPolicies"
                response = await client.get(monitoring_url, headers=headers)
                response.raise_for_status()
                
                policies = response.json().get("alertPolicies", [])
                for policy in policies:
                    logs.append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "alert_policy",
                        "data": policy
                    })
                
                logger.info("gcp_logs_fetched", count=len(logs))
                return logs
        except Exception as e:
            logger.error("gcp_fetch_failed", error=str(e))
            return []
    
    def parse_log(self, raw_log: dict) -> dict:
        log_type = raw_log.get("type", "unknown")
        data = raw_log.get("data", {})
        
        if log_type == "compute_instance":
            instance_name = data.get("name", "unknown")
            status = data.get("status", "unknown")
            
            severity = "CRITICAL" if status == "TERMINATED" else "WARNING" if status == "STOPPING" else "INFO"
            
            return {
                "source": "gcp",
                "severity": severity,
                "service_name": f"GCP-Compute-{instance_name}",
                "message": f"Compute instance {instance_name}: {status}",
                "error_code": "GCP_INSTANCE_TERMINATED" if status == "TERMINATED" else None,
                "raw_payload": json.dumps(data),
                "metadata": {
                    "instance_name": instance_name,
                    "status": status,
                    "machine_type": data.get("machineType"),
                    "zone": data.get("zone")
                }
            }
        
        elif log_type == "alert_policy":
            policy_name = data.get("displayName", "unknown")
            
            return {
                "source": "gcp",
                "severity": "INFO",
                "service_name": f"GCP-Monitoring-{policy_name}",
                "message": f"Alert policy: {policy_name}",
                "error_code": None,
                "raw_payload": json.dumps(data),
                "metadata": {
                    "policy_name": policy_name,
                    "conditions": len(data.get("conditions", []))
                }
            }
        
        return {
            "source": "gcp",
            "severity": "INFO",
            "service_name": "GCP",
            "message": "GCP status",
            "error_code": None,
            "raw_payload": json.dumps(data),
            "metadata": {}
        }
