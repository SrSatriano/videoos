from __future__ import annotations

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import DATABASE_URL, ensure_data_dirs


class Base(DeclarativeBase):
    pass


ensure_data_dirs()

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
    future=True,
)


@event.listens_for(engine, "connect")
def _enable_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    from . import models  # noqa: F401
    from .services.migrations import run_schema_upgrades

    with engine.connect() as conn:
        try:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.execute(text("PRAGMA wal_autocheckpoint=1000"))
            conn.commit()
        except Exception:
            pass
        try:
            check_res = conn.execute(text("PRAGMA quick_check")).scalar()
            if check_res != "ok":
                import logging
                logging.getLogger("videoos").warning("SQLite quick_check reportou: %s", check_res)
        except Exception:
            pass

    Base.metadata.create_all(bind=engine)
    run_schema_upgrades(engine)



def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def database_status(db: Session) -> dict[str, int | str]:
    return {
        "journal_mode": str(db.execute(text("PRAGMA journal_mode")).scalar_one()),
        "synchronous": int(db.execute(text("PRAGMA synchronous")).scalar_one()),
        "busy_timeout_ms": int(db.execute(text("PRAGMA busy_timeout")).scalar_one()),
        "wal_autocheckpoint": int(db.execute(text("PRAGMA wal_autocheckpoint")).scalar_one()),
    }
