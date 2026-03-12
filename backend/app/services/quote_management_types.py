from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class QuoteCountBucket:
    value: str
    count: int


@dataclass(frozen=True)
class QuoteSummary:
    total: int
    active: int
    approved: int
    by_language: list[QuoteCountBucket]
    by_tone: list[QuoteCountBucket]
    by_origin: list[QuoteCountBucket]


@dataclass(frozen=True)
class QuoteFilters:
    language: str | None = None
    source_universe: str | None = None
    tone: str | None = None
    origin: str | None = None
    is_active: bool | None = None
    is_approved: bool | None = None
    created_from: date | None = None
    created_to: date | None = None
    query: str | None = None


@dataclass(frozen=True)
class QuotePayload:
    language: str
    text: str
    author: str
    source_universe: str
    tone: str
    tags: list[str]
    is_active: bool
    is_approved: bool
    origin: str
    external_ref: str | None


@dataclass(frozen=True)
class QuoteRecord:
    id: int
    language: str
    text: str
    author: str
    source_universe: str
    tone: str
    tags: list[str]
    is_active: bool
    is_approved: bool
    origin: str
    external_ref: str | None
    created_at: datetime | None
    updated_at: datetime | None


@dataclass(frozen=True)
class QuoteListResult:
    items: list[QuoteRecord]
    total: int
