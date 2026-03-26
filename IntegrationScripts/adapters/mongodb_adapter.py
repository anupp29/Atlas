import json
from datetime import datetime
import structlog

logger = structlog.get_logger()


class MongoDBAdapter:
    def __init__(self, client_id: str, config: dict):
        if not client_id:
            raise ValueError("client_id is mandatory")
        self.client_id = client_id
        self.config = config
    
    async def fetch_logs(self) -> list:
        connection_string = self.config.get("connection_string", "mongodb://localhost:27017")
        
        try:
            from pymongo import MongoClient
            
            client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
            admin_db = client.admin
            
            logs = []
            
            server_status = admin_db.command("serverStatus")
            logs.append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": "server_status",
                "data": server_status
            })
            
            db_stats = admin_db.command("dbStats")
            logs.append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": "db_stats",
                "data": db_stats
            })
            
            client.close()
            logger.info("mongodb_logs_fetched", count=len(logs))
            return logs
        except Exception as e:
            logger.error("mongodb_fetch_failed", error=str(e))
            return []
    
    def parse_log(self, raw_log: dict) -> dict:
        log_type = raw_log.get("type", "unknown")
        data = raw_log.get("data", {})
        
        if log_type == "server_status":
            uptime = data.get("uptime", 0)
            connections = data.get("connections", {})
            current_conns = connections.get("current", 0)
            available_conns = connections.get("available", 0)
            
            conn_percent = (current_conns / (current_conns + available_conns) * 100) if (current_conns + available_conns) > 0 else 0
            
            severity = "CRITICAL" if conn_percent > 90 else "WARNING" if conn_percent > 75 else "INFO"
            
            return {
                "source": "mongodb",
                "severity": severity,
                "service_name": "MongoDB",
                "message": f"MongoDB connections: {current_conns}/{current_conns + available_conns}",
                "error_code": "MONGODB_CONNECTION_LIMIT" if conn_percent > 90 else None,
                "raw_payload": json.dumps(data),
                "metadata": {
                    "uptime_seconds": uptime,
                    "current_connections": current_conns,
                    "available_connections": available_conns,
                    "connection_percent": conn_percent
                }
            }
        
        elif log_type == "db_stats":
            storage_size = data.get("storageSize", 0)
            data_size = data.get("dataSize", 0)
            
            return {
                "source": "mongodb",
                "severity": "INFO",
                "service_name": "MongoDB",
                "message": f"Database size: {storage_size / 1024 / 1024:.2f}MB",
                "error_code": None,
                "raw_payload": json.dumps(data),
                "metadata": {
                    "storage_size_mb": storage_size / 1024 / 1024,
                    "data_size_mb": data_size / 1024 / 1024,
                    "collections": data.get("collections", 0),
                    "indexes": data.get("indexes", 0)
                }
            }
        
        return {
            "source": "mongodb",
            "severity": "INFO",
            "service_name": "MongoDB",
            "message": "MongoDB status",
            "error_code": None,
            "raw_payload": json.dumps(data),
            "metadata": {}
        }
