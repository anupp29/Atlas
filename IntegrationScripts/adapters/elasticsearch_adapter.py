import json
from datetime import datetime
import structlog
import httpx

logger = structlog.get_logger()


class ElasticsearchAdapter:
    def __init__(self, client_id: str, config: dict):
        if not client_id:
            raise ValueError("client_id is mandatory")
        self.client_id = client_id
        self.config = config
    
    async def fetch_logs(self) -> list:
        es_url = self.config.get("url", "http://localhost:9200")
        username = self.config.get("username")
        password = self.config.get("password")
        
        try:
            auth = (username, password) if username and password else None
            
            async with httpx.AsyncClient(timeout=10, auth=auth) as client:
                response = await client.get(f"{es_url}/_cluster/health")
                response.raise_for_status()
                
                health_data = response.json()
                logs = [
                    {
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "cluster_health",
                        "data": health_data
                    }
                ]
                
                logger.info("elasticsearch_logs_fetched", count=len(logs))
                return logs
        except Exception as e:
            logger.error("elasticsearch_fetch_failed", error=str(e))
            return []
    
    def parse_log(self, raw_log: dict) -> dict:
        data = raw_log.get("data", {})
        
        status = data.get("status", "unknown")
        active_shards = data.get("active_shards", 0)
        unassigned_shards = data.get("unassigned_shards", 0)
        
        severity = "CRITICAL" if status == "red" else "WARNING" if status == "yellow" else "INFO"
        
        return {
            "source": "elasticsearch",
            "severity": severity,
            "service_name": "Elasticsearch",
            "message": f"Cluster status: {status}",
            "error_code": "ES_CLUSTER_RED" if status == "red" else None,
            "raw_payload": json.dumps(data),
            "metadata": {
                "status": status,
                "active_shards": active_shards,
                "unassigned_shards": unassigned_shards,
                "number_of_nodes": data.get("number_of_nodes"),
                "number_of_data_nodes": data.get("number_of_data_nodes")
            }
        }
