from __future__ import annotations

from sqlalchemy.exc import OperationalError

from app.worker import is_transient_sqlite_lock, sqlite_retry_delay


def operational_error(message: str) -> OperationalError:
    return OperationalError("SELECT 1", {}, Exception(message))


def test_transient_sqlite_lock_messages_are_recognized() -> None:
    assert is_transient_sqlite_lock(operational_error("database is locked"))
    assert is_transient_sqlite_lock(operational_error("database table is locked"))
    assert is_transient_sqlite_lock(operational_error("locking protocol"))


def test_other_operational_errors_are_not_hidden() -> None:
    assert not is_transient_sqlite_lock(operational_error("no such table: render_jobs"))
    assert not is_transient_sqlite_lock(operational_error("disk I/O error"))


def test_sqlite_retry_delay_is_bounded() -> None:
    assert sqlite_retry_delay(1, 2.0) == 2.0
    assert sqlite_retry_delay(2, 2.0) == 4.0
    assert sqlite_retry_delay(20, 2.0) == 30.0
    assert sqlite_retry_delay(1, 0.1) == 0.5
