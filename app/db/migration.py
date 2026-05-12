import asyncio
import json
import os
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.db.database import engine, Base, AsyncSessionLocal
from app.db.models import Report

OUTPUTS_DIR = Path("outputs")
REPORTS_CATALOG_PATH = OUTPUTS_DIR / "reports_catalog.json"

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def migrate_json_to_sqlite():
    if not REPORTS_CATALOG_PATH.is_file():
        print("No legacy catalog found to migrate.")
        return

    print("Found legacy JSON catalog. Migrating data...")
    try:
        raw = REPORTS_CATALOG_PATH.read_text(encoding="utf-8")
        cat = json.loads(raw)
    except Exception as e:
        print(f"Error reading legacy catalog: {e}")
        return

    async with AsyncSessionLocal() as session:
        for user, items in cat.items():
            if not isinstance(items, list):
                continue
            for entry in items:
                report_id = str(entry.get("id"))
                existing = await session.get(Report, report_id)
                if not existing:
                    report = Report(
                        id=report_id,
                        user=user,
                        title=entry.get("title", "Без названия"),
                        audio_file=entry.get("audio_file"),
                        audio_bytes=entry.get("audio_bytes"),
                        transcript_file=entry.get("transcript_file"),
                        report_file=entry.get("report_file")
                    )
                    # For dates, we could parse 'created_at', but it's okay to let SQLAlchemy handle default
                    # or keep it simple if format is known. We will just use the string if we modify the model,
                    # but here model uses DateTime so we leave created_at to default or parse it if needed.
                    # For a robust migration we might parse entry.get("created_at") here.
                    session.add(report)
        await session.commit()
    print("Migration complete.")
    # Optional: rename the JSON file so we don't migrate again
    REPORTS_CATALOG_PATH.rename(OUTPUTS_DIR / "reports_catalog.json.bak")

if __name__ == "__main__":
    asyncio.run(init_db())
    asyncio.run(migrate_json_to_sqlite())
