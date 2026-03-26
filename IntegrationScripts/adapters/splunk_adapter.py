import json
from datetime import datetime
import structlog
import httpx

logger = structlog.get_logger()


class SplunkAdapter:
    def __init__(self, client_id: str, config: dict):
        if not client_id:
            raise ValueError("client_id is mandatory")
        self.client_id = client_id
        self.config = config
    
    async def fetch_logs(self) -> list:
        splunk_url = self.config.get("url", "https://localhost:8089")
        username = self.config.get("username")
        password = self.config.get("password")
        
        if not username or not password:
            logger.error("splunk_missing_credentials")
            return []
        
        try:
            auth = (username, password)
            logs = []
            
            async with httpx.AsyncClient(timeout=10, verify=False, auth=auth) as client:
                searches_url = f"{splunk_url}/services/search/jobs"
                response = await client.get(searches_url)
                response.raise_for_status()
                
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.text)
                
                for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
                    title = entry.find("{http://www.w3.org/2005/Atom}title")
                    if title is not None:
                        logs.append({
                            "timestamp": datetime.utcnow().isoformat(),
                            "type": "search_job",
                            "data": {"title": title.text}
                        })
                
                alerts_url = f"{splunk_url}/services/alerts/fired_alerts"
                response = await client.get(alerts_url)
                response.raise_for_status()
                
                root = ET.fromstring(response.text)
                for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
                    title = entry.find("{http://www.w3.org/2005/Atom}title")
                    if title is not None:
                        logs.append({
                            "timestamp": datetime.utcnow().isoformat(),
                            "type": "fired_alert",
                            "data": {"title": title.text}
                        })
                
                logger.info("splunk_logs_fetched", count=len(logs))
                return logs
        except Exception as e:
            logger.error("splunk_fetch_failed", error=str(e))
            return []
    
    def parse_log(self, raw_log: dict) -> dict:
        log_type = raw_log.get("type", "unknown")
        data = raw_log.get("data", {})
        
        if log_type == "search_job":
            title = data.get("title", "unknown")
            
            return {
                "source": "splunk",
                "severity": "INFO",
                "service_name": f"Splunk-Search-{title}",
                "message": f"Search job: {title}",
                "error_code": None,
                "raw_payload": json.dumps(data),
                "metadata": {
                    "title": title
                }
            }
        
        elif log_type == "fired_alert":
            title = data.get("title", "unknown")
            
            return {
                "source": "splunk",
                "severity": "WARNING",
                "service_name": f"Splunk-Alert-{title}",
                "message": f"Alert fired: {title}",
                "error_code": "SPLUNK_ALERT_FIRED",
                "raw_payload": json.dumps(data),
                "metadata": {
                    "title": title
                }
            }
        
        return {
            "source": "splunk",
            "severity": "INFO",
            "service_name": "Splunk",
            "message": "Splunk status",
            "error_code": None,
            "raw_payload": json.dumps(data),
            "metadata": {}
        }
