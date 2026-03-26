import json
from datetime import datetime
import structlog

logger = structlog.get_logger()


class MySQLAdapter:
    def __init__(self, client_id: str, config: dict):
        if not client_id:
            raise ValueError("client_id is mandatory")
        self.client_id = client_id
        self.config = config
    
    async def fetch_logs(self) -> list:
        host = self.config.get("host", "localhost")
        port = self.config.get("port", 3306)
        user = self.config.get("user", "root")
        password = self.config.get("password")
        
        try:
            import mysql.connector
            
            conn = mysql.connector.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                connection_timeout=5
            )
            
            cursor = conn.cursor(dictionary=True)
            logs = []
            
            cursor.execute("SHOW STATUS")
            status = {row["Variable_name"]: row["Value"] for row in cursor.fetchall()}
            logs.append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": "server_status",
                "data": status
            })
            
            cursor.execute("SHOW PROCESSLIST")
            processes = cursor.fetchall()
            logs.append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": "processes",
                "data": {"process_count": len(processes), "processes": processes}
            })
            
            cursor.close()
            conn.close()
            logger.info("mysql_logs_fetched", count=len(logs))
            return logs
        except Exception as e:
            logger.error("mysql_fetch_failed", error=str(e))
            return []
    
    def parse_log(self, raw_log: dict) -> dict:
        log_type = raw_log.get("type", "unknown")
        data = raw_log.get("data", {})
        
        if log_type == "server_status":
            threads_connected = int(data.get("Threads_connected", 0))
            max_connections = int(data.get("max_connections", 100))
            
            conn_percent = (threads_connected / max_connections * 100) if max_connections > 0 else 0
            
            severity = "CRITICAL" if conn_percent > 90 else "WARNING" if conn_percent > 75 else "INFO"
            
            return {
                "source": "mysql",
                "severity": severity,
                "service_name": "MySQL",
                "message": f"MySQL connections: {threads_connected}/{max_connections}",
                "error_code": "MYSQL_CONNECTION_LIMIT" if conn_percent > 90 else None,
                "raw_payload": json.dumps(data),
                "metadata": {
                    "threads_connected": threads_connected,
                    "max_connections": max_connections,
                    "connection_percent": conn_percent,
                    "questions": int(data.get("Questions", 0)),
                    "slow_queries": int(data.get("Slow_queries", 0))
                }
            }
        
        elif log_type == "processes":
            process_count = data.get("process_count", 0)
            
            return {
                "source": "mysql",
                "severity": "WARNING" if process_count > 50 else "INFO",
                "service_name": "MySQL",
                "message": f"Active processes: {process_count}",
                "error_code": None,
                "raw_payload": json.dumps(data),
                "metadata": {
                    "process_count": process_count
                }
            }
        
        return {
            "source": "mysql",
            "severity": "INFO",
            "service_name": "MySQL",
            "message": "MySQL status",
            "error_code": None,
            "raw_payload": json.dumps(data),
            "metadata": {}
        }
