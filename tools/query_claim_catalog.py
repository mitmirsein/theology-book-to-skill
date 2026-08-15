#!/usr/bin/env python3
"""Query a claim catalog without emitting the full catalog."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from book_to_skill.claim_catalog import (  # noqa: E402
    ClaimCatalogError,
    ClaimCatalogQuery,
    ClaimQueryError,
    load_claim_catalog,
    query_claim_catalog,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", required=True, type=Path)
    for option, destination in (("--tag", "tags"), ("--term", "terms"), ("--scripture", "scriptures"), ("--locus", "loci"), ("--person", "persons"), ("--type", "types"), ("--verification", "verification")):
        parser.add_argument(option, dest=destination, action="append", default=[])
    parser.add_argument("--book")
    parser.add_argument("--match", choices=("all", "any"), default="all")
    parser.add_argument("--include-generated", action="store_true")
    parser.add_argument("--min-books", type=int, default=1)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args(argv)
    query = ClaimCatalogQuery(
        tags=args.tags, terms=args.terms, scriptures=args.scriptures, loci=args.loci,
        persons=args.persons, types=args.types, verification=args.verification, book=args.book,
        match=args.match, include_generated=args.include_generated, min_books=args.min_books, limit=args.limit,
    )
    try:
        results = query_claim_catalog(load_claim_catalog(args.catalog), query)
    except ClaimQueryError as exc:
        print(f"ERROR invalid claim catalog query: {exc}", file=sys.stderr)
        return 2
    except ClaimCatalogError as exc:
        print(f"ERROR claim catalog query failed: {exc}", file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps({"schema_version": 1, "results": results}, ensure_ascii=False, indent=2))
    else:
        for item in results:
            print(f"- {item['claim_id']} — {item['display']} ({item['book_id']}/{item['chapter_id']}; {item['verification']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
