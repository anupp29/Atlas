"""
One-time ChromaDB seed script.
Embeds all historical incidents from historical_incidents.json into ChromaDB.
Rate-limited to avoid overwhelming the embedding model.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database.chromadb_client import ChromaDBClient

_INCIDENTS_FILE = Path(__file__).parent.parent / "data" / "seed" / "historical_incidents.json"
_RATE_LIMIT_DELAY = 0.1  # seconds between embeddings


def run() -> None:
    client = ChromaDBClient()

    incidents = json.loads(_INCIDENTS_FILE.read_text(encoding="utf-8"))
    print(f"Seeding {len(incidents)} incidents into ChromaDB...")

    skipped = 0
    for incident in incidents:
        client_id = incident["client_id"]
        try:
            client.embed_and_store(incident, client_id)
            print(f"  ✓ {incident['incident_id']} → {client_id}")
            time.sleep(_RATE_LIMIT_DELAY)
        except Exception as exc:
            print(f"  ✗ {incident['incident_id']} — {exc} (skipping)")
            skipped += 1

    print(f"\nSeeding complete. {len(incidents) - skipped} stored, {skipped} skipped.")

    # Quick count verification
    for client_id in ("FINCORE_UK_001", "RETAILMAX_EU_002"):
        collection = client.get_or_create_collection(client_id)
        count = collection.count()
        print(f"  {client_id}: {count} documents in collection")


if __name__ == "__main__":
    run()
