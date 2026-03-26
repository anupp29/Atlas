"""
Log Processor - Captures, processes, and streams logs for monitoring
Standalone script with no UI dependencies
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Callable, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import structlog
from pathlib import Path

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


class LogLevel(str, Enum):
    """Log severity levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogSource(str, Enum):
    """Log sources"""
    SYSTEM = "SYSTEM"
    APPLICATION = "APPLICATION"
    DATABASE = "DATABASE"
    NETWORK = "NETWORK"
    SECURITY = "SECURITY"
    CUSTOM = "CUSTOM"


@dataclass
class LogEntry:
    """Structured log entry"""
    timestamp: str
    level: LogLevel
    source: LogSource
    message: str
    service_name: str
    client_id: str
    metadata: dict
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    error_code: Optional[str] = None
    stack_trace: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), default=str)


class LogProcessor:
    """Process and stream logs for monitoring"""

    def __init__(
        self,
        service_name: str,
        client_id: str,
        log_file: Optional[str] = None,
        buffer_size: int = 100,
    ):
        """
        Initialize log processor

        Args:
            service_name: Name of the service
            client_id: Client identifier
            log_file: Optional file to write logs
            buffer_size: Number of logs to buffer before processing
        """
        self.service_name = service_name
        self.client_id = client_id
        self.log_file = log_file
        self.buffer_size = buffer_size
        self.log_buffer: list[LogEntry] = []
        self.callbacks: list[Callable[[LogEntry], None]] = []
        self.error_count = 0
        self.warning_count = 0
        self.info_count = 0

        if log_file:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            "log_processor_initialized",
            service_name=service_name,
            client_id=client_id,
            log_file=log_file,
        )

    def add_callback(self, callback: Callable[[LogEntry], None]) -> None:
        """
        Add callback to be called when log is processed

        Args:
            callback: Function to call with LogEntry
        """
        self.callbacks.append(callback)
        logger.info("callback_added", callback_name=callback.__name__)

    async def process_log(
        self,
        level: LogLevel,
        source: LogSource,
        message: str,
        metadata: Optional[dict] = None,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        error_code: Optional[str] = None,
        stack_trace: Optional[str] = None,
    ) -> LogEntry:
        """
        Process a log entry

        Args:
            level: Log level
            source: Log source
            message: Log message
            metadata: Additional metadata
            trace_id: Trace ID for correlation
            span_id: Span ID for tracing
            error_code: Error code if applicable
            stack_trace: Stack trace if applicable

        Returns:
            Processed LogEntry
        """
        try:
            log_entry = LogEntry(
                timestamp=datetime.utcnow().isoformat(),
                level=level,
                source=source,
                message=message,
                service_name=self.service_name,
                client_id=self.client_id,
                metadata=metadata or {},
                trace_id=trace_id,
                span_id=span_id,
                error_code=error_code,
                stack_trace=stack_trace,
            )

            # Update counters
            if level == LogLevel.ERROR:
                self.error_count += 1
            elif level == LogLevel.WARNING:
                self.warning_count += 1
            elif level == LogLevel.INFO:
                self.info_count += 1

            # Add to buffer
            self.log_buffer.append(log_entry)

            # Write to file if configured
            if self.log_file:
                await self._write_to_file(log_entry)

            # Call callbacks
            for callback in self.callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(log_entry)
                    else:
                        callback(log_entry)
                except Exception as e:
                    logger.error(
                        "callback_error",
                        callback_name=callback.__name__,
                        error=str(e),
                    )

            # Flush buffer if needed
            if len(self.log_buffer) >= self.buffer_size:
                await self.flush_buffer()

            return log_entry

        except Exception as e:
            logger.error("log_processing_error", error=str(e), stack_trace=str(e))
            raise

    async def _write_to_file(self, log_entry: LogEntry) -> None:
        """Write log entry to file"""
        try:
            with open(self.log_file, "a") as f:
                f.write(log_entry.to_json() + "\n")
        except Exception as e:
            logger.error("file_write_error", error=str(e))

    async def flush_buffer(self) -> None:
        """Flush log buffer"""
        if not self.log_buffer:
            return

        try:
            logger.info(
                "buffer_flush",
                buffer_size=len(self.log_buffer),
                error_count=self.error_count,
                warning_count=self.warning_count,
                info_count=self.info_count,
            )
            self.log_buffer.clear()
        except Exception as e:
            logger.error("buffer_flush_error", error=str(e))

    def get_stats(self) -> dict:
        """Get log statistics"""
        return {
            "service_name": self.service_name,
            "client_id": self.client_id,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "buffer_size": len(self.log_buffer),
            "timestamp": datetime.utcnow().isoformat(),
        }


