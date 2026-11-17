from __future__ import annotations

from sqlalchemy import create_engine, inspect, text

from app.database import SessionLocal, engine, init_db
from app.services.migrations import SCHEMA_MIGRATIONS_TABLE, run_schema_upgrades


def test_new_creator_tables_exist():
    init_db()
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    assert "brand_kits" in table_names
    assert "transcripts" in table_names
    assert "clip_candidates" in table_names
    assert "caption_styles" in table_names
    assert "broll_cues" in table_names
    assert "music_tracks" in table_names
    assert "music_stems" in table_names
    assert "creator_profiles" in table_names
    assert "content_ideas" in table_names
    assert "schedule_slots" in table_names
    assert "asset_proxies" in table_names
    assert "scene_markers" in table_names


def test_default_brand_kit_table_is_queryable():
    init_db()
    with SessionLocal() as db:
        count = db.execute(text("select count(*) from brand_kits")).scalar_one()
    assert count >= 0


def test_schema_upgrades_add_platform_rule_columns_to_legacy_database(tmp_path):
    legacy_engine = create_engine(f"sqlite:///{tmp_path / 'legacy.sqlite3'}", future=True)
    with legacy_engine.begin() as connection:
        connection.execute(
            text(
                """
                create table platform_presets (
                    id varchar(32) primary key,
                    platform varchar(80) not null unique,
                    label varchar(120) not null,
                    width integer not null default 1080,
                    height integer not null default 1920,
                    codec varchar(80) not null default 'H.264/AAC',
                    checklist_json text not null
                )
                """
            )
        )
        connection.execute(
            text(
                """
                insert into platform_presets
                    (id, platform, label, width, height, codec, checklist_json)
                values
                    ('preset1', 'youtube_shorts', 'YouTube Shorts', 1080, 1920, 'H.264/AAC', '[]')
                """
            )
        )

    run_schema_upgrades(legacy_engine)
    run_schema_upgrades(legacy_engine)

    inspector = inspect(legacy_engine)
    columns = {column["name"] for column in inspector.get_columns("platform_presets")}
    assert {
        "rule_type",
        "source_url",
        "source_checked_at",
        "max_duration_seconds",
        "max_file_size_mb",
        "min_width",
        "min_height",
        "min_bitrate_kbps",
        "safe_zone_json",
        "notes",
    }.issubset(columns)
    assert SCHEMA_MIGRATIONS_TABLE in set(inspector.get_table_names())

    with legacy_engine.connect() as connection:
        row = connection.execute(
            text("select rule_type, safe_zone_json, notes from platform_presets where platform='youtube_shorts'")
        ).mappings().one()
        migrations = connection.execute(text(f"select count(*) from {SCHEMA_MIGRATIONS_TABLE}")).scalar_one()

    assert row["rule_type"] == "organic"
    assert row["safe_zone_json"] == "{}"
    assert row["notes"] == ""
    assert migrations >= 1


def test_schema_upgrades_add_batch_output_dir_to_legacy_database(tmp_path):
    legacy_engine = create_engine(f"sqlite:///{tmp_path / 'legacy-batches.sqlite3'}", future=True)
    with legacy_engine.begin() as connection:
        connection.execute(
            text(
                """
                create table batches (
                    id varchar(32) primary key,
                    name varchar(160) not null,
                    template_id varchar(32) not null,
                    status varchar(32) not null default 'queued',
                    total_jobs integer not null default 0,
                    created_at datetime not null
                )
                """
            )
        )

    run_schema_upgrades(legacy_engine)
    run_schema_upgrades(legacy_engine)

    inspector = inspect(legacy_engine)
    columns = {column["name"] for column in inspector.get_columns("batches")}
    assert "output_dir" in columns


def test_schema_upgrades_add_render_performance_columns_to_legacy_database(tmp_path):
    legacy_engine = create_engine(f"sqlite:///{tmp_path / 'legacy-renders.sqlite3'}", future=True)
    with legacy_engine.begin() as connection:
        connection.execute(
            text(
                """
                create table rendered_videos (
                    id varchar(32) primary key,
                    job_id varchar(32) not null unique,
                    asset_id varchar(32) not null,
                    template_id varchar(32) not null,
                    path text not null,
                    status varchar(32) not null default 'pending_review',
                    created_at datetime not null
                )
                """
            )
        )

    run_schema_upgrades(legacy_engine)
    run_schema_upgrades(legacy_engine)

    inspector = inspect(legacy_engine)
    columns = {column["name"] for column in inspector.get_columns("rendered_videos")}
    assert {"size_bytes", "render_seconds", "peak_rss_bytes", "quality_cache_json"}.issubset(columns)

    with legacy_engine.connect() as connection:
        migrations = connection.execute(
            text(f"select count(*) from {SCHEMA_MIGRATIONS_TABLE} where id='20260719_0006_render_quality_cache'")
        ).scalar_one()
    assert migrations == 1


def test_schema_upgrades_add_queue_control_columns_to_legacy_database(tmp_path):
    legacy_engine = create_engine(f"sqlite:///{tmp_path / 'legacy-queue.sqlite3'}", future=True)
    with legacy_engine.begin() as connection:
        connection.execute(
            text(
                """
                create table batches (
                    id varchar(32) primary key,
                    name varchar(160) not null,
                    template_id varchar(32) not null,
                    status varchar(32) not null default 'queued',
                    total_jobs integer not null default 0,
                    created_at datetime not null
                )
                """
            )
        )
        connection.execute(
            text(
                """
                create table render_jobs (
                    id varchar(32) primary key,
                    batch_id varchar(32) not null,
                    asset_id varchar(32) not null,
                    template_id varchar(32) not null,
                    status varchar(32) not null default 'queued',
                    created_at datetime not null
                )
                """
            )
        )

    run_schema_upgrades(legacy_engine)
    run_schema_upgrades(legacy_engine)

    inspector = inspect(legacy_engine)
    batch_columns = {column["name"] for column in inspector.get_columns("batches")}
    job_columns = {column["name"] for column in inspector.get_columns("render_jobs")}
    assert "is_paused" in batch_columns
    assert "cancel_requested" in job_columns

    with legacy_engine.connect() as connection:
        migrations = connection.execute(
            text(f"select count(*) from {SCHEMA_MIGRATIONS_TABLE} where id='20260711_0004_queue_controls'")
        ).scalar_one()
    assert migrations == 1
