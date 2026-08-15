"""Strict v1 validation for portable, evidence-backed book claims."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

from book_to_skill.catalog import ManifestError, load_manifest


CLAIM_SCHEMA_VERSION = 1
CLAIM_TYPES = {
    "thesis",
    "exegetical",
    "dogmatic",
    "historical",
    "methodological",
    "lexical",
    "critical",
}
VERIFICATIONS = {"generated", "source-checked", "human-reviewed"}
BASES = {"explicit", "inferred"}
_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_TAG = re.compile(r"^(?:concept|framework|method|theme)/[a-z0-9]+(?:-[a-z0-9]+)*$")
_LOCUS = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*(?:/[a-z0-9]+(?:-[a-z0-9]+)*)+$")
_SCRIPTURE = re.compile(
    r"^(?:[1-3] )?[A-Za-z][A-Za-z0-9.]* [1-9][0-9]*(?::[1-9][0-9]*[a-z]?)?(?:-[1-9][0-9]*(?::[1-9][0-9]*[a-z]?)?)?$"
)
_PATHISH = re.compile(r"(?:^/|^~|^[A-Za-z]:[\\/]|(?:^|[\\/])\.\.(?:[\\/]|$))")


class ClaimIndexError(ValueError):
    """Raised when a claim index cannot be loaded or validated."""


def _error(path: str, message: str) -> str:
    return f"{path}: {message}"


def _safe_string(value: Any, path: str, errors: list[str], *, maximum: int = 0) -> bool:
    if not isinstance(value, str) or not value.strip():
        errors.append(_error(path, "must be a non-empty string"))
        return False
    if maximum and len(value) > maximum:
        errors.append(_error(path, f"must be at most {maximum} characters"))
        return False
    if _PATHISH.search(value):
        errors.append(_error(path, "must not contain an absolute or traversal path"))
        return False
    return True


def _keys(
    value: Any, *, path: str, allowed: set[str], required: set[str], errors: list[str]
) -> bool:
    if not isinstance(value, dict):
        errors.append(_error(path, "must be an object"))
        return False
    for key in sorted(set(value) - allowed):
        errors.append(_error(path, f"unknown field {key!r}"))
    for key in sorted(required - set(value)):
        errors.append(_error(f"{path}.{key}", "is required"))
    return True


def _string_array(value: Any, path: str, errors: list[str], pattern: re.Pattern[str]) -> list[str]:
    if not isinstance(value, list):
        errors.append(_error(path, "must be an array"))
        return []
    result: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        if not _safe_string(item, item_path, errors) or not pattern.fullmatch(item):
            errors.append(_error(item_path, "has an invalid canonical identifier"))
            continue
        if item in seen:
            errors.append(_error(item_path, "duplicates an earlier identifier"))
            continue
        seen.add(item)
        result.append(item)
    return result


def _validate_locator(value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, dict) or not value:
        errors.append(_error(path, "must be a non-empty object"))
        return
    allowed = {
        "segment_id", "pdf_page_start", "pdf_page_end", "printed_page_start",
        "printed_page_end", "spine_item_start", "spine_item_end", "heading_path",
        "paragraph_start", "paragraph_end", "line_start", "line_end",
    }
    for key in sorted(set(value) - allowed):
        errors.append(_error(path, f"unknown field {key!r}"))
    for key, item in value.items():
        item_path = f"{path}.{key}"
        if key == "heading_path":
            if not isinstance(item, list) or not all(isinstance(part, str) and part.strip() for part in item):
                errors.append(_error(item_path, "must be an array of non-empty heading strings"))
        elif key == "segment_id":
            if not isinstance(item, str) or not _ID.fullmatch(item):
                errors.append(_error(item_path, "must be a portable segment id"))
        elif key.startswith("printed_page"):
            if not isinstance(item, (int, str)) or isinstance(item, bool):
                errors.append(_error(item_path, "must be an integer or printed page label"))
        elif not isinstance(item, int) or isinstance(item, bool) or item < 1:
            errors.append(_error(item_path, "must be a positive integer"))
    for start, end in (
        ("pdf_page_start", "pdf_page_end"),
        ("spine_item_start", "spine_item_end"),
        ("paragraph_start", "paragraph_end"),
        ("line_start", "line_end"),
    ):
        if start in value and end in value and isinstance(value[start], int) and isinstance(value[end], int) and value[start] > value[end]:
            errors.append(_error(path, f"{start} must not be greater than {end}"))


def validate_claim_index(data: dict[str, Any], book_dir: Path) -> list[str]:
    """Return all v1 contract violations without raising for data errors."""

    errors: list[str] = []
    root = f"{Path(book_dir) / 'claim-index.json'}: $"
    if not _keys(data, path=root, allowed={"schema_version", "book_id", "sources", "claims"}, required={"schema_version", "book_id", "sources", "claims"}, errors=errors):
        return errors
    if type(data.get("schema_version")) is not int or data.get("schema_version") != CLAIM_SCHEMA_VERSION:
        errors.append(_error(f"{root}.schema_version", f"must be integer {CLAIM_SCHEMA_VERSION}"))

    try:
        manifest = load_manifest(Path(book_dir) / "book-index.json")
    except ManifestError as exc:
        errors.append(str(exc))
        return errors
    book_id = data.get("book_id")
    if not _safe_string(book_id, f"{root}.book_id", errors) or book_id != manifest["book"]["id"]:
        errors.append(_error(f"{root}.book_id", "must match book-index.json book.id"))

    source_ids: set[str] = set()
    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append(_error(f"{root}.sources", "must be a non-empty array"))
    else:
        for index, source in enumerate(sources):
            path = f"{root}.sources[{index}]"
            if not _keys(source, path=path, allowed={"id", "filename", "format", "sha256", "locator_scheme"}, required={"id", "filename", "format", "sha256", "locator_scheme"}, errors=errors):
                continue
            source_id = source.get("id")
            if not _safe_string(source_id, f"{path}.id", errors) or not _ID.fullmatch(source_id):
                errors.append(_error(f"{path}.id", "must be a kebab-case id"))
            elif source_id in source_ids:
                errors.append(_error(f"{path}.id", "duplicates an earlier source id"))
            else:
                source_ids.add(source_id)
            _safe_string(source.get("filename"), f"{path}.filename", errors)
            if isinstance(source.get("filename"), str) and Path(source["filename"]).name != source["filename"]:
                errors.append(_error(f"{path}.filename", "must be a filename, not a path"))
            _safe_string(source.get("format"), f"{path}.format", errors)
            if not isinstance(source.get("sha256"), str) or not _SHA256.fullmatch(source["sha256"]):
                errors.append(_error(f"{path}.sha256", "must be a lowercase SHA-256 hex digest"))
            _safe_string(source.get("locator_scheme"), f"{path}.locator_scheme", errors)

    chapter_ids = {chapter["id"] for chapter in manifest["chapters"]}
    claim_ids: set[str] = set()
    claims = data.get("claims")
    if not isinstance(claims, list):
        errors.append(_error(f"{root}.claims", "must be an array"))
        return errors
    for index, claim in enumerate(claims):
        path = f"{root}.claims[{index}]"
        allowed = {"id", "chapter_id", "type", "claim", "attribution", "basis", "verification", "tags", "loci", "scriptures", "persons", "evidence"}
        if not _keys(claim, path=path, allowed=allowed, required=allowed, errors=errors):
            continue
        claim_id = claim.get("id")
        if not _safe_string(claim_id, f"{path}.id", errors) or not _ID.fullmatch(claim_id):
            errors.append(_error(f"{path}.id", "must be a kebab-case id"))
        elif claim_id in claim_ids:
            errors.append(_error(f"{path}.id", "duplicates an earlier claim id"))
        else:
            claim_ids.add(claim_id)
        if claim.get("chapter_id") not in chapter_ids:
            errors.append(_error(f"{path}.chapter_id", "must reference a chapter in book-index.json"))
        if claim.get("type") not in CLAIM_TYPES:
            errors.append(_error(f"{path}.type", f"must be one of {', '.join(sorted(CLAIM_TYPES))}"))
        _safe_string(claim.get("claim"), f"{path}.claim", errors, maximum=800)
        _safe_string(claim.get("attribution"), f"{path}.attribution", errors, maximum=160)
        if claim.get("basis") not in BASES:
            errors.append(_error(f"{path}.basis", "must be explicit or inferred"))
        if claim.get("verification") not in VERIFICATIONS:
            errors.append(_error(f"{path}.verification", "must be generated, source-checked, or human-reviewed"))
        _string_array(claim.get("tags"), f"{path}.tags", errors, _TAG)
        _string_array(claim.get("loci"), f"{path}.loci", errors, _LOCUS)
        _string_array(claim.get("scriptures"), f"{path}.scriptures", errors, _SCRIPTURE)
        _string_array(claim.get("persons"), f"{path}.persons", errors, _ID)
        evidence = claim.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(_error(f"{path}.evidence", "must be a non-empty array"))
            continue
        seen_evidence: set[str] = set()
        source_checked = True
        for evidence_index, item in enumerate(evidence):
            evidence_path = f"{path}.evidence[{evidence_index}]"
            if not _keys(item, path=evidence_path, allowed={"source_id", "locator", "source_checked"}, required={"source_id", "locator"}, errors=errors):
                source_checked = False
                continue
            if item.get("source_id") not in source_ids:
                errors.append(_error(f"{evidence_path}.source_id", "must reference a declared source"))
            _validate_locator(item.get("locator"), f"{evidence_path}.locator", errors)
            fingerprint = json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            if fingerprint in seen_evidence:
                errors.append(_error(evidence_path, "duplicates an earlier evidence record"))
            seen_evidence.add(fingerprint)
            source_checked = source_checked and item.get("source_checked") is True
        if claim.get("verification") in {"source-checked", "human-reviewed"} and not source_checked:
            errors.append(_error(f"{path}.verification", "requires every evidence record to set source_checked=true"))
    return errors


def claim_index_warnings(data: Mapping[str, Any], manifest: Mapping[str, Any]) -> list[str]:
    """Report taxonomy drift without rejecting a valid new canonical term."""

    known_tags = {ref["id"] for ref in manifest["book"]["tags"]}
    known_loci = {ref["id"] for ref in manifest["book"]["facets"]["loci"]}
    known_scriptures: set[str] = set()
    known_persons: set[str] = set()
    for chapter in manifest["chapters"]:
        known_tags.update(ref["id"] for ref in chapter["tags"])
        known_loci.update(ref["id"] for ref in chapter["facets"]["loci"])
        known_scriptures.update(ref["id"] for ref in chapter["facets"]["scriptures"])
        known_persons.update(ref["id"] for ref in chapter["facets"]["persons"])
    warnings: list[str] = []
    for index, claim in enumerate(data.get("claims", [])):
        if not isinstance(claim, Mapping):
            continue
        for field, known in (("tags", known_tags), ("loci", known_loci), ("scriptures", known_scriptures), ("persons", known_persons)):
            for value in claim.get(field, []):
                if value not in known:
                    warnings.append(f"$.claims[{index}].{field}: taxonomy drift candidate {value!r}")
    return warnings


def load_claim_index(path: Path) -> dict[str, Any]:
    """Load and strictly validate a book-local ``claim-index.json`` file."""

    path = Path(path)
    if path.name != "claim-index.json":
        raise ClaimIndexError(f"{path}: expected filename claim-index.json")
    if path.is_symlink():
        raise ClaimIndexError(f"{path}: claim index must not be a symbolic link")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ClaimIndexError(f"{path}: invalid JSON at line {exc.lineno}, column {exc.colno}") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise ClaimIndexError(f"{path}: could not read valid UTF-8 JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ClaimIndexError(f"{path}: root must be an object")
    errors = validate_claim_index(data, path.parent)
    if errors:
        raise ClaimIndexError("\n".join(errors))
    return data
