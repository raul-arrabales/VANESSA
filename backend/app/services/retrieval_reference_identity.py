from __future__ import annotations

from typing import Any

URI_METADATA_KEYS = ("uri", "file_uri", "source_uri", "url", "source_url")
PATH_METADATA_KEYS = ("source_path", "source_filename", "file_path", "filename")
PAGE_METADATA_KEYS = ("page", "page_number", "page_numbers", "pages")


def reference_group_key(result: dict[str, Any], metadata: dict[str, Any]) -> str:
    for value in (
        first_metadata_string(metadata, URI_METADATA_KEYS),
        first_metadata_string(metadata, PATH_METADATA_KEYS),
        string_or_none(metadata.get("document_id")),
        string_or_none(metadata.get("title")),
        string_or_none(result.get("id")),
    ):
        if value:
            return value
    return "unknown-source"


def reference_title(result: dict[str, Any], metadata: dict[str, Any]) -> str:
    return (
        string_or_none(metadata.get("title"))
        or string_or_none(metadata.get("source_display_name"))
        or string_or_none(metadata.get("source_name"))
        or string_or_none(metadata.get("source_filename"))
        or string_or_none(metadata.get("source_path"))
        or string_or_none(result.get("id"))
        or "Source"
    )


def reference_description(result: dict[str, Any], metadata: dict[str, Any]) -> str:
    return (
        string_or_none(metadata.get("description"))
        or string_or_none(metadata.get("source_description"))
        or string_or_none(metadata.get("source_display_name"))
        or string_or_none(metadata.get("source_name"))
        or string_or_none(metadata.get("source_type"))
        or reference_title(result, metadata)
    )


def reference_file_value(metadata: dict[str, Any], result: dict[str, Any]) -> str | None:
    return (
        first_metadata_string(metadata, URI_METADATA_KEYS)
        or first_metadata_string(metadata, PATH_METADATA_KEYS)
        or string_or_none(metadata.get("document_id"))
        or string_or_none(result.get("id"))
    )


def metadata_page_numbers(metadata: dict[str, Any]) -> set[int]:
    pages: set[int] = set()
    for key in PAGE_METADATA_KEYS:
        pages.update(coerce_page_numbers(metadata.get(key)))

    start = first_page_number(metadata.get("page_start"))
    end = first_page_number(metadata.get("page_end"))
    if start is not None and end is not None:
        lower = min(start, end)
        upper = max(start, end)
        if upper - lower <= 50:
            pages.update(range(lower, upper + 1))
        else:
            pages.update({lower, upper})
    elif start is not None:
        pages.add(start)
    elif end is not None:
        pages.add(end)

    return pages


def first_metadata_string(metadata: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        normalized = string_or_none(metadata.get(key))
        if normalized:
            return normalized
    return None


def string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def coerce_page_numbers(value: Any) -> set[int]:
    if value is None or isinstance(value, bool):
        return set()
    if isinstance(value, int):
        return {value} if value > 0 else set()
    if isinstance(value, float):
        return {int(value)} if value.is_integer() and value > 0 else set()
    if isinstance(value, str):
        pages: set[int] = set()
        for part in value.replace(";", ",").split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                start_raw, end_raw = part.split("-", 1)
                start = parse_positive_int(start_raw)
                end = parse_positive_int(end_raw)
                if start is not None and end is not None:
                    lower = min(start, end)
                    upper = max(start, end)
                    if upper - lower <= 50:
                        pages.update(range(lower, upper + 1))
                    else:
                        pages.update({lower, upper})
                continue
            page = parse_positive_int(part)
            if page is not None:
                pages.add(page)
        return pages
    if isinstance(value, list):
        pages: set[int] = set()
        for item in value:
            pages.update(coerce_page_numbers(item))
        return pages
    return set()


def first_page_number(value: Any) -> int | None:
    pages = coerce_page_numbers(value)
    return min(pages) if pages else None


def parse_positive_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, float):
        return int(value) if value.is_integer() and value > 0 else None
    normalized = str(value).strip()
    if not normalized.isdigit():
        return None
    parsed = int(normalized)
    return parsed if parsed > 0 else None
