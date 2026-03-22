"""Check checkpoint state for active threads."""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    import aiosqlite
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    conn = await aiosqlite.connect('./data/atlas_checkpoints.db')
    checkpointer = AsyncSqliteSaver(conn)
    await checkpointer.setup()

    count = 0
    async for config, metadata, values, next_nodes, ts in checkpointer.alist({"configurable": {"thread_id": ""}}):
        if next_nodes:
            tid = config["configurable"]["thread_id"]
            print(f"Thread: {tid[:50]}")
            print(f"  Next nodes: {next_nodes}")
            print(f"  human_action: {values.get('human_action', '')!r}")
            print(f"  routing_decision: {values.get('routing_decision', '')!r}")
            print()
            count += 1
            if count >= 5:
                break

    if count == 0:
        print("No threads with pending nodes found.")

    await conn.close()


asyncio.run(main())
