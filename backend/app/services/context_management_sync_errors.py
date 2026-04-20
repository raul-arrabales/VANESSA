from __future__ import annotations


def sync_error_summary(exc: Exception, *, fallback: str) -> str:
    return str(exc).strip() or fallback.strip() or "Sync failed."
