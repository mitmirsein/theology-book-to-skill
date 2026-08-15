import json

import pytest

from book_to_skill.claims import ClaimIndexError, claim_index_warnings, load_claim_index


def _write_book(tmp_path):
    book = tmp_path / "book-a"
    (book / "chapters").mkdir(parents=True)
    (book / "SKILL.md").write_text("---\nname: book-a\ndescription: Book A\n---\n", encoding="utf-8")
    (book / "chapters/ch01-one.md").write_text("# One\n", encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "book": {
            "id": "book-a", "title": "Book A", "authors": ["Author"], "lens": "theology",
            "tags": [{"id": "concept/incarnation", "labels": ["Incarnation"], "relevance": "primary", "basis": "explicit"}],
            "facets": {"disciplines": [], "loci": [], "traditions": []},
        },
        "chapters": [{
            "id": "ch01", "number": 1, "slug": "one", "title": "One", "path": "chapters/ch01-one.md",
            "tags": [], "facets": {"loci": [], "scriptures": [], "persons": []},
        }],
    }
    (book / "book-index.json").write_text(json.dumps(manifest), encoding="utf-8")
    return book, manifest


def _index():
    return {
        "schema_version": 1, "book_id": "book-a",
        "sources": [{"id": "source-01", "filename": "book.pdf", "format": "pdf", "sha256": "a" * 64, "locator_scheme": "pdf-page-index"}],
        "claims": [{
            "id": "book-a-ch01-c01", "chapter_id": "ch01", "type": "dogmatic", "claim": "The Word became flesh.",
            "attribution": "author", "basis": "explicit", "verification": "source-checked",
            "tags": ["concept/incarnation"], "loci": [], "scriptures": ["John 1:14"], "persons": [],
            "evidence": [{"source_id": "source-01", "locator": {"pdf_page_start": 3, "pdf_page_end": 3}, "source_checked": True}],
        }],
    }


def test_load_claim_index_accepts_valid_index_and_reports_taxonomy_drift(tmp_path):
    book, manifest = _write_book(tmp_path)
    index = _index()
    path = book / "claim-index.json"
    path.write_text(json.dumps(index), encoding="utf-8")

    assert load_claim_index(path)["claims"][0]["id"] == "book-a-ch01-c01"
    warnings = claim_index_warnings(index, manifest)
    assert "John 1:14" in warnings[0]


@pytest.mark.parametrize("mutation, expected", [
    (lambda data: data["claims"].append(data["claims"][0].copy()), "duplicates an earlier claim id"),
    (lambda data: data["claims"][0].update({"chapter_id": "ch99"}), "must reference a chapter"),
    (lambda data: data["claims"][0]["evidence"][0].update({"source_id": "missing"}), "must reference a declared source"),
    (lambda data: data["claims"][0]["evidence"][0].update({"locator": {"pdf_page_start": 4, "pdf_page_end": 3}}), "must not be greater"),
    (lambda data: data["claims"][0].update({"verification": "human-reviewed"}) or data["claims"][0]["evidence"][0].pop("source_checked"), "requires every evidence"),
])
def test_claim_index_rejects_invalid_contracts(tmp_path, mutation, expected):
    book, _ = _write_book(tmp_path)
    index = _index()
    mutation(index)
    path = book / "claim-index.json"
    path.write_text(json.dumps(index), encoding="utf-8")

    with pytest.raises(ClaimIndexError, match=expected):
        load_claim_index(path)