class LogStream:
    """Stream logs to external systems"""

    def __init__(self, processor: LogProcessor):
        """
        Initialize log stream

        Args:
            processor: LogProcessor instance
        """
        self.processor = processor
        self.streams: dict[str, Callable] = {}

    def add_stream(self, name: str, handler: Callable[[LogEntry], None]) -> None:
        """
        Add log stream handler

        Args:
            name: Stream name
            handler: Handler function
        """
        self.streams[name] = handler
        self.processor.add_callback(handler)
        logger.info("stream_added", stream_name=name)

    async def stream_to_http(
        self,
        url: str,
        headers: Optional[dict] = None,
    ) -> Callable[[LogEntry], None]:
        """
        Create HTTP stream handler

        Args:
            url: HTTP endpoint URL
            headers: Optional HTTP headers

        Returns:
            Handler function
        """
        import aiohttp

        async def handler(log_entry: LogEntry) -> None:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url,
                        json=log_entry.to_dict(),
                        headers=headers or {},
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as response:
                        if response.status != 200:
                            logger.warning(
                                "http_stream_error",
                                status=response.status,
                                url=url,
                            )
            except Exception as e:
                logger.error("http_stream_error", error=str(e), url=url)

        return handler

    async def stream_to_kafka(
        self,
        brokers: list[str],
        topic: str,
    ) -> Callable[[LogEntry], None]:
        """
        Create Kafka stream handler

        Args:
            brokers: Kafka broker addresses
            topic: Kafka topic

        Returns:
            Handler function
        """
        from aiokafka import AIOKafkaProducer

        producer = AIOKafkaProducer(
            bootstrap_servers=brokers,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        )
        await producer.start()

        async def handler(log_entry: LogEntry) -> None:
            try:
                await producer.send_and_wait(topic, log_entry.to_dict())
            except Exception as e:
                logger.error("kafka_stream_error", error=str(e), topic=topic)

        return handler

    async def stream_to_elasticsearch(
        self,
        hosts: list[str],
        index: str,
    ) -> Callable[[LogEntry], None]:
        """
        Create Elasticsearch stream handler

        Args:
            hosts: Elasticsearch hosts
            index: Index name

        Returns:
            Handler function
        """
        from elasticsearch import Elasticsearch

        es = Elasticsearch(hosts)

        async def handler(log_entry: LogEntry) -> None:
            try:
                es.index(index=index, document=log_entry.to_dict())
            except Exception as e:
                logger.error("elasticsearch_stream_error", error=str(e), index=index)

        return handler


async def example_usage():
    """Example usage of log processor"""
    # Create processor
    processor = LogProcessor(
        service_name="payment-service",
        client_id="FINCORE_UK_001",
        log_file="logs/payment_service.log",
    )

    # Add console callback
    def console_callback(log_entry: LogEntry) -> None:
        print(f"[{log_entry.level}] {log_entry.message}")

    processor.add_callback(console_callback)

    # Process some logs
    await processor.process_log(
        level=LogLevel.INFO,
        source=LogSource.APPLICATION,
        message="Payment service started",
        metadata={"version": "1.0.0"},
    )

    await processor.process_log(
        level=LogLevel.WARNING,
        source=LogSource.DATABASE,
        message="Database connection slow",
        metadata={"latency_ms": 250},
    )

    await processor.process_log(
        level=LogLevel.ERROR,
        source=LogSource.NETWORK,
        message="Failed to connect to payment gateway",
        error_code="GATEWAY_TIMEOUT",
        metadata={"retry_count": 3},
    )

    # Get stats
    stats = processor.get_stats()
    print(f"\nLog Statistics: {json.dumps(stats, indent=2)}")

    # Flush buffer
    await processor.flush_buffer()


if __name__ == "__main__":
    asyncio.run(example_usage())
