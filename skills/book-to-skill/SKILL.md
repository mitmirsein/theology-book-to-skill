---
name: book-to-skill
description: Convert theology and philosophy books into evidence-aware agent skills with source segments, atomic claim indexes, and bounded cross-book retrieval. Use when a user wants to transform a permitted PDF, EPUB, document folder, or text source into a reusable research skill.
---

# book-to-skill

Convert a permitted source into a research skill without copying the source text into the output repository.

## Resolve the project

Find the theology-book-to-skill project root in this order:

1. Use THEOLOGY_BOOK_TO_SKILL_ROOT when it names a directory containing pyproject.toml.
2. Search the current directory and its parents for a directory containing pyproject.toml, book_to_skill/, and tools/.
3. Ask the user for the checked-out project path.

Read <project-root>/SKILL.md before conversion. It is the detailed, version-matched generator workflow.

## Convert a source

1. Confirm that the user owns the source or is authorized to process it. Do not ingest a source merely because it is publicly reachable.
2. Identify the input files and a stable skill slug. Preserve a source filename and SHA-256 digest, never an absolute local path.
3. Extract text with the repository workflow. Preserve PDF page boundaries and EPUB spine boundaries.
4. Generate the book skill with concise chapter files, a lexicon, core arguments, and methodology. Distinguish source statements from the researcher's synthesis.
5. Write segments.json and a strict claim-index.json. A claim is atomic, has an evidence locator, and remains generated until reread against the source.
6. Mark a claim source-checked only after reopening the locator's source segment. Do not infer authorial agreement from matching tags.
7. Validate the generated skill and scan it before publishing or using it.

## Cross-book retrieval

For a directory of generated book skills, rebuild the derived catalog and use bounded queries:

~~~bash
python3 <project-root>/tools/build_claim_catalog.py --books-root <books-root>
python3 <project-root>/tools/query_claim_catalog.py --catalog <books-root>/claim-catalog.json --term "<term>" --verification source-checked --format json
~~~

Treat claim-catalog.json as rebuildable. claim-index.json and book-index.json remain the book-level sources of truth.

## Guardrails

- Do not publish copyrighted source files, full extracted text, or generated book skills without the required rights.
- Do not fabricate locators, verification state, original-language forms, or quotations.
- Report missing sources, partial chapter coverage, and unverifiable locators plainly.
