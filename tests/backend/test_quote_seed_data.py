from __future__ import annotations

from collections import Counter, defaultdict

from app.quote_seed_data import YEARLY_QUOTE_COUNT, build_quote_seed_rows


def test_quote_seed_rows_cover_a_full_year_per_language() -> None:
    rows = build_quote_seed_rows()
    by_language: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_language[str(row["language"])].append(row)

    assert set(by_language) == {"en", "es"}
    assert len(by_language["en"]) >= YEARLY_QUOTE_COUNT
    assert len(by_language["es"]) >= YEARLY_QUOTE_COUNT


def test_quote_seed_rows_are_unique_and_well_formed() -> None:
    rows = build_quote_seed_rows()
    by_language_text: dict[str, set[str]] = defaultdict(set)
    tone_counts: dict[str, Counter[str]] = defaultdict(Counter)

    for row in rows:
        language = str(row["language"])
        text = str(row["text"])
        tone = str(row["tone"])

        assert row["author"] == "VANESSA Curated"
        assert row["source_universe"] == "Original"
        assert row["origin"] == "local"
        assert isinstance(row["tags"], list)
        assert row["tags"]
        assert text not in by_language_text[language]

        by_language_text[language].add(text)
        tone_counts[language][tone] += 1

    for language in ("en", "es"):
        assert "reflective" in tone_counts[language]
        assert "funny" in tone_counts[language]
