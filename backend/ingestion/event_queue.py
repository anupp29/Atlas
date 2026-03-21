"""
In-memory async event queue for ATLAS.
One queue per client_id. Strict per-client isolation.
Simulates Kafka behaviour for the MVP.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Maximum events per client queue before oldest are dropped
_MAX_QUEUE_SIZE = 10_000
# Events older than 5 minutes are flagged as stale
_STALE_THRESHOLD_SECONDS = 300
# Warn when queue depth exceeds this
_DEPTH_WARN_THRESHOLD = 1_000


class EventQueue:
    """
    Per-client async event queue.
    Strict isolation: no method allows reading across client queues.
    Events are read-only after entering the queue.
    """

    def __init__(self) -> None:
        # client_id → asyncio.Queue of (event_dict, enqueue_time)
        self._queues: dict[str, asyncio.Queue[tuple[dict[str, Any], datetime]]] = {}
        self._drop_counts: dict[str, int] = {}

    def _get_or_create_queue(self, client_id: str) -> asyncio.Queue[tuple[dict[str, Any], datetime]]:
        """Get or create the queue for a client. Never returns another client's queue."""
        if client_id not in self._queues:
            self._queues[client_id] = asyncio.Queue(maxsize=_MAX_QUEUE_SIZE)
            self._drop_counts[client_id] = 0
            logger.info("event_queue.created", client_id=client_id)
        return self._queues[client_id]

    async def enqueue(self, event: dict[str, Any], client_id: str) -> None:
        """
        Add an enriched event to the client's queue.

        Args:
            event: Normalised enriched event dict. Must have client_id field.
            client_id: The client this event belongs to.

        Raises:
            ValueError: If event client_id does not match the provided client_id.
        """
        event_client = event.get("client_id")
        if event_client != client_id:
            raise ValueError(
                f"Event client_id '{event_client}' does not match queue client_id '{client_id}'. "
                "Multi-tenancy violation — events cannot be enqueued to the wrong client queue."
            )

        queue = self._get_or_create_queue(client_id)
        now = datetime.now(timezone.utc)

        if queue.full():
            # Drop oldest event to make room — log the drop
            try:
                dropped_event, _ = queue.get_nowait()
                self._drop_counts[client_id] += 1
                logger.warning(
                    "event_queue.event_dropped",
                    client_id=client_id,
                    total_drops=self._drop_counts[client_id],
                    dropped_event_id=dropped_event.get("atlas_event_id", "unknown"),
                )
            except asyncio.QueueEmpty:
                pass

        await queue.put((event, now))

        depth = queue.qsize()
        if depth >= _DEPTH_WARN_THRESHOLD:
            logger.warning(
                "event_queue.depth_warning",
                client_id=client_id,
                depth=depth,
                threshold=_DEPTH_WARN_THRESHOLD,
            )

    async def dequeue(self, client_id: str) -> dict[str, Any] | None:
        """
        Get the next event for a client. Blocks until an event is available.

        Args:
            client_id: The client whose queue to read from.

        Returns:
            Event dict, or None if the event is stale (flagged but still returned).
        """
        queue = self._get_or_create_queue(client_id)
        event, enqueue_time = await queue.get()

        age_seconds = (datetime.now(timezone.utc) - enqueue_time).total_seconds()
        if age_seconds > _STALE_THRESHOLD_SECONDS:
            event = {**event, "stale": True, "queue_age_seconds": round(age_seconds, 1)}
            logger.warning(
                "event_queue.stale_event",
                client_id=client_id,
                age_seconds=round(age_seconds, 1),
                event_id=event.get("atlas_event_id", "unknown"),
            )

        return event

    def dequeue_nowait(self, client_id: str) -> dict[str, Any] | None:
        """
        Non-blocking dequeue. Returns None if queue is empty.

        Args:
            client_id: The client whose queue to read from.
        """
        queue = self._get_or_create_queue(client_id)
        try:
            event, enqueue_time = queue.get_nowait()
            age_seconds = (datetime.now(timezone.utc) - enqueue_time).total_seconds()
            if age_seconds > _STALE_THRESHOLD_SECONDS:
                event = {**event, "stale": True, "queue_age_seconds": round(age_seconds, 1)}
            return event
        except asyncio.QueueEmpty:
            return None

    def depth(self, client_id: str) -> int:
        """Return current queue depth for a client."""
        if client_id not in self._queues:
            return 0
        return self._queues[client_id].qsize()

    def drop_count(self, client_id: str) -> int:
        """Return total events dropped for a client due to queue overflow."""
        return self._drop_counts.get(client_id, 0)

    def get_all_client_ids(self) -> list[str]:
        """Return all client IDs that have active queues."""
        return list(self._queues.keys())
