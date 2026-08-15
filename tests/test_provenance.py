import hashlib
import json
import sys

from book_to_skill.provenance import build_extracted_source, render_segments_document
from book_to_skill.utils import main


def test_text_provenance_uses_heading_and_line_locators_without_a_path(tmp_path):
    source = tmp_path / "notes.md"
    source.write_text("# Title\nIntro\n## First\nBody\n## Second\nMore\n", encoding="utf-8")

    extracted = build_extracted_source(
        path=source,
        source_id="source-01",
        document_format="md",
        extraction_method="plain-text",
        text=source.read_text(encoding="utf-8"),
    )

    assert extracted.filename == "notes.md"
    assert extracted.sha256 == hashlib.sha256(source.read_bytes()).hexdigest()
    assert str(tmp_path) not in json.dumps(extracted.to_dict())
    assert [segment.locator["heading_path"] for segment in extracted.segments] == [
        ["Title"],
        ["Title", "First"],
        ["Title", "Second"],
    ]
    assert extracted.segments[1].locator["line_start"] == 3
    assert extracted.segments[1].char_end <= len(source.read_text(encoding="utf-8"))


def test_pdf_and_epub_segments_retain_delimited_locator_ranges(tmp_path):
    source = tmp_path / "book.pdf"
    source.write_bytes(b"not a real PDF")

    pdf = build_extracted_source(
        path=source,
        source_id="source-01",
        document_format="pdf",
        extraction_method="pypdf",
        text="first page\fsecond page",
    )
    assert pdf.locator_scheme == "pdf-page-index"
    assert [segment.locator["pdf_page_start"] for segment in pdf.segments] == [1, 2]

    epub = build_extracted_source(
        path=source,
        source_id="source-02",
        document_format="epub",
        extraction_method="zipfile",
        text="chapter one\fchapter two",
    )
    assert epub.locator_scheme == "epub-spine-item"
    assert [segment.locator["spine_item_start"] for segment in epub.segments] == [1, 2]


def test_main_writes_deterministic_portable_segments_json(tmp_path, monkeypatch):
    source = tmp_path / "source.md"
    source.write_text("# Title\n\n## One\nText\n\n## Two\nMore\n", encoding="utf-8")
    output_dir = tmp_path / "output"
    monkeypatch.setattr(sys, "argv", ["extract.py", str(source)])
    monkeypatch.setattr("book_to_skill.utils.OUTPUT_DIR", output_dir)
    monkeypatch.setattr("book_to_skill.utils.OUTPUT_TEXT", output_dir / "full_text.txt")
    monkeypatch.setattr("book_to_skill.utils.OUTPUT_META", output_dir / "metadata.json")
    monkeypatch.setattr("book_to_skill.utils.OUTPUT_SEGMENTS", output_dir / "segments.json")
    monkeypatch.setattr("book_to_skill.utils.prepare_dependencies", lambda *args: None)

    main()
    first = (output_dir / "segments.json").read_bytes()
    main()
    second = (output_dir / "segments.json").read_bytes()

    document = json.loads(first)
    assert first == second
    assert document["schema_version"] == 1
    assert document["sources"][0]["filename"] == "source.md"
    assert str(tmp_path) not in first.decode("utf-8")
    assert document["segments"][0]["source_id"] == "source-01"
    assert render_segments_document(()) == {
        "schema_version": 1,
        "sources": [],
        "segments": [],
    }
