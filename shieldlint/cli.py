"""Command line interface for ShieldLint."""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

from . import engine, output
from .address import classify
from .rules import RULES
from .uri import parse_payment_uri

EPILOG = """\
examples:
  shieldlint check src/                         lint a source tree
  shieldlint check . --format sarif -o out.sarif
  shieldlint rules                              list every privacy rule
  shieldlint address u1...                      decode an address offline
  shieldlint uri 'zcash:u1...?amount=0.5'
"""


def _version() -> str:
    return f"shieldlint {engine.__version__}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shieldlint",
        description=(
            "Offline static analysis for Zcash privacy leaks: transparent "
            "recipients, memo/key exposure, malformed addresses and broken ZIP 321 "
            "payment requests."
        ),
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=_version())
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    check = sub.add_parser("check", help="lint files or directories")
    check.add_argument("paths", nargs="*", default=["."], help="files or directories (default: .)")
    check.add_argument("--config", help="path to shieldlint.toml / .json")
    check.add_argument(
        "--format",
        choices=("text", "json", "sarif", "github"),
        default="text",
        help="output format (sarif for code scanning, github for workflow commands)",
    )
    check.add_argument("-o", "--output", help="write the report to a file")
    check.add_argument(
        "--fail-on",
        choices=tuple(engine.FAIL_ON_ORDER),
        help="lowest severity that produces exit code 1 (default: error)",
    )
    check.add_argument("--exclude", action="append", default=[], metavar="GLOB", help="skip matching paths (repeatable)")
    check.add_argument("--include-docs", action="store_true", help="also scan .md/.txt documentation")
    check.add_argument("--no-color", action="store_true", help="disable ANSI colors")
    check.add_argument("--quiet", action="store_true", help="only print the summary line")

    rules = sub.add_parser("rules", help="list rules")
    rules.add_argument("--format", choices=("text", "json"), default="text")

    address = sub.add_parser("address", help="decode Zcash addresses / viewing keys offline")
    address.add_argument("values", nargs="+")

    uri = sub.add_parser("uri", help="parse and validate ZIP 321 payment request URIs")
    uri.add_argument("values", nargs="+")

    sub.add_parser("version", help="print the version")
    return parser


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def _cmd_check(args: argparse.Namespace) -> int:
    try:
        config = engine.load_config(args.config)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"shieldlint: {exc}", file=sys.stderr)
        return 2
    if args.fail_on:
        config.fail_on = args.fail_on
    if args.exclude:
        config.exclude.extend(args.exclude)
    if args.include_docs:
        config.include_docs = True

    paths = [Path(p) for p in args.paths]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        print(f"shieldlint: path not found: {', '.join(missing)}", file=sys.stderr)
        return 2
    report = engine.run(paths, config)

    if args.quiet and args.format == "text" and not args.output:
        print(
            f"{report.errors} errors, {report.warnings} warnings, "
            f"{report.notes} notes ({report.files_scanned} files scanned)"
        )
        return 1 if report.exceeds_threshold() else 0

    if args.format == "json":
        text = output.render_json(report)
    elif args.format == "sarif":
        text = output.render_sarif(report)
    elif args.format == "github":
        text = output.render_github(report)
    else:
        buffer = io.StringIO()
        output.render_text(report, buffer, color_off=args.no_color or bool(args.output))
        text = buffer.getvalue()

    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(
            f"wrote {args.format} report to {args.output} "
            f"({report.errors} errors, {report.warnings} warnings)",
            file=sys.stderr,
        )
    else:
        print(text, end="" if text.endswith("\n") else "\n")
    return 1 if report.exceeds_threshold() else 0


def _cmd_rules(args: argparse.Namespace) -> int:
    if args.format == "json":
        import json

        print(
            json.dumps(
                [
                    {
                        "id": r.id,
                        "slug": r.slug,
                        "severity": r.severity,
                        "title": r.title,
                        "summary": r.summary,
                        "rationale": r.rationale,
                        "remediation": r.remediation,
                        "references": [{"label": l, "url": u} for l, u in r.refs],
                    }
                    for r in RULES
                ],
                indent=2,
            )
        )
        return 0
    print(f"{'ID':<7} {'SEVERITY':<8} TITLE")
    for rule in RULES:
        print(f"{rule.id:<7} {rule.severity:<8} {rule.title}")
        print(f"{'':<16}{rule.summary}")
        print(f"{'':<16}docs/rules.md#{rule.slug}")
    return 0


def _cmd_address(args: argparse.Namespace) -> int:
    exit_code = 0
    for value in args.values:
        info = classify(value.strip())
        shown = value.strip()
        print(shown if len(shown) <= 80 else shown[:79] + "…")
        print(f"  kind       {info.kind}")
        print(f"  network    {info.network}")
        if info.hrp:
            print(f"  hrp        {info.hrp}")
        if info.revision is not None:
            print(f"  revision   {info.revision}")
        if info.receivers:
            det = []
            for r in info.receivers:
                det.append(f"{r.name} ({len(r.data)} bytes)")
            print(f"  receivers  {', '.join(det)}")
        for md in info.metadata:
            print(f"  metadata   {md.kind} = {md.value}")
        if info.is_address:
            shielded = bool(info.shielded_receivers) or info.kind == "sapling"
            print(f"  shielded   {'yes' if shielded else 'no'}")
            if info.is_unified and info.has_transparent_receiver:
                print("  warning    Unified Address contains a transparent receiver")
            elif info.is_transparent:
                print("  note       transparent addresses are public on-chain")
        for note in info.notes:
            print(f"  note       {note}")
        for err in info.errors:
            print(f"  error      {err}")
        if not info.ok:
            exit_code = 1
        print()
    return exit_code


def _cmd_uri(args: argparse.Namespace) -> int:
    exit_code = 0
    for value in args.values:
        req = parse_payment_uri(value.strip())
        print(f"{value.strip()[:100]}")
        print(f"  status     {'valid' if req.ok else 'INVALID'}")
        if req.payments:
            print("  payments")
            for payment in req.payments:
                idx = payment.index or "—"
                kind = payment.info.kind if payment.info else "?"
                line = f"    [{idx}] {kind}"
                if payment.amount is not None:
                    line += f"  {payment.amount_text} ZEC"
                if payment.memo:
                    line += f"  memo {len(payment.memo)} bytes"
                if payment.label:
                    line += f"  label {payment.label!r}"
                print(line)
        for err in req.errors:
            print(f"  error      {err}")
        for warn in req.warnings:
            print(f"  warning    {warn}")
        if not req.ok:
            exit_code = 1
        print()
    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command in (None, "version"):
        print(_version())
        return 0
    if args.command == "check":
        return _cmd_check(args)
    if args.command == "rules":
        return _cmd_rules(args)
    if args.command == "address":
        return _cmd_address(args)
    if args.command == "uri":
        return _cmd_uri(args)
    parser.error(f"unknown command {args.command}")  # pragma: no cover
    return 2
