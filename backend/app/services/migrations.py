from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine


SCHEMA_MIGRATIONS_TABLE = "schema_migrations"


@dataclass(frozen=True)
class ColumnSpec:
    table: str
    column: str
    ddl: str


@dataclass(frozen=True)
class Migration:
    migration_id: str
    name: str
    operations: tuple[str, ...]
    apply: Callable[[Connection], None]

    @property
    def checksum(self) -> str:
        payload = "|".join((self.migration_id, self.name, *self.operations))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


PLATFORM_PRESET_RULE_COLUMNS = (
    ColumnSpec("platform_presets", "rule_type", "rule_type TEXT NOT NULL DEFAULT 'organic'"),
    ColumnSpec("platform_presets", "source_url", "source_url TEXT"),
    ColumnSpec("platform_presets", "source_checked_at", "source_checked_at TEXT"),
    ColumnSpec("platform_presets", "max_duration_seconds", "max_duration_seconds INTEGER"),
    ColumnSpec("platform_presets", "max_file_size_mb", "max_file_size_mb INTEGER"),
    ColumnSpec("platform_presets", "min_width", "min_width INTEGER"),
    ColumnSpec("platform_presets", "min_height", "min_height INTEGER"),
    ColumnSpec("platform_presets", "min_bitrate_kbps", "min_bitrate_kbps INTEGER"),
    ColumnSpec("platform_presets", "safe_zone_json", "safe_zone_json TEXT NOT NULL DEFAULT '{}'"),
    ColumnSpec("platform_presets", "notes", "notes TEXT NOT NULL DEFAULT ''"),
)

BATCH_OUTPUT_COLUMNS = (
    ColumnSpec("batches", "output_dir", "output_dir TEXT"),
)

RENDER_PERFORMANCE_COLUMNS = (
    ColumnSpec("rendered_videos", "size_bytes", "size_bytes INTEGER"),
    ColumnSpec("rendered_videos", "render_seconds", "render_seconds REAL"),
)

QUEUE_CONTROL_COLUMNS = (
    ColumnSpec("batches", "is_paused", "is_paused INTEGER NOT NULL DEFAULT 0"),
    ColumnSpec("render_jobs", "cancel_requested", "cancel_requested INTEGER NOT NULL DEFAULT 0"),
)

RENDER_MEMORY_COLUMNS = (
    ColumnSpec("rendered_videos", "peak_rss_bytes", "peak_rss_bytes INTEGER"),
)

RENDER_QUALITY_CACHE_COLUMNS = (
    ColumnSpec("rendered_videos", "quality_cache_json", "quality_cache_json TEXT"),
)


def _quote_identifier(value: str) -> str:
    if not value.replace("_", "").isalnum():
        raise ValueError(f"Identificador SQL invalido: {value}")
    return f'"{value}"'


def _table_exists(connection: Connection, table_name: str) -> bool:
    query = text("select 1 from sqlite_master where type='table' and name=:name")
    return connection.execute(query, {"name": table_name}).first() is not None


def _column_names(connection: Connection, table_name: str) -> set[str]:
    if not _table_exists(connection, table_name):
        return set()
    rows = connection.execute(text(f"PRAGMA table_info({_quote_identifier(table_name)})")).mappings()
    return {str(row["name"]) for row in rows}


def _ensure_column(connection: Connection, spec: ColumnSpec) -> bool:
    if not _table_exists(connection, spec.table):
        return False
    if spec.column in _column_names(connection, spec.table):
        return False
    connection.execute(text(f"ALTER TABLE {_quote_identifier(spec.table)} ADD COLUMN {spec.ddl}"))
    return True


def _ensure_schema_migrations_table(connection: Connection) -> None:
    connection.execute(
        text(
            f"""
            CREATE TABLE IF NOT EXISTS {_quote_identifier(SCHEMA_MIGRATIONS_TABLE)} (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                checksum TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )
            """
        )
    )


def _applied_migrations(connection: Connection) -> set[str]:
    _ensure_schema_migrations_table(connection)
    rows = connection.execute(text(f"SELECT id FROM {_quote_identifier(SCHEMA_MIGRATIONS_TABLE)}"))
    return {str(row[0]) for row in rows}


def _record_migration(connection: Connection, migration: Migration, applied: set[str]) -> None:
    if migration.migration_id in applied:
        return
    connection.execute(
        text(
            f"""
            INSERT INTO {_quote_identifier(SCHEMA_MIGRATIONS_TABLE)}
                (id, name, checksum, applied_at)
            VALUES
                (:id, :name, :checksum, :applied_at)
            """
        ),
        {
            "id": migration.migration_id,
            "name": migration.name,
            "checksum": migration.checksum,
            "applied_at": datetime.now(UTC).replace(tzinfo=None).isoformat(),
        },
    )
    applied.add(migration.migration_id)


def _apply_schema_migrations_table(_connection: Connection) -> None:
    return None


