import json
from datetime import datetime
import structlog
import httpx

logger = structlog.get_logger()


class VercelAdapter:
    def __init__(self, client_id: str, config: dict):
        if not client_id:
            raise ValueError("client_id is mandatory")
        self.client_id = client_id
        self.config = config
    
    async def fetch_logs(self) -> list:
        api_token = self.config.get("api_token")
        team_id = self.config.get("team_id")
        project_id = self.config.get("project_id")
        
        if not api_token:
            logger.error("vercel_missing_token")
            return []
        
        try:
            headers = {"Authorization": f"Bearer {api_token}"}
            base_url = "https://api.vercel.com"
            
            async with httpx.AsyncClient(timeout=10) as client:
                logs = []
                
                deployments_url = f"{base_url}/v6/deployments"
                if team_id:
                    deployments_url += f"?teamId={team_id}"
                
                response = await client.get(deployments_url, headers=headers)
                response.raise_for_status()
                
                deployments = response.json().get("deployments", [])
                
                for deployment in deployments[:10]:
                    logs.append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "deployment",
                        "data": deployment
                    })
                
                logger.info("vercel_logs_fetched", count=len(logs))
                return logs
        except Exception as e:
            logger.error("vercel_fetch_failed", error=str(e))
            return []
    
    def parse_log(self, raw_log: dict) -> dict:
        data = raw_log.get("data", {})
        
        deployment_id = data.get("uid", "unknown")
        state = data.get("state", "unknown")
        
        severity = "CRITICAL" if state == "ERROR" else "WARNING" if state == "BUILDING" else "INFO"
        
        return {
            "source": "vercel",
            "severity": severity,
            "service_name": f"Vercel-{data.get('name', 'deployment')}",
            "message": f"Deployment {deployment_id}: {state}",
            "error_code": "VERCEL_DEPLOYMENT_FAILED" if state == "ERROR" else None,
            "raw_payload": json.dumps(data),
            "metadata": {
                "deployment_id": deployment_id,
                "state": state,
                "created_at": data.get("createdAt"),
                "url": data.get("url")
            }
        }
