import asyncio
import json
import re
from datetime import datetime
from typing import Optional
from abc import ABC, abstractmethod
import structlog
import httpx

logger = structlog.get_logger()


class PlatformAdapter(ABC):
    def __init__(self, client_id: str, config: dict):
        if not client_id:
            raise ValueError("client_id is mandatory")
        self.client_id = client_id
        self.config = config
    
    @abstractmethod
    async def fetch_logs(self) -> list:
        pass
    
    @abstractmethod
    def parse_log(self, raw_log: dict) -> dict:
        pass


class RedisAdapter(PlatformAdapter):
    async def fetch_logs(self) -> list[dict]:
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


class KubernetesAdapter(PlatformAdapter):
    async def fetch_logs(self) -> list[dict]:
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


class KafkaAdapter(PlatformAdapter):
    async def fetch_logs(self) -> list[dict]:
        bootstrap_servers = self.config.get("bootstrap_servers", ["localhost:9092"])
        
        try:
            from kafka.admin import KafkaAdminClient
            from kafka import KafkaConsumer
            
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


class VercelAdapter(PlatformAdapter):
    async def fetch_logs(self) -> list[dict]:
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


class DockerAdapter(PlatformAdapter):
    async def fetch_logs(self) -> list[dict]:
        socket_path = self.config.get("socket_path", "/var/run/docker.sock")
        
        try:
            import docker
            
            client = docker.DockerClient(base_url=f"unix://{socket_path}")
            containers = client.containers.list()
            logs = []
            
            for container in containers:
                logs.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "container",
                    "data": {
                        "id": container.id,
                        "name": container.name,
                        "status": container.status,
                        "stats": container.stats(stream=False)
                    }
                })
            
            logger.info("docker_logs_fetched", count=len(logs))
            return logs
        except Exception as e:
            logger.error("docker_fetch_failed", error=str(e))
            return []
    
    def parse_log(self, raw_log: dict) -> dict:
        data = raw_log.get("data", {})
        
        container_name = data.get("name", "unknown")
        status = data.get("status", "unknown")
        stats = data.get("stats", {})
        
        memory_usage = stats.get("memory_stats", {}).get("usage", 0)
        memory_limit = stats.get("memory_stats", {}).get("limit", 1)
        memory_percent = (memory_usage / memory_limit * 100) if memory_limit > 0 else 0
        
        severity = "CRITICAL" if status == "exited" else "WARNING" if memory_percent > 80 else "INFO"
        
        return {
            "source": "docker",
            "severity": severity,
            "service_name": f"Docker-{container_name}",
            "message": f"Container {container_name}: {status}",
            "error_code": "DOCKER_CONTAINER_EXITED" if status == "exited" else None,
            "raw_payload": json.dumps(data),
            "metadata": {
                "container_id": data.get("id"),
                "container_name": container_name,
                "status": status,
                "memory_usage_mb": memory_usage / 1024 / 1024,
                "memory_percent": memory_percent,
                "cpu_percent": stats.get("cpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0)
            }
        }


class PrometheusAdapter(PlatformAdapter):
    async def fetch_logs(self) -> list[dict]:
        prometheus_url = self.config.get("url", "http://localhost:9090")
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{prometheus_url}/api/v1/targets")
                response.raise_for_status()
                
                targets_data = response.json()
                logs = []
                
                for target in targets_data.get("data", {}).get("activeTargets", []):
                    logs.append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "target",
                        "data": target
                    })
                
                logger.info("prometheus_logs_fetched", count=len(logs))
                return logs
        except Exception as e:
            logger.error("prometheus_fetch_failed", error=str(e))
            return []
    
    def parse_log(self, raw_log: dict) -> dict:
        data = raw_log.get("data", {})
        
        labels = data.get("labels", {})
        health = data.get("health", "unknown")
        
        severity = "CRITICAL" if health == "down" else "INFO"
        
        return {
            "source": "prometheus",
            "severity": severity,
            "service_name": f"Prometheus-{labels.get('job', 'unknown')}",
            "message": f"Target {labels.get('instance', 'unknown')}: {health}",
            "error_code": "PROMETHEUS_TARGET_DOWN" if health == "down" else None,
            "raw_payload": json.dumps(data),
            "metadata": {
                "job": labels.get("job"),
                "instance": labels.get("instance"),
                "health": health,
                "labels": labels
            }
        }


class ElasticsearchAdapter(PlatformAdapter):
    async def fetch_logs(self) -> list[dict]:
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


class DatadogAdapter(PlatformAdapter):
    async def fetch_logs(self) -> list[dict]:
        api_key = self.config.get("api_key")
        app_key = self.config.get("app_key")
        site = self.config.get("site", "datadoghq.com")
        
        if not api_key or not app_key:
            logger.error("datadog_missing_keys")
            return []
        
        try:
            headers = {
                "DD-API-KEY": api_key,
                "DD-APPLICATION-KEY": app_key
            }
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"https://api.{site}/api/v1/monitor",
                    headers=headers
                )
                response.raise_for_status()
                
                monitors = response.json()
                logs = []
                
                for monitor in monitors[:10]:
                    logs.append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "monitor",
                        "data": monitor
                    })
                
                logger.info("datadog_logs_fetched", count=len(logs))
                return logs
        except Exception as e:
            logger.error("datadog_fetch_failed", error=str(e))
            return []
    
    def parse_log(self, raw_log: dict) -> dict:
        data = raw_log.get("data", {})
        
        monitor_id = data.get("id", "unknown")
        name = data.get("name", "unknown")
        state = data.get("overall_state", "unknown")
        
        severity = "CRITICAL" if state == "alert" else "WARNING" if state == "warn" else "INFO"
        
        return {
            "source": "datadog",
            "severity": severity,
            "service_name": f"Datadog-{name}",
            "message": f"Monitor {monitor_id}: {state}",
            "error_code": "DATADOG_ALERT" if state == "alert" else None,
            "raw_payload": json.dumps(data),
            "metadata": {
                "monitor_id": monitor_id,
                "name": name,
                "state": state,
                "type": data.get("type")
            }
        }


PLATFORM_ADAPTERS = {
    "redis": RedisAdapter,
    "kubernetes": KubernetesAdapter,
    "kafka": KafkaAdapter,
    "vercel": VercelAdapter,
    "docker": DockerAdapter,
    "prometheus": PrometheusAdapter,
    "elasticsearch": ElasticsearchAdapter,
    "datadog": DatadogAdapter,
}


def get_adapter(platform: str, client_id: str, config: dict) -> Optional[PlatformAdapter]:
    adapter_class = PLATFORM_ADAPTERS.get(platform.lower())
    if not adapter_class:
        logger.error("unknown_platform", platform=platform)
        return None
    
    return adapter_class(client_id, config)