def _apply_platform_preset_rule_metadata(connection: Connection) -> None:
    for spec in PLATFORM_PRESET_RULE_COLUMNS:
        _ensure_column(connection, spec)


def _apply_batch_output_dir(connection: Connection) -> None:
    for spec in BATCH_OUTPUT_COLUMNS:
        _ensure_column(connection, spec)


def _apply_render_performance_metrics(connection: Connection) -> None:
    for spec in RENDER_PERFORMANCE_COLUMNS:
        _ensure_column(connection, spec)


def _apply_queue_controls(connection: Connection) -> None:
    for spec in QUEUE_CONTROL_COLUMNS:
        _ensure_column(connection, spec)


def _apply_render_memory_metrics(connection: Connection) -> None:
    for spec in RENDER_MEMORY_COLUMNS:
        _ensure_column(connection, spec)


def _apply_render_quality_cache(connection: Connection) -> None:
    for spec in RENDER_QUALITY_CACHE_COLUMNS:
        _ensure_column(connection, spec)


INDEX_OPERATIONS = (
    ("render_jobs", "CREATE INDEX IF NOT EXISTS ix_render_jobs_queue ON render_jobs (status, cancel_requested, created_at)"),
    ("render_jobs", "CREATE INDEX IF NOT EXISTS ix_render_jobs_batch_id ON render_jobs (batch_id)"),
    ("download_jobs", "CREATE INDEX IF NOT EXISTS ix_download_jobs_queue ON download_jobs (status, created_at)"),
    ("batches", "CREATE INDEX IF NOT EXISTS ix_batches_created_at ON batches (created_at)"),
    ("rendered_videos", "CREATE INDEX IF NOT EXISTS ix_rendered_videos_status ON rendered_videos (status)"),
)


def _apply_performance_indexes(connection: Connection) -> None:
    for table, sql in INDEX_OPERATIONS:
        if _table_exists(connection, table):
            connection.execute(text(sql))


MIGRATIONS = (
    Migration(
        migration_id="20260619_0000_schema_migrations_table",
        name="Create schema migrations registry",
        operations=("CREATE TABLE schema_migrations",),
        apply=_apply_schema_migrations_table,
    ),
    Migration(
        migration_id="20260619_0001_platform_preset_rule_metadata",
        name="Add platform preset rule metadata",
        operations=tuple(f"{spec.table}.{spec.ddl}" for spec in PLATFORM_PRESET_RULE_COLUMNS),
        apply=_apply_platform_preset_rule_metadata,
    ),
    Migration(
        migration_id="20260709_0002_batch_output_dir",
        name="Add per-batch render output directory",
        operations=tuple(f"{spec.table}.{spec.ddl}" for spec in BATCH_OUTPUT_COLUMNS),
        apply=_apply_batch_output_dir,
    ),
    Migration(
        migration_id="20260711_0003_render_performance_metrics",
        name="Add local render performance metrics",
        operations=tuple(f"{spec.table}.{spec.ddl}" for spec in RENDER_PERFORMANCE_COLUMNS),
        apply=_apply_render_performance_metrics,
    ),
    Migration(
        migration_id="20260711_0004_queue_controls",
        name="Add persistent batch pause and render cancellation controls",
        operations=tuple(f"{spec.table}.{spec.ddl}" for spec in QUEUE_CONTROL_COLUMNS),
        apply=_apply_queue_controls,
    ),
    Migration(
        migration_id="20260716_0005_render_peak_rss",
        name="Add per-render peak RSS metric",
        operations=tuple(f"{spec.table}.{spec.ddl}" for spec in RENDER_MEMORY_COLUMNS),
        apply=_apply_render_memory_metrics,
    ),
    Migration(
        migration_id="20260719_0006_render_quality_cache",
        name="Add persistent render quality analysis cache",
        operations=tuple(f"{spec.table}.{spec.ddl}" for spec in RENDER_QUALITY_CACHE_COLUMNS),
        apply=_apply_render_quality_cache,
    ),
    Migration(
        migration_id="20260909_0007_performance_indexes",
        name="Add strategic query and queue performance indexes",
        operations=tuple(sql for _, sql in INDEX_OPERATIONS),
        apply=_apply_performance_indexes,
    ),
)


def _apply_pragmas(connection: Connection) -> None:
    try:
        connection.execute(text("PRAGMA journal_mode=WAL"))
        connection.execute(text("PRAGMA busy_timeout=30000"))
        connection.execute(text("PRAGMA synchronous=NORMAL"))
        connection.execute(text("PRAGMA wal_autocheckpoint=1000"))
    except Exception:
        pass


def run_schema_upgrades(engine: Engine) -> None:
    """Apply idempotent SQLite schema upgrades after metadata creation."""
    try:
        with engine.connect() as connection:
            _apply_pragmas(connection)
    except Exception:
        pass

    with engine.begin() as connection:
        _ensure_schema_migrations_table(connection)
        applied = _applied_migrations(connection)
        for migration in MIGRATIONS:
            migration.apply(connection)
            _record_migration(connection, migration, applied)
