# theology-book-to-skill

[한국어](README.md) · English

An evidence-aware edition of book-to-skill for theology and philosophy. It turns a book you are entitled to use into an agent skill with a domain lens, traceable source segments, atomic claims, and bounded cross-book retrieval.

This repository contains the converter and its research workflow. It does not distribute books, extracted full text, or generated notes from copyrighted sources.

## Core capabilities

- Theology and philosophy lenses structure doctrinal loci, original-language terms, arguments, methods, persons, and Scripture references.
- `segments.json` deterministically maps extracted text to source pages, EPUB spine items, or text headings and lines.
- `claim-index.json` strictly records atomic claims, evidence locators, and verification state for one book.
- `claim-catalog.json` returns a small, explainable cross-book evidence set rather than an unbounded text dump.
- The workflow distinguishes generated candidates from claims reread against the original source and marked `source-checked`.

## Outputs

Normal conversion produces an agent skill with a master `SKILL.md`, chapter files, and supporting material. Theology and philosophy workflows also use:

| File | Purpose |
| --- | --- |
| `segments.json` | Portable provenance for extracted text |
| `claim-index.json` | Source-linked atomic claims for one book |
| `claim-catalog.json` | Rebuildable cross-book retrieval index |
| `lexicon.md` | Technical and original-language vocabulary |
| `core_arguments.md` | Arguments, doctrinal positions, and distinctions |
| `methodology.md` | Interpretive and research method |

Source files are never copied into these indexes. Source identity uses a filename and SHA-256 digest, not a local absolute path.

## Quick start

Clone the repository, then extract a book you own or are authorized to process.

```bash
git clone https://github.com/mitmirsein/theology-book-to-skill.git
cd theology-book-to-skill
uv sync --all-extras
uv run book-to-skill path/to/book.pdf
```

## Included public skills

This repository includes two installable agent skills and no generated book content.

| Skill | Role |
| --- | --- |
| [book-to-skill](skills/book-to-skill/SKILL.md) | Convert permitted theology and philosophy sources into traceable research skills |
| [book-research](skills/book-research/SKILL.md) | Compare verified claims across book skills and write a research packet |

Copy both directories into your host's personal skills directory, then provide the project checkout path or set `THEOLOGY_BOOK_TO_SKILL_ROOT`.

```bash
cp -R skills/book-to-skill ~/.claude/skills/
cp -R skills/book-research ~/.claude/skills/
export THEOLOGY_BOOK_TO_SKILL_ROOT="$PWD"
```

For another Agent Skills host, copy the same directories to that host's personal skills root. The skills search for the project root and ask for its path when it cannot be found.

Build and query a claim catalog for a generated books directory:

```bash
python3 tools/build_claim_catalog.py --books-root "$SKILLS_HOME"
python3 tools/query_claim_catalog.py --catalog "$SKILLS_HOME/claim-catalog.json" --term "incarnation" --scripture "John 1:14" --match all
```

Use only `source-checked` records where source attribution must be accurate. A generated claim remains a candidate until it has been reread against the source and given a locator.

## Research safeguards

- Open the original source when precision matters; a claim index is not a substitute for it.
- Preserve page locators and the source digest when verifying or updating a book.
- Do not publish generated skills or claim indexes derived from copyrighted books unless you have the required rights.
- Do not commit source PDFs, EPUBs, full extracted text, API keys, or machine-specific paths.

## Repository layout

```text
book_to_skill/       converter, provenance, claims, and catalogs
tools/               catalog construction, querying, and validation tools
tests/               automated coverage for the code surface
docs/                architecture and operating documentation
SKILL.md             agent workflow for generating research skills
```

The two public distribution skills are versioned with this project. A user's personal global skills library and generated book content can remain separate.

## Upstream acknowledgement

This project is an independent specialized edition based on [virgiliojr94/book-to-skill](https://github.com/virgiliojr94/book-to-skill) by Virgilio. The upstream project established the general-purpose book-to-agent-skill converter on which this edition builds.

The original copyright notice is retained under the MIT License:

> Copyright (c) 2025 virgiliojr94

This edition maintains the domain lens, provenance, claim index, and cross-book evidence-retrieval additions. Upstream changes are reviewed and integrated deliberately so that domain-specific research guarantees remain intact.

## License

MIT. See [LICENSE.md](LICENSE.md). The license covers this converter and its documentation, not the books or documents that users process with it.
