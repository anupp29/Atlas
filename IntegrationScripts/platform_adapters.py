import structlog

from adapters import ADAPTERS, get_adapter

logger = structlog.get_logger()

PLATFORM_ADAPTERS = ADAPTERS

__all__ = ["get_adapter", "PLATFORM_ADAPTERS"]
