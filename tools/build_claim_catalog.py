#!/usr/bin/env python3
"""Build a deterministic claim-catalog.json from migrated book claim indexes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from book_to_skill.claim_catalog import (  # noqa: E402
    ClaimCatalogError,
    build_claim_catalog,
    discover_claim_indexes,
    write_claim_catalog_atomic,
)
from book_to_skill.claims import load_claim_index  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--books-root", required=True, type=Path)
    parser.add_argument("--check", action="store_true", help="validate and build without replacing claim-catalog.json")
    args = parser.parse_args(argv)
    try:
        paths, missing = discover_claim_indexes(args.books_root)
        catalog = build_claim_catalog(
            [(path, load_claim_index(path)) for path in paths],
            args.books_root,
            missing_books=missing,
        )
        if not args.check:
            write_claim_catalog_atomic(catalog, args.books_root)
    except ClaimCatalogError as exc:
        print(f"ERROR claim catalog build failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"Claim catalog {'check passed' if args.check else 'built'}: "
        f"claims={len(catalog['claims'])}, ready_books={sum(item['migration_status'] == 'ready' for item in catalog['books'].values())}, "
        f"partial_books={sum(item['migration_status'] == 'partial' for item in catalog['books'].values())}, "
        f"missing_books={sum(item['migration_status'] == 'missing' for item in catalog['books'].values())}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
