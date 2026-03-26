import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import structlog
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import sqlite3
from contextlib import asynccontextmanager

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


class LogSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"


class LogSource(str, Enum):
    JAVA = "java"
    POSTGRES = "postgres"
    NODEJS = "nodejs"
    REDIS = "redis"
    SYSTEM = "system"


@dataclass
class MonitoredLogEntry:
    log_id: str
    client_id: str
    timestamp: str
    source: LogSource
    severity: LogSeverity
    service_name: str
    message: str
    error_code: Optional[str]
    raw_payload: str
    metadata: dict
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


class LogMonitorDB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS monitored_logs (
                    log_id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    service_name TEXT NOT NULL,
                    message TEXT NOT NULL,
                    error_code TEXT,
                    raw_payload TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    INDEX idx_client_timestamp (client_id, timestamp),
                    INDEX idx_severity (severity),
                    INDEX idx_source (source)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS log_stats (
                    stat_id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    total_logs INTEGER NOT NULL,
                    error_count INTEGER NOT NULL,
                    warning_count INTEGER NOT NULL,
                    last_updated TEXT NOT NULL,
                    UNIQUE(client_id, source)
                )
            """)
            conn.commit()
    
    async def insert_log(self, entry: MonitoredLogEntry) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._insert_log_sync,
            entry
        )
    
    def _insert_log_sync(self, entry: MonitoredLogEntry) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO monitored_logs 
                    (log_id, client_id, timestamp, source, severity, service_name, 
                     message, error_code, raw_payload, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry.log_id,
                    entry.client_id,
                    entry.timestamp,
                    entry.source.value,
                    entry.severity.value,
                    entry.service_name,
                    entry.message,
                    entry.error_code,
                    entry.raw_payload,
                    json.dumps(entry.metadata),
                    datetime.utcnow().isoformat()
                ))
                conn.commit()
                logger.info("log_inserted", log_id=entry.log_id, client_id=entry.client_id)
        except Exception as e:
            logger.error("log_insert_failed", error=str(e), log_id=entry.log_id)
            raise
    
    async def query_logs(
        self,
        client_id: str,
        source: Optional[LogSource] = None,
        severity: Optional[LogSeverity] = None,
        limit: int = 100
    ) -> list[dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._query_logs_sync,
            client_id,
            source,
            severity,
            limit
        )
    
    def _query_logs_sync(
        self,
        client_id: str,
        source: Optional[LogSource],
        severity: Optional[LogSeverity],
        limit: int
    ) -> list[dict]:
        query = "SELECT * FROM monitored_logs WHERE client_id = ?"
        params = [client_id]
        
        if source:
            query += " AND source = ?"
            params.append(source.value)
        
        if severity:
            query += " AND severity = ?"
            params.append(severity.value)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]


class LogMonitor:
    def __init__(
        self,
        client_id: str,
        db_path: str,
        log_dir: str,
        buffer_size: int = 100,
        flush_interval: float = 5.0
    ):
        if not client_id:
            raise ValueError("client_id is mandatory")
        
        self.client_id = client_id
        self.db = LogMonitorDB(db_path)
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        self.buffer: list[MonitoredLogEntry] = []
        self._lock = asyncio.Lock()
        self._running = False
        self._stats = {
            "total_processed": 0,
            "errors": 0,
            "warnings": 0,
            "last_flush": datetime.utcnow().isoformat()
        }
    
    def _generate_log_id(self, entry_data: str) -> str:
        return hashlib.sha256(
            f"{self.client_id}{entry_data}{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]
    
    async def ingest_log(
        self,
        source: LogSource,
        severity: LogSeverity,
        service_name: str,
        message: str,
        raw_payload: str,
        error_code: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        if not message or not raw_payload:
            raise ValueError("message and raw_payload are mandatory")
        
        log_id = self._generate_log_id(raw_payload)
        
        entry = MonitoredLogEntry(
            log_id=log_id,
            client_id=self.client_id,
            timestamp=datetime.utcnow().isoformat(),
            source=source,
            severity=severity,
            service_name=service_name,
            message=message,
            error_code=error_code,
            raw_payload=raw_payload,
            metadata=metadata or {}
        )
        
        async with self._lock:
            self.buffer.append(entry)
            self._stats["total_processed"] += 1
            
            if severity == LogSeverity.ERROR:
                self._stats["errors"] += 1
            elif severity == LogSeverity.WARNING:
                self._stats["warnings"] += 1
            
            if len(self.buffer) >= self.buffer_size:
                await self._flush_buffer()
        
        logger.info(
            "log_ingested",
            log_id=log_id,
            client_id=self.client_id,
            source=source.value,
            severity=severity.value
        )
        
        return log_id
    
    async def _flush_buffer(self) -> None:
        if not self.buffer:
            return
        
        try:
            for entry in self.buffer:
                await self.db.insert_log(entry)
            
            await self._write_to_file(self.buffer)
            self._stats["last_flush"] = datetime.utcnow().isoformat()
            
            logger.info(
                "buffer_flushed",
                client_id=self.client_id,
                count=len(self.buffer)
            )
            
            self.buffer.clear()
        except Exception as e:
            logger.error("flush_failed", client_id=self.client_id, error=str(e))
            raise
    
    async def _write_to_file(self, entries: list[MonitoredLogEntry]) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._write_to_file_sync, entries)
    
    def _write_to_file_sync(self, entries: list[MonitoredLogEntry]) -> None:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        file_path = self.log_dir / f"{self.client_id}_logs_{timestamp}.jsonl"
        
        try:
            with open(file_path, "a") as f:
                for entry in entries:
                    f.write(entry.to_json() + "\n")
            
            logger.info("logs_written_to_file", file_path=str(file_path), count=len(entries))
        except Exception as e:
            logger.error("file_write_failed", file_path=str(file_path), error=str(e))
            raise
    
    async def start(self) -> None:
        self._running = True
        logger.info("monitor_started", client_id=self.client_id)
        
        try:
            while self._running:
                await asyncio.sleep(self.flush_interval)
                async with self._lock:
                    await self._flush_buffer()
        except asyncio.CancelledError:
            logger.info("monitor_cancelled", client_id=self.client_id)
            async with self._lock:
                await self._flush_buffer()
        except Exception as e:
            logger.error("monitor_error", client_id=self.client_id, error=str(e))
            raise
    
    async def stop(self) -> None:
        self._running = False
        async with self._lock:
            await self._flush_buffer()
        logger.info("monitor_stopped", client_id=self.client_id, stats=self._stats)
    
    def get_stats(self) -> dict:
        return self._stats.copy()


@asynccontextmanager
async def monitor_context(
    client_id: str,
    db_path: str,
    log_dir: str
):
    monitor = LogMonitor(client_id, db_path, log_dir)
    task = asyncio.create_task(monitor.start())
    
    try:
        yield monitor
    finally:
        await monitor.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
