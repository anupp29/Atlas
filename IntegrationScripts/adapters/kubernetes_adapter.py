import json
from datetime import datetime
import structlog
import httpx

logger = structlog.get_logger()


class KubernetesAdapter:
    def __init__(self, client_id: str, config: dict):
        if not client_id:
            raise ValueError("client_id is mandatory")
        self.client_id = client_id
        self.config = config
    
    async def fetch_logs(self) -> list:
        api_url = self.config.get("api_url", "https://kubernetes.default.svc")
        namespace = self.config.get("namespace", "default")
        token = self.config.get("token")
        
        try:
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            
            async with httpx.AsyncClient(timeout=10, verify=False) as client:
                response = await client.get(
                    f"{api_url}/api/v1/namespaces/{namespace}/pods",
                    headers=headers
                )
                response.raise_for_status()
                
                pods_data = response.json()
                logs = []
                
                for pod in pods_data.get("items", []):
                    logs.append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "pod_status",
                        "data": pod
                    })
                
                logger.info("kubernetes_logs_fetched", count=len(logs))
                return logs
        except Exception as e:
            logger.error("kubernetes_fetch_failed", error=str(e))
            return []
    
    def parse_log(self, raw_log: dict) -> dict:
        data = raw_log.get("data", {})
        metadata = data.get("metadata", {})
        status = data.get("status", {})
        
        pod_name = metadata.get("name", "unknown")
        phase = status.get("phase", "Unknown")
        conditions = status.get("conditions", [])
        
        severity = "CRITICAL" if phase == "Failed" else "WARNING" if phase == "Pending" else "INFO"
        
        container_statuses = status.get("containerStatuses", [])
        restart_count = sum(cs.get("restartCount", 0) for cs in container_statuses)
        
        return {
            "source": "kubernetes",
            "severity": severity,
            "service_name": f"K8s-{pod_name}",
            "message": f"Pod {pod_name} phase: {phase}",
            "error_code": "K8S_POD_FAILED" if phase == "Failed" else None,
            "raw_payload": json.dumps(data),
            "metadata": {
                "pod_name": pod_name,
                "namespace": metadata.get("namespace"),
                "phase": phase,
                "restart_count": restart_count,
                "conditions": [{"type": c.get("type"), "status": c.get("status")} for c in conditions]
            }
        }
