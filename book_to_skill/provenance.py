"""Deterministic, portable provenance records for extracted source text.

The public parser contract remains ``str | None``.  This module creates a
parallel segment map *after* extraction and sanitization, so legacy callers
can keep consuming ``full_text.txt`` while later generation steps can locate
the source material that produced a claim.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


SEGMENT_SCHEMA_VERSION = 1
_ATX_HEADING = re.compile(r"^\s*(#{1,6})\s+(.+?)\s*#*\s*$")
_SETEXT_UNDERLINE = re.compile(r"^\s*(=+|-+)\s*$")


@dataclass(frozen=True)
class SourceSegment:
    """A contiguous, sanitized range of a source's extracted text."""

    id: str
    source_id: str
    char_start: int
    char_end: int
    locator: dict[str, Any]
    locator_reliability: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExtractedSource:
    """Portable source metadata and its locatable text segments."""

    id: str
    filename: str
    format: str
    sha256: str
    locator_scheme: str
    locator_reliability: str
    chars: int
    segments: tuple[SourceSegment, ...]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["segments"] = [segment.to_dict() for segment in self.segments]
        return result


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of ``path`` without persisting its path."""

    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _heading_sections(text: str) -> Iterable[tuple[int, int, dict[str, Any]]]:
    """Yield heading-aware line ranges for text-like formats.

    The result intentionally uses source-text line numbers, not generated
    document line numbers.  ATX and Setext headings are enough for the formats
    the extractor can locate reliably without a markup-specific parser.
    """

    lines = text.splitlines(keepends=True)
    if not lines:
        return
    starts: list[int] = []
    offset = 0
    for line in lines:
        starts.append(offset)
        offset += len(line)

    heading_paths: dict[int, list[str]] = {}
    stack: list[tuple[int, str]] = []
    for index, raw_line in enumerate(lines):
        line = raw_line.rstrip("\r\n")
        match = _ATX_HEADING.match(line)
        level: int | None = None
        title: str | None = None
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
        elif index + 1 < len(lines) and line.strip() and _SETEXT_UNDERLINE.match(
            lines[index + 1].rstrip("\r\n")
        ):
            underline = lines[index + 1].lstrip()[:1]
            level = 1 if underline == "=" else 2
            title = line.strip()
        if level is None or not title:
            continue
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, title))
        heading_paths[index] = [item[1] for item in stack]

    boundaries = sorted({0, *heading_paths, len(lines)})
    for position, start_line in enumerate(boundaries[:-1]):
        end_line = boundaries[position + 1]
        if start_line == end_line:
            continue
        char_start = starts[start_line]
        char_end = starts[end_line] if end_line < len(lines) else len(text)
        yield char_start, char_end, {
            "heading_path": heading_paths.get(start_line, []),
            "line_start": start_line + 1,
            "line_end": end_line,
        }


def _delimited_segments(
    text: str, *, source_id: str, kind: str, reliability: str
) -> tuple[SourceSegment, ...]:
    """Map form-feed-delimited PDF pages or EPUB spine items to ranges."""

    segments: list[SourceSegment] = []
    offset = 0
    for index, part in enumerate(text.split("\f"), start=1):
        char_start = offset
        char_end = char_start + len(part)
        if part:
            if kind == "pdf":
                locator = {"pdf_page_start": index, "pdf_page_end": index}
            else:
                locator = {"spine_item_start": index, "spine_item_end": index}
            segments.append(
                SourceSegment(
                    id=f"{source_id}-s{len(segments) + 1:04d}",
                    source_id=source_id,
                    char_start=char_start,
                    char_end=char_end,
                    locator=locator,
                    locator_reliability=reliability,
                )
            )
        offset = char_end + 1  # the form-feed delimiter
    return tuple(segments)


def build_extracted_source(
    *,
    path: Path,
    source_id: str,
    document_format: str,
    extraction_method: str,
    text: str,
) -> ExtractedSource:
    """Create provenance records without recording an absolute input path."""

    if document_format == "pdf" and "\f" in text:
        scheme = "pdf-page-index"
        reliability = "high" if extraction_method in {"pdftotext", "pypdf"} else "medium"
        segments = _delimited_segments(
            text, source_id=source_id, kind="pdf", reliability=reliability
        )
    elif document_format == "epub" and "\f" in text:
        scheme = "epub-spine-item"
        reliability = "high"
        segments = _delimited_segments(
            text, source_id=source_id, kind="epub", reliability=reliability
        )
    else:
        scheme = "heading-line-range"
        reliability = "medium"
        segments = tuple(
            SourceSegment(
                id=f"{source_id}-s{index:04d}",
                source_id=source_id,
                char_start=char_start,
                char_end=char_end,
                locator=locator,
                locator_reliability=reliability,
            )
            for index, (char_start, char_end, locator) in enumerate(
                _heading_sections(text), start=1
            )
        )
        if not segments and text:
            segments = (
                SourceSegment(
                    id=f"{source_id}-s0001",
                    source_id=source_id,
                    char_start=0,
                    char_end=len(text),
                    locator={"heading_path": [], "line_start": 1, "line_end": 1},
                    locator_reliability=reliability,
                ),
            )

    return ExtractedSource(
        id=source_id,
        filename=path.name,
        format=document_format,
        sha256=sha256_file(path),
        locator_scheme=scheme,
        locator_reliability=reliability,
        chars=len(text),
        segments=segments,
    )


def render_segments_document(sources: Iterable[ExtractedSource]) -> dict[str, Any]:
    """Render a deterministic JSON-ready segment map."""

    source_list = list(sources)
    return {
        "schema_version": SEGMENT_SCHEMA_VERSION,
        "sources": [
            {
                key: value
                for key, value in source.to_dict().items()
                if key != "segments"
            }
            for source in source_list
        ],
        "segments": [
            segment.to_dict()
            for source in source_list
            for segment in source.segments
        ],
    }
