"""Test resume_after_approval directly without HTTP."""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog
structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(20))  # INFO


async def main():
    from backend.orchestrator.pipeline import resume_after_approval

    # Use the first incident that was approved
    thread_id = "FINCORE_UK_001_47bd0eb6-4a60-4c98-86fe-ef221858f877"

    print(f"Resuming thread: {thread_id}")
    result = await resume_after_approval(
        thread_id=thread_id,
        human_action="approved",
        modifier="test.engineer",
    )
    print(f"execution_status: {result.get('execution_status')}")
    print(f"resolution_outcome: {result.get('resolution_outcome')}")
    print(f"human_action: {result.get('human_action')}")
    print(f"routing_decision: {result.get('routing_decision')}")


asyncio.run(main())
