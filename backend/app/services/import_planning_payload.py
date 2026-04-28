"""CLI: importiert bereinigte Planungs-JSON in die Datenbank.

Aufruf im Backend-Container:
    python -m app.services.import_planning_payload /tmp/planning.json
"""

from __future__ import annotations

import asyncio
import sys

from app.database import async_session
from app.services.planning_import import import_planning_payload_file


async def main(path: str) -> None:
    async with async_session() as db:
        result = await import_planning_payload_file(db, path)
        await db.commit()
        print(result)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m app.services.import_planning_payload <planning.json>")
    asyncio.run(main(sys.argv[1]))
