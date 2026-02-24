from __future__ import annotations

from typing import Any

from psycopg import errors

from ..db import get_connection


UserRecord = dict[str, Any]


def normalize_email(value: str) -> str:
    return value.strip().lower()


def normalize_username(value: str) -> str:
    return value.strip().lower()


def sanitize_user_record(user: UserRecord) -> UserRecord:
    return {
        "id": user["id"],
        "email": user["email"],
        "username": user["username"],
        "role": user["role"],
        "is_active": user["is_active"],
        "created_at": user["created_at"].isoformat() if user.get("created_at") else None,
        "updated_at": user["updated_at"].isoformat() if user.get("updated_at") else None,
    }


def count_users(database_url: str) -> int:
    with get_connection(database_url) as connection:
        row = connection.execute("SELECT COUNT(*) AS total FROM users").fetchone()
    return int(row["total"]) if row else 0


def count_users_by_role(database_url: str, role: str) -> int:
    with get_connection(database_url) as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS total FROM users WHERE role = %s",
            (role,),
        ).fetchone()
    return int(row["total"]) if row else 0


def create_user(
    database_url: str,
    *,
    email: str,
    username: str,
    password_hash: str,
    role: str,
    is_active: bool,
) -> UserRecord:
    with get_connection(database_url) as connection:
        try:
            row = connection.execute(
                """
                INSERT INTO users (email, username, password_hash, role, is_active)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, email, username, role, is_active, created_at, updated_at
                """,
                (
                    normalize_email(email),
                    normalize_username(username),
                    password_hash,
                    role,
                    is_active,
                ),
            ).fetchone()
        except errors.UniqueViolation as exc:
            raise ValueError("duplicate_user") from exc

    if row is None:
        raise RuntimeError("Failed to create user")
    return dict(row)


def find_user_by_identifier(database_url: str, identifier: str) -> UserRecord | None:
    normalized = identifier.strip().lower()
    field = "email" if "@" in normalized else "username"
    with get_connection(database_url) as connection:
        row = connection.execute(
            f"""
            SELECT id, email, username, password_hash, role, is_active, created_at, updated_at
            FROM users
            WHERE {field} = %s
            """,
            (normalized,),
        ).fetchone()
    return dict(row) if row else None


def find_user_by_id(database_url: str, user_id: int) -> UserRecord | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            SELECT id, email, username, password_hash, role, is_active, created_at, updated_at
            FROM users
            WHERE id = %s
            """,
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def activate_user(database_url: str, user_id: int) -> UserRecord | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            UPDATE users
            SET is_active = TRUE, updated_at = NOW()
            WHERE id = %s
            RETURNING id, email, username, role, is_active, created_at, updated_at
            """,
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def update_user_role(database_url: str, user_id: int, role: str) -> UserRecord | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            UPDATE users
            SET role = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING id, email, username, role, is_active, created_at, updated_at
            """,
            (role, user_id),
        ).fetchone()
    return dict(row) if row else None


def list_users(database_url: str, *, is_active: bool | None = None) -> list[UserRecord]:
    query = """
        SELECT id, email, username, role, is_active, created_at, updated_at
        FROM users
    """
    params: tuple[Any, ...] = ()

    if is_active is not None:
        query += " WHERE is_active = %s"
        params = (is_active,)

    query += " ORDER BY id ASC"

    with get_connection(database_url) as connection:
        rows = connection.execute(query, params).fetchall()
    return [dict(row) for row in rows]
