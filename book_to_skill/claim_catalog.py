"""Deterministic claim catalog construction and bounded retrieval."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from book_to_skill.catalog import CatalogError, load_manifest, normalize_alias
from book_to_skill.claims import ClaimIndexError, load_claim_index


CLAIM_CATALOG_SCHEMA_VERSION = 1
CATALOG_FILENAME = "claim-catalog.json"


class ClaimCatalogError(CatalogError):
    """Raised for claim catalog construction or loading failures."""


class ClaimQueryError(ClaimCatalogError):
    """Raised for an invalid bounded claim query."""


@dataclass(frozen=True)
class ClaimCatalogQuery:
    tags: Sequence[str] = ()
    terms: Sequence[str] = ()
    scriptures: Sequence[str] = ()
    loci: Sequence[str] = ()
    persons: Sequence[str] = ()
    types: Sequence[str] = ()
    verification: Sequence[str] = ()
    book: str | None = None
    match: str = "all"
    include_generated: bool = False
    min_books: int = 1
    limit: int = 20


def _root(path: Path) -> Path:
    path = Path(path)
    if path.is_symlink():
        raise ClaimCatalogError(f"{path}: books root must not be a symbolic link")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ClaimCatalogError(f"{path}: books root does not exist") from exc
    if not resolved.is_dir():
        raise ClaimCatalogError(f"{path}: books root is not a directory")
    return resolved


def discover_claim_indexes(books_root: Path) -> tuple[list[Path], list[str]]:
    """Find migrated indexes and report books that still need migration."""

    root = _root(books_root)
    indexes: list[Path] = []
    missing: list[str] = []
    for child in sorted(root.iterdir(), key=lambda item: item.name):
        if child.name in {"catalog.json", "INDEX.md", CATALOG_FILENAME}:
            continue
        if child.is_symlink():
            if (child / "SKILL.md").exists():
                raise ClaimCatalogError(f"{child}: book directory must not be a symbolic link")
            continue
        if not child.is_dir() or not (child / "SKILL.md").is_file():
            continue
        manifest = child / "book-index.json"
        if not manifest.is_file():
            raise ClaimCatalogError(f"{child}: book-index.json is required before claim migration")
        index = child / "claim-index.json"
        if index.exists():
            if index.is_symlink() or not index.is_file():
                raise ClaimCatalogError(f"{index}: claim index must be a regular non-symlink file")
            indexes.append(index)
        else:
            missing.append(child.name)
    return indexes, missing


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve(strict=True).relative_to(root).as_posix()
    except (OSError, ValueError) as exc:
        raise ClaimCatalogError(f"{path}: path is outside books root") from exc


def _append(index: dict[str, list[str]], key: str, claim_id: str) -> None:
    index.setdefault(key, []).append(claim_id)


def build_claim_catalog(
    claim_indexes: Sequence[tuple[Path, dict[str, Any]]],
    books_root: Path,
    *,
    missing_books: Sequence[str] = (),
) -> dict[str, Any]:
    """Build a deterministic derived catalog from validated claim indexes."""

    root = _root(books_root)
    books: dict[str, dict[str, Any]] = {
        book_id: {"migration_status": "missing", "claim_count": 0}
        for book_id in sorted(missing_books)
    }
    claims: dict[str, dict[str, Any]] = {}
    indexes: dict[str, dict[str, list[str]]] = {
        name: {} for name in ("tags", "terms", "loci", "scriptures", "persons", "types", "verification")
    }
    errors: list[str] = []
    for index_path, index_data in claim_indexes:
        path = Path(index_path)
        try:
            relative = _relative(path, root)
            if len(Path(relative).parts) != 2:
                raise ClaimCatalogError("claim index must be in a direct child book directory")
            manifest = load_manifest(path.parent / "book-index.json")
            loaded = load_claim_index(path)
        except (ClaimCatalogError, ClaimIndexError, CatalogError) as exc:
            errors.append(str(exc))
            continue
        if loaded != index_data:
            errors.append(f"{path}: supplied claim index differs from validated file contents")
            continue
        book_id = loaded["book_id"]
        if book_id in books and books[book_id]["migration_status"] == "ready":
            errors.append(f"{path}: duplicate claim index for {book_id}")
            continue
        tag_labels = {
            ref["id"]: ref.get("labels", [])
            for chapter in manifest["chapters"]
            for ref in chapter["tags"]
        }
        tag_labels.update({ref["id"]: ref.get("labels", []) for ref in manifest["book"]["tags"]})
        chapters = {chapter["id"]: chapter for chapter in manifest["chapters"]}
        covered_chapters = {claim["chapter_id"] for claim in loaded["claims"]}
        migration_status = (
            "ready"
            if covered_chapters == set(chapters)
            else "partial"
        )
        books[book_id] = {
            "migration_status": migration_status,
            "claim_count": len(loaded["claims"]),
            "claim_index_path": relative,
        }
        for claim in loaded["claims"]:
            claim_id = claim["id"]
            if claim_id in claims:
                errors.append(f"{path}: duplicate global claim id {claim_id!r}")
                continue
            chapter = chapters[claim["chapter_id"]]
            evidence = [
                {"source_id": item["source_id"], "locator": item["locator"]}
                for item in claim["evidence"]
            ]
            claims[claim_id] = {
                "book_id": book_id,
                "chapter_id": claim["chapter_id"],
                "chapter_path": f"{book_id}/{chapter['path']}",
                "type": claim["type"],
                "display": claim["claim"][:200],
                "attribution": claim["attribution"],
                "basis": claim["basis"],
                "verification": claim["verification"],
                "tags": list(claim["tags"]),
                "loci": list(claim["loci"]),
                "scriptures": list(claim["scriptures"]),
                "persons": list(claim["persons"]),
                "evidence": evidence,
            }
            for tag in claim["tags"]:
                _append(indexes["tags"], tag, claim_id)
                _append(indexes["terms"], normalize_alias(tag), claim_id)
                for label in tag_labels.get(tag, []):
                    _append(indexes["terms"], normalize_alias(label), claim_id)
            for field in ("loci", "scriptures", "persons"):
                for value in claim[field]:
                    _append(indexes[field], value, claim_id)
            _append(indexes["types"], claim["type"], claim_id)
            _append(indexes["verification"], claim["verification"], claim_id)
    if errors:
        raise ClaimCatalogError("\n".join(errors))
    for mapping in indexes.values():
        for value in mapping.values():
            value.sort()
    return {
        "schema_version": CLAIM_CATALOG_SCHEMA_VERSION,
        "books": dict(sorted(books.items())),
        "claims": dict(sorted(claims.items())),
        "indexes": {name: dict(sorted(mapping.items())) for name, mapping in indexes.items()},
    }


def write_claim_catalog_atomic(catalog: Mapping[str, Any], books_root: Path) -> Path:
    """Atomically replace only a fully-built, deterministic catalog."""

    root = _root(books_root)
    destination = root / CATALOG_FILENAME
    payload = json.dumps(catalog, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    descriptor, temp_name = tempfile.mkstemp(prefix=".claim-catalog-", suffix=".json", dir=root)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, destination)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise
    return destination


def load_claim_catalog(path: Path) -> dict[str, Any]:
    path = Path(path)
    if path.name != CATALOG_FILENAME:
        raise ClaimCatalogError(f"{path}: expected filename {CATALOG_FILENAME}")
    if path.is_symlink():
        raise ClaimCatalogError(f"{path}: catalog must not be a symbolic link")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ClaimCatalogError(f"{path}: invalid JSON at line {exc.lineno}, column {exc.colno}") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise ClaimCatalogError(f"{path}: could not read valid UTF-8 JSON: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema_version") != CLAIM_CATALOG_SCHEMA_VERSION:
        raise ClaimCatalogError(f"{path}: unsupported or invalid claim catalog schema")
    if not isinstance(data.get("claims"), dict) or not isinstance(data.get("indexes"), dict):
        raise ClaimCatalogError(f"{path}: catalog claims and indexes must be objects")
    return data


def _conditions(catalog: Mapping[str, Any], query: ClaimCatalogQuery) -> list[set[str]]:
    if query.match not in {"all", "any"}:
        raise ClaimQueryError("match must be all or any")
    if not 1 <= query.limit <= 200:
        raise ClaimQueryError("limit must be between 1 and 200")
    if query.min_books < 1:
        raise ClaimQueryError("min_books must be at least 1")
    indexes = catalog["indexes"]
    condition_values = (
        ("tags", query.tags), ("terms", query.terms), ("scriptures", query.scriptures),
        ("loci", query.loci), ("persons", query.persons), ("types", query.types),
        ("verification", query.verification),
    )
    conditions: list[set[str]] = []
    for name, values in condition_values:
        for value in values:
            key = normalize_alias(value) if name == "terms" else value
            conditions.append(set(indexes.get(name, {}).get(key, [])))
    return conditions


def query_claim_catalog(catalog: Mapping[str, Any], query: ClaimCatalogQuery) -> list[dict[str, Any]]:
    """Return bounded claim records, excluding generated claims by default."""

    conditions = _conditions(catalog, query)
    claim_map: Mapping[str, Mapping[str, Any]] = catalog["claims"]
    candidates = set(claim_map)
    if conditions:
        candidates = set.intersection(*conditions) if query.match == "all" else set.union(*conditions)
    if query.book:
        candidates = {claim_id for claim_id in candidates if claim_map[claim_id]["book_id"] == query.book}
    if not query.include_generated:
        candidates = {claim_id for claim_id in candidates if claim_map[claim_id]["verification"] != "generated"}
    book_count = len({claim_map[claim_id]["book_id"] for claim_id in candidates})
    if book_count < query.min_books:
        return []
    ordered = sorted(
        candidates,
        key=lambda claim_id: (
            claim_map[claim_id]["book_id"], claim_map[claim_id]["chapter_id"], claim_id,
        ),
    )[:query.limit]
    return [{"claim_id": claim_id, **claim_map[claim_id]} for claim_id in ordered]
