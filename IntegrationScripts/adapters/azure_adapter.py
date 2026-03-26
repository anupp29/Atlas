import json
from datetime import datetime
import structlog
import httpx

logger = structlog.get_logger()


class AzureAdapter:
    def __init__(self, client_id: str, config: dict):
        if not client_id:
            raise ValueError("client_id is mandatory")
        self.client_id = client_id
        self.config = config
    
    async def fetch_logs(self) -> list:
        subscription_id = self.config.get("subscription_id")
        access_token = self.config.get("access_token")
        resource_group = self.config.get("resource_group")
        
        if not subscription_id or not access_token:
            logger.error("azure_missing_credentials")
            return []
        
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            logs = []
            
            async with httpx.AsyncClient(timeout=10) as client:
                vms_url = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Compute/virtualMachines?api-version=2021-03-01"
                response = await client.get(vms_url, headers=headers)
                response.raise_for_status()
                
                vms = response.json().get("value", [])
                for vm in vms:
                    logs.append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "virtual_machine",
                        "data": vm
                    })
                
                alerts_url = f"https://management.azure.com/subscriptions/{subscription_id}/providers/Microsoft.AlertsManagement/alerts?api-version=2019-03-01"
                response = await client.get(alerts_url, headers=headers)
                response.raise_for_status()
                
                alerts = response.json().get("value", [])
                for alert in alerts:
                    logs.append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "alert",
                        "data": alert
                    })
                
                logger.info("azure_logs_fetched", count=len(logs))
                return logs
        except Exception as e:
            logger.error("azure_fetch_failed", error=str(e))
            return []
    
    def parse_log(self, raw_log: dict) -> dict:
        log_type = raw_log.get("type", "unknown")
        data = raw_log.get("data", {})
        
        if log_type == "virtual_machine":
            vm_name = data.get("name", "unknown")
            properties = data.get("properties", {})
            vm_status = properties.get("provisioningState", "unknown")
            
            severity = "CRITICAL" if vm_status == "Failed" else "WARNING" if vm_status == "Updating" else "INFO"
            
            return {
                "source": "azure",
                "severity": severity,
                "service_name": f"Azure-VM-{vm_name}",
                "message": f"Virtual machine {vm_name}: {vm_status}",
                "error_code": "AZURE_VM_FAILED" if vm_status == "Failed" else None,
                "raw_payload": json.dumps(data),
                "metadata": {
                    "vm_name": vm_name,
                    "status": vm_status,
                    "vm_size": properties.get("hardwareProfile", {}).get("vmSize"),
                    "location": data.get("location")
                }
            }
        
        elif log_type == "alert":
            alert_name = data.get("properties", {}).get("essentials", {}).get("alertRule", "unknown")
            severity_level = data.get("properties", {}).get("essentials", {}).get("severity", "unknown")
            
            severity = "CRITICAL" if severity_level == "Sev0" else "WARNING" if severity_level == "Sev1" else "INFO"
            
            return {
                "source": "azure",
                "severity": severity,
                "service_name": f"Azure-Alert-{alert_name}",
                "message": f"Alert: {alert_name}",
                "error_code": "AZURE_ALERT" if severity_level in ["Sev0", "Sev1"] else None,
                "raw_payload": json.dumps(data),
                "metadata": {
                    "alert_name": alert_name,
                    "severity": severity_level
                }
            }
        
        return {
            "source": "azure",
            "severity": "INFO",
            "service_name": "Azure",
            "message": "Azure status",
            "error_code": None,
            "raw_payload": json.dumps(data),
            "metadata": {}
        }
