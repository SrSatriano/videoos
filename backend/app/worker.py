from __future__ import annotations

import os
import time

from sqlalchemy.exc import OperationalError

from .database import SessionLocal, init_db
from .services.queue import claim_next_job, process_job, recover_interrupted_jobs
from .services.seed import seed_defaults
from .services.social import (
    claim_next_download_job,
    process_download_job,
    recover_interrupted_download_jobs,
)


_TRANSIENT_SQLITE_LOCK_ERRORS = (
    "database is locked",
    "database table is locked",
    "locking protocol",
)


def is_transient_sqlite_lock(error: OperationalError) -> bool:
    message = str(error).lower()
    return any(fragment in message for fragment in _TRANSIENT_SQLITE_LOCK_ERRORS)


def sqlite_retry_delay(attempt: int, interval: float) -> float:
    return min(30.0, max(0.5, interval) * (2 ** min(max(attempt - 1, 0), 4)))


def run_worker() -> None:
    init_db()
    with SessionLocal() as db:
        seed_defaults(db)
        recovered = recover_interrupted_jobs(db)
        if recovered:
            print(f"{recovered} job(s) de render interrompido(s) recuperado(s).")
        recovered_downloads = recover_interrupted_download_jobs(db)
        if recovered_downloads:
            print(f"{recovered_downloads} download(s) interrompido(s) recuperado(s).")
    interval = float(os.getenv("VIDEO_OS_WORKER_INTERVAL", "2.0"))
    print("Worker iniciado (render + download).")
    lock_attempts = 0
    while True:
        try:
            with SessionLocal() as db:
                job = claim_next_job(db)
                if job:
                    print(f"Processando render {job.id} ({job.asset.filename})")
                    process_job(db, job)
                    lock_attempts = 0
                    continue

                download = claim_next_download_job(db)
                if download:
                    print(f"Processando download {download.id}")
                    process_download_job(db, download)
                    lock_attempts = 0
                    continue

            lock_attempts = 0
            time.sleep(interval)
        except OperationalError as error:
            if not is_transient_sqlite_lock(error):
                raise
            lock_attempts += 1
            delay = sqlite_retry_delay(lock_attempts, interval)
            print(f"SQLite temporariamente bloqueado; nova tentativa em {delay:.1f}s.")
            time.sleep(delay)


if __name__ == "__main__":
    run_worker()
