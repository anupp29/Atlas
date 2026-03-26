from .redis_adapter import RedisAdapter
from .kafka_adapter import KafkaAdapter
from .kubernetes_adapter import KubernetesAdapter
from .vercel_adapter import VercelAdapter
from .docker_adapter import DockerAdapter
from .prometheus_adapter import PrometheusAdapter
from .elasticsearch_adapter import ElasticsearchAdapter
from .datadog_adapter import DatadogAdapter
from .aws_adapter import AWSAdapter
from .gcp_adapter import GCPAdapter
from .azure_adapter import AzureAdapter
from .mongodb_adapter import MongoDBAdapter
from .mysql_adapter import MySQLAdapter
from .newrelic_adapter import NewRelicAdapter
from .splunk_adapter import SplunkAdapter

ADAPTERS = {
    "redis": RedisAdapter,
    "kafka": KafkaAdapter,
    "kubernetes": KubernetesAdapter,
    "vercel": VercelAdapter,
    "docker": DockerAdapter,
    "prometheus": PrometheusAdapter,
    "elasticsearch": ElasticsearchAdapter,
    "datadog": DatadogAdapter,
    "aws": AWSAdapter,
    "gcp": GCPAdapter,
    "azure": AzureAdapter,
    "mongodb": MongoDBAdapter,
    "mysql": MySQLAdapter,
    "newrelic": NewRelicAdapter,
    "splunk": SplunkAdapter,
}


def get_adapter(platform: str, client_id: str, config: dict):
    adapter_class = ADAPTERS.get(platform.lower())
    if not adapter_class:
        return None
    return adapter_class(client_id, config)
