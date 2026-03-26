import json
from datetime import datetime
import structlog

logger = structlog.get_logger()


class KafkaAdapter:
    def __init__(self, client_id: str, config: dict):
        if not client_id:
            raise ValueError("client_id is mandatory")
        self.client_id = client_id
        self.config = config
    
    async def fetch_logs(self) -> list:
        bootstrap_servers = self.config.get("bootstrap_servers", ["localhost:9092"])
        
        try:
            from kafka.admin import KafkaAdminClient
            
            admin_client = KafkaAdminClient(bootstrap_servers=bootstrap_servers, request_timeout_ms=5000)
            
            cluster_metadata = admin_client.describe_cluster()
            logs = []
            
            logs.append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": "cluster",
                "data": {
                    "brokers": cluster_metadata.get("brokers", []),
                    "controller": cluster_metadata.get("controller")
                }
            })
            
            topics = admin_client.list_topics()
            for topic_name in topics:
                logs.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "topic",
                    "data": {"topic": topic_name}
                })
            
            admin_client.close()
            logger.info("kafka_logs_fetched", count=len(logs))
            return logs
        except Exception as e:
            logger.error("kafka_fetch_failed", error=str(e))
            return []
    
    def parse_log(self, raw_log: dict) -> dict:
        log_type = raw_log.get("type", "unknown")
        data = raw_log.get("data", {})
        
        if log_type == "cluster":
            brokers = data.get("brokers", [])
            
            return {
                "source": "kafka",
                "severity": "CRITICAL" if len(brokers) == 0 else "INFO",
                "service_name": "Kafka-Cluster",
                "message": f"Kafka cluster: {len(brokers)} brokers",
                "error_code": "KAFKA_NO_BROKERS" if len(brokers) == 0 else None,
                "raw_payload": json.dumps(data),
                "metadata": {
                    "broker_count": len(brokers),
                    "controller": data.get("controller")
                }
            }
        
        elif log_type == "topic":
            topic = data.get("topic", "unknown")
            
            return {
                "source": "kafka",
                "severity": "INFO",
                "service_name": f"Kafka-Topic-{topic}",
                "message": f"Topic: {topic}",
                "error_code": None,
                "raw_payload": json.dumps(data),
                "metadata": {"topic": topic}
            }
        
        return {
            "source": "kafka",
            "severity": "INFO",
            "service_name": "Kafka",
            "message": "Kafka status",
            "error_code": None,
            "raw_payload": json.dumps(data),
            "metadata": {}
        }
