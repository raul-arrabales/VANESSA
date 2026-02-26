from __future__ import annotations

from typing import Any
from uuid import UUID

from ..db import get_connection


def create_download_job(
    database_url: str,
    *,
    job_id: UUID,
    provider: str,
    source_id: str,
    target_dir: str,
    created_by_user_id: int,
) -> dict[str, Any]:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            INSERT INTO model_download_jobs (
                id,
                provider,
                source_id,
                target_dir,
                status,
                created_by_user_id
            )
            VALUES (%s, %s, %s, %s, 'queued', %s)
            RETURNING *
            """,
            (str(job_id), provider, source_id, target_dir, created_by_user_id),
        ).fetchone()
    if row is None:
        raise RuntimeError("failed_to_create_download_job")
    return dict(row)


def get_download_job(database_url: str, job_id: str) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            "SELECT * FROM model_download_jobs WHERE id = %s",
            (job_id,),
        ).fetchone()
    return dict(row) if row else None


def list_download_jobs(
    database_url: str,
    *,
    status: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    with get_connection(database_url) as connection:
        if status:
            rows = connection.execute(
                """
                SELECT * FROM model_download_jobs
                WHERE status = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (status, limit),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT * FROM model_download_jobs
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            ).fetchall()
    return [dict(row) for row in rows]


def claim_next_queued_job(database_url: str) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            UPDATE model_download_jobs AS jobs
            SET status = 'running', started_at = NOW(), updated_at = NOW()
            WHERE jobs.id = (
                SELECT id
                FROM model_download_jobs
                WHERE status = 'queued'
                ORDER BY created_at ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            )
            RETURNING *
            """
        ).fetchone()
    return dict(row) if row else None


def mark_job_succeeded(
    database_url: str,
    *,
    job_id: str,
    model_id: str | None = None,
) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            UPDATE model_download_jobs
            SET
                status = 'succeeded',
                model_id = COALESCE(%s, model_id),
                error_message = NULL,
                finished_at = NOW(),
                updated_at = NOW()
            WHERE id = %s
            RETURNING *
            """,
            (model_id, job_id),
        ).fetchone()
    return dict(row) if row else None


def mark_job_failed(
    database_url: str,
    *,
    job_id: str,
    error_message: str,
) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            UPDATE model_download_jobs
            SET
                status = 'failed',
                error_message = %s,
                finished_at = NOW(),
                updated_at = NOW()
            WHERE id = %s
            RETURNING *
            """,
            (error_message, job_id),
        ).fetchone()
    return dict(row) if row else None


def reconcile_stale_running_jobs(database_url: str, *, stale_after_seconds: int) -> int:
    with get_connection(database_url) as connection:
        rows = connection.execute(
            """
            UPDATE model_download_jobs
            SET
                status = 'failed',
                error_message = 'Worker restarted while job was running',
                finished_at = NOW(),
                updated_at = NOW()
            WHERE status = 'running'
              AND started_at < (NOW() - (%s * INTERVAL '1 second'))
            RETURNING id
            """,
            (stale_after_seconds,),
        ).fetchall()
    return len(rows)

