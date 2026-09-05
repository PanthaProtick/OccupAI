from __future__ import annotations

import argparse
from pathlib import Path
from sqlalchemy.engine import make_url

from alembic import command
from alembic.config import Config

from backend.config import PROJECT_ROOT, Settings
from backend.database import create_database_engine, make_session_factory
from backend.maintenance import (
    aggregate_five_minute_buckets, apply_retention, backup_sqlite_database,
    import_history, import_live_states, reset_database, seed_canonical,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="OccupAI database maintenance")
    parser.add_argument("command", choices=("migrate", "seed", "reset", "import-history", "aggregate", "retention", "backup"))
    parser.add_argument("--path", type=Path, default=PROJECT_ROOT / "mock" / "generated" / "history_5min_7days.json")
    args = parser.parse_args()
    settings = Settings.from_env()
    url = make_url(settings.database_url)
    if url.get_backend_name() == "sqlite" and url.database and url.database != ":memory:":
        Path(url.database).resolve().parent.mkdir(parents=True, exist_ok=True)
    if args.command == "migrate":
        config = Config(str(PROJECT_ROOT / "alembic.ini"))
        config.set_main_option("sqlalchemy.url", settings.database_url)
        command.upgrade(config, "head")
        return
    if args.command == "backup":
        backup_sqlite_database(settings.database_url, args.path)
        print(f"Backed up database to {args.path}")
        return
    engine = create_database_engine(settings.database_url, settings.sqlite_busy_timeout_ms)
    sessions = make_session_factory(engine)
    if args.command == "reset":
        reset_database(sessions)
        seed_canonical(sessions, settings.mock_data_dir)
        history_count = import_history(sessions, settings.mock_data_dir / "history_5min_7days.json")
        state_count = import_live_states(sessions, settings.mock_data_dir / "live_occupancy.json")
        print(f"Reset database: seeded {state_count} rooms/camera states and {history_count} history buckets")
    elif args.command == "seed":
        seed_canonical(sessions, settings.mock_data_dir)
    elif args.command == "import-history":
        print(f"Imported {import_history(sessions, args.path)} buckets")
    elif args.command == "aggregate":
        print(f"Aggregated {aggregate_five_minute_buckets(sessions)} buckets")
    else:
        print(apply_retention(sessions, settings.raw_sample_retention_days,
                              settings.aggregate_retention_days, settings.retention_batch_size))
    engine.dispose()


if __name__ == "__main__":
    main()
