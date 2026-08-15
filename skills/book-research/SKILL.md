---
name: book-research
description: Compare source-checked claims across theology and philosophy book skills and produce a source-traceable research packet. Use when a user asks to compare authors, synthesize books, verify a claim at its locator, or search for counterarguments.
---

# book-research

Compare book skills without conflating an author's statement with the researcher's synthesis.

## Start safely

Read [gotchas.md](references/gotchas.md). Use source-checked claims by default. Treat generated claims only as leads for source rereading.

Resolve the theology-book-to-skill project root from THEOLOGY_BOOK_TO_SKILL_ROOT, the current directory or its parents, or a path supplied by the user. Locate the user's generated books root separately; it is not part of this public skill package.

## Search and verify

1. Convert the research question into the smallest useful axes: concept, Scripture, locus, person, period, method, and author scope.
2. Rebuild the catalog when it is missing or stale.
3. Query the catalog with explicit filters and a bounded limit.
4. Record each selected claim's ID, attribution, chapter path, verification state, and evidence locator.
5. Reopen the relevant source segment for central claims. State when the source is unavailable or a locator cannot be verified.
6. Run one counter-query with an opposing term, an adjacent locus, or a criticism-oriented tag.

~~~bash
python3 <project-root>/tools/query_claim_catalog.py --catalog <books-root>/claim-catalog.json --term "incarnation" --scripture "John 1:14" --verification source-checked --match all --limit 20 --format json
~~~

## Write the research packet

Use this order:

~~~markdown
# Research Packet

## Question and scope
## Selected books and selection rationale
## Each author's claims
## Comparison matrix
## Agreements
## Tensions, counterarguments, and minority positions
## Synthesis
## Inferred connections in the synthesis
## Source locators
## Unresolved questions
~~~

Keep author claims separate from inferred connections. If only one book has relevant evidence, report that cross-book comparison is not established rather than adding weakly related books.

## Report limits

Report the number of source-checked claims used, unverified locators, excluded generated claims, and any partial book coverage. Do not reproduce long source passages in the packet.
