import json
from datetime import datetime
from typing import Optional
import structlog

logger = structlog.get_logger()


class RedisAdapter:
    def __init__(self, client_id: str, config: dict):
        if not client_id:
            raise ValueError("client_id is mandatory")
        self.client_id = client_id
        self.config = config
    
    async def fetch_logs(self) -> list:
        host = self.config.get("host", "localhost")
        port = self.config.get("port", 6379)
        password = self.config.get("password")
        
        try:
            import redis
            
            client = redis.Redis(
                host=host,
                port=port,
                password=password,
                decode_responses=True,
                socket_timeout=5
            )
            
            info = client.info()
            logs = []
            
            if info.get("used_memory_human"):
                logs.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "memory",
                    "data": info
                })
            
            if info.get("connected_clients"):
                logs.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "clients",
                    "data": info
                })
            
            client.close()
            logger.info("redis_logs_fetched", count=len(logs))
            return logs
        except Exception as e:
            logger.error("redis_fetch_failed", error=str(e))
            return []
    
    def parse_log(self, raw_log: dict) -> dict:
        log_type = raw_log.get("type", "unknown")
        data = raw_log.get("data", {})
        
        if log_type == "memory":
            used_memory = data.get("used_memory", 0)
            max_memory = data.get("maxmemory", 0)
            memory_percent = (used_memory / max_memory * 100) if max_memory > 0 else 0
            
            severity = "CRITICAL" if memory_percent > 90 else "WARNING" if memory_percent > 75 else "INFO"
            
            return {
                "source": "redis",
                "severity": severity,
                "service_name": "Redis",
                "message": f"Memory usage: {memory_percent:.1f}%",
                "error_code": "REDIS_OOM" if memory_percent > 90 else None,
                "raw_payload": json.dumps(data),
                "metadata": {
                    "used_memory_mb": used_memory / 1024 / 1024,
                    "max_memory_mb": max_memory / 1024 / 1024,
                    "memory_percent": memory_percent,
                    "evicted_keys": data.get("evicted_keys", 0),
                    "rejected_connections": data.get("rejected_connections", 0)
                }
            }
        
        elif log_type == "clients":
            connected = data.get("connected_clients", 0)
            max_clients = data.get("maxclients", 10000)
            
            return {
                "source": "redis",
                "severity": "WARNING" if connected > max_clients * 0.8 else "INFO",
                "service_name": "Redis",
                "message": f"Connected clients: {connected}/{max_clients}",
                "error_code": None,
                "raw_payload": json.dumps(data),
                "metadata": {
                    "connected_clients": connected,
                    "max_clients": max_clients,
                    "blocked_clients": data.get("blocked_clients", 0)
                }
            }
        
        return {
            "source": "redis",
            "severity": "INFO",
            "service_name": "Redis",
            "message": "Redis status",
            "error_code": None,
            "raw_payload": json.dumps(data),
            "metadata": {}
        }
