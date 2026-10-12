"""Command line interface: ``changeimagehash photo.png ./folder --overwrite``."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from changeimagehash import __version__
from changeimagehash.core import DEFAULT_SUFFIX, change_hash, collect_files
from changeimagehash.formats import FormatError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="changeimagehash",
        description=(
            "Give images a new MD5/SHA-256 hash without changing how they look. "
            "By default a copy is saved next to each original."
        ),
    )
    parser.add_argument("paths", nargs="+", metavar="PATH", help="image files or folders")
    parser.add_argument(
        "--overwrite", action="store_true", help="modify the original files instead of saving copies"
    )
    parser.add_argument(
        "--suffix",
        default=DEFAULT_SUFFIX,
        help=f"suffix added to copies (default: {DEFAULT_SUFFIX!r})",
    )
    parser.add_argument("-o", "--output-dir", metavar="DIR", help="save copies into this folder")
    parser.add_argument("-r", "--recursive", action="store_true", help="include images in subfolders")
    parser.add_argument(
        "--all-files", action="store_true", help="process every file in folders, not just images"
    )
    parser.add_argument("--json", action="store_true", help="print results as JSON")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return the exit code: 0 ok, 1 some files failed, 2 nothing to do."""
    args = build_parser().parse_args(argv)
    if args.overwrite and args.output_dir:
        print("error: --overwrite and --output-dir cannot be used together", file=sys.stderr)
        return 2

    files = collect_files(args.paths, recursive=args.recursive, all_files=args.all_files)
    if not files:
        print("error: no files found", file=sys.stderr)
        return 2

    results, failures = [], 0
    for path in files:
        try:
            result = change_hash(
                path, overwrite=args.overwrite, suffix=args.suffix, output_dir=args.output_dir
            )
        except (OSError, FormatError) as exc:
            failures += 1
            print(f"error: {path}: {exc}", file=sys.stderr)
            continue
        results.append(result)
        if not args.json:
            print(f"{result.source} -> {result.output}  [{result.method}]")
            print(f"    MD5     {result.before.md5} -> {result.after.md5}")
            print(f"    SHA-256 {result.before.sha256} -> {result.after.sha256}")

    if args.json:
        payload = [
            {
                "source": str(r.source),
                "output": str(r.output),
                "method": r.method,
                "md5_before": r.before.md5,
                "md5_after": r.after.md5,
                "sha256_before": r.before.sha256,
                "sha256_after": r.after.sha256,
            }
            for r in results
        ]
        print(json.dumps(payload, indent=2))
    else:
        print(f"\nDone: {len(results)} changed, {failures} failed.")
    return 1 if failures else 0
