"""
All ChromaDB interactions for ATLAS.
Collections are namespaced per client: atlas_{client_id}.
No other module accesses ChromaDB directly.
"""

from __future__ import annotations

import os
from typing import Any

import chromadb
import structlog
from chromadb.config import Settings
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

logger = structlog.get_logger(__name__)

_EMBEDDING_MODEL = "onnx-mini-lm-l6-v2"  # onnxruntime backend, no TF/Keras dependency


class ChromaDBClient:
    """
    Manages ChromaDB collections for all ATLAS clients.
    Each client has an isolated namespaced collection: atlas_{client_id}.
    Embeddings use a local sentence-transformer model — no external API calls.
    """

    def __init__(self) -> None:
        path = os.environ.get("CHROMADB_PATH")
        if not path:
            raise EnvironmentError("Required environment variable 'CHROMADB_PATH' is not set.")

        self._client = chromadb.PersistentClient(
            path=path,
            settings=Settings(anonymized_telemetry=False),
        )
        self._embedding_fn = ONNXMiniLM_L6_V2()
        logger.info("chromadb_client.initialised", path=path, embedding_model=_EMBEDDING_MODEL)

    def _collection_name(self, client_id: str) -> str:
        return f"atlas_{client_id}"

    def get_or_create_collection(self, client_id: str) -> chromadb.Collection:
        """Get or create the namespaced collection for a client."""
        name = self._collection_name(client_id)
        collection = self._client.get_or_create_collection(
            name=name,
            embedding_function=self._embedding_fn,
            metadata={"client_id": client_id, "embedding_model": _EMBEDDING_MODEL},
        )
        logger.info("chromadb_client.collection_ready", collection=name, client_id=client_id)
        return collection

    def embed_and_store(self, incident_record: dict[str, Any], client_id: str) -> None:
        """
        Generate embedding and store an incident record in the client's collection.

        Args:
            incident_record: Must include 'incident_id' and text fields for embedding.
            client_id: Client scope — determines which collection to write to.

        Raises:
            ValueError: If incident_record is missing required fields.
        """
        required = {"incident_id", "anomaly_type", "root_cause", "resolution_steps"}
        missing = required - incident_record.keys()
        if missing:
            raise ValueError(f"incident_record missing required fields: {missing}")

        collection = self.get_or_create_collection(client_id)

        # Validate stored model matches
        stored_model = collection.metadata.get("embedding_model")
        if stored_model and stored_model != _EMBEDDING_MODEL:
            raise ValueError(
                f"Embedding model mismatch: collection uses '{stored_model}' "
                f"but client is configured for '{_EMBEDDING_MODEL}'. "
                "Re-seed the collection with the correct model."
            )

        document = self._build_document_text(incident_record)
        metadata = {k: str(v) for k, v in incident_record.items() if k != "incident_id"}
        metadata["client_id"] = client_id

        collection.upsert(
            ids=[incident_record["incident_id"]],
            documents=[document],
            metadatas=[metadata],
        )
        logger.info(
            "chromadb_client.stored",
            incident_id=incident_record["incident_id"],
            client_id=client_id,
        )

    def similarity_search(
        self,
        query_text: str,
        client_id: str,
        n_results: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Search only the specified client's collection. Never cross-client.

        Args:
            query_text: Natural language description of the current incident.
            client_id: Client scope.
            n_results: Number of results to return.

        Returns:
            List of dicts with 'incident_id', 'similarity_score', and metadata fields.
        """
        collection = self.get_or_create_collection(client_id)
        count = collection.count()
        if count == 0:
            logger.info("chromadb_client.empty_collection", client_id=client_id)
            return []

        actual_n = min(n_results, count)
        results = collection.query(
            query_texts=[query_text],
            n_results=actual_n,
            include=["documents", "metadatas", "distances"],
        )

        output: list[dict] = []
        for i, doc_id in enumerate(results["ids"][0]):
            distance = results["distances"][0][i]
            # ChromaDB with ONNXMiniLM returns cosine distance in [0, 2].
            # Cosine similarity = 1 - cosine_distance, clamped to [0, 1].
            # A distance of 0 = identical vectors (similarity 1.0).
            # A distance of 2 = maximally opposite (similarity 0.0, clamped).
            similarity = max(0.0, min(1.0, 1.0 - distance))
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            output.append({
                "incident_id": doc_id,
                "similarity_score": round(similarity, 4),
                "document": results["documents"][0][i],
                "source": "client_specific",
                **meta,
            })

        logger.info(
            "chromadb_client.search_complete",
            client_id=client_id,
            results=len(output),
            top_score=output[0]["similarity_score"] if output else 0,
        )
        return output

    def cross_client_search(
        self,
        query_text: str,
        tech_stack: list[str],
        exclude_client_id: str,
        n_results: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Search across all client collections for the same technology stack.
        Results are anonymised — client_id stripped before return.
        Only called when the requesting client has fewer than 5 incidents (cold start).

        Args:
            query_text: Incident description.
            tech_stack: List of technology types to match (e.g. ['java-spring-boot', 'postgresql']).
            exclude_client_id: The requesting client — never included in cross-client results.
            n_results: Max results to return.

        Returns:
            List of anonymised result dicts flagged with source='cross_client_anonymised'.
        """
        all_collections = self._client.list_collections()
        results: list[dict] = []

        for col_meta in all_collections:
            col_name = col_meta.name
            if not col_name.startswith("atlas_"):
                continue
            col_client_id = col_name[len("atlas_"):]
            if col_client_id == exclude_client_id:
                continue

            try:
                collection = self._client.get_collection(
                    name=col_name,
                    embedding_function=self._embedding_fn,
                )
                if collection.count() == 0:
                    continue

                col_results = collection.query(
                    query_texts=[query_text],
                    n_results=min(n_results, collection.count()),
                    include=["documents", "metadatas", "distances"],
                )

                for i, doc_id in enumerate(col_results["ids"][0]):
                    distance = col_results["distances"][0][i]
                    # Same cosine distance → similarity conversion as similarity_search
                    similarity = max(0.0, min(1.0, 1.0 - distance))
                    meta = col_results["metadatas"][0][i] if col_results["metadatas"] else {}
                    # Strip all client-identifying metadata
                    anonymised_meta = {
                        k: v for k, v in meta.items()
                        if k not in ("client_id", "incident_id")
                    }
                    results.append({
                        "incident_id": f"CROSS_CLIENT_{i}",
                        "similarity_score": round(similarity, 4),
                        "document": col_results["documents"][0][i],
                        "source": "cross_client_anonymised",
                        **anonymised_meta,
                    })
            except Exception as exc:
                logger.warning(
                    "chromadb_client.cross_client_search_error",
                    collection=col_name,
                    error=str(exc),
                )
                continue

        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        top = results[:n_results]
        logger.info(
            "chromadb_client.cross_client_search_complete",
            exclude_client=exclude_client_id,
            results=len(top),
        )
        return top

    def health_check(self) -> bool:
        """Verify ChromaDB is accessible."""
        try:
            self._client.list_collections()
            return True
        except Exception as exc:
            logger.error("chromadb_client.health_check.failed", error=str(exc))
            return False

    @staticmethod
    def _build_document_text(record: dict[str, Any]) -> str:
        """Build the text document used for embedding from an incident record."""
        parts = [
            record.get("service_name", ""),
            record.get("anomaly_type", ""),
            " ".join(record.get("error_codes_observed", [])),
            record.get("root_cause", ""),
            record.get("resolution_steps", ""),
        ]
        return " ".join(p for p in parts if p).strip()
