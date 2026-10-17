"""Render reports as human text, JSON or SARIF 2.1.0."""

from __future__ import annotations

import json
import os
import shutil
import textwrap
from typing import TextIO

from .engine import Report, __version__
from .rules import RULES

_COLORS = {
    "error": "\033[31m",
    "warning": "\033[33m",
    "note": "\033[36m",
    "dim": "\033[2m",
    "bold": "\033[1m",
    "reset": "\033[0m",
    "green": "\033[32m",
}


def _supports_color(stream: TextIO, force_off: bool) -> bool:
    if force_off or os.environ.get("NO_COLOR"):
        return False
    return bool(getattr(stream, "isatty", lambda: False)())


def render_text(report: Report, stream: TextIO, color_off: bool = False) -> None:
    color = _supports_color(stream, color_off)

    def paint(text: str, key: str) -> str:
        return f"{_COLORS.get(key, '')}{text}{_COLORS['reset']}" if color else text

    width = min(shutil.get_terminal_size((100, 20)).columns, 110)
    out = stream.write

    header = (
        f"shieldlint {__version__}  ·  {report.files_scanned} file"
        f"{'s' if report.files_scanned != 1 else ''} scanned"
    )
    if report.findings:
        header += (
            f"  ·  {report.errors} error{'s' if report.errors != 1 else ''}, "
            f"{report.warnings} warning{'s' if report.warnings != 1 else ''}"
        )
    out(paint(header, "bold") + "\n")
    if not report.findings:
        out(paint("✔ no findings", "green") + "\n")
        return

    current = None
    for finding in report.findings:
        if finding.path != current:
            current = finding.path
            out("\n" + paint(current, "bold") + "\n")
        location = f"{finding.line}:{finding.col}"
        sev = paint(f"{finding.severity:<7}", finding.severity)
        out(
            f"  {location:<9} {sev} {paint(finding.rule.id, 'dim')}  "
            f"{finding.message}\n"
        )
        detail = finding.detail
        if detail:
            indent = " " * 22
            for line in textwrap.wrap(
                detail, width=max(40, width - 22), break_long_words=False
            ):
                out(f"{indent}{paint(line, 'dim')}\n")
        out(
            f"{' ' * 22}{paint('help: ' + finding.rule.url, 'dim')}\n"
        )
    out("\n")
    summary = (
        f"{report.errors} errors, {report.warnings} warnings, {report.notes} notes "
        f"across {report.files_with_findings} file"
        f"{'s' if report.files_with_findings != 1 else ''}"
    )
    out(paint(summary, "bold") + f"   (fail-on={report.config.fail_on})\n")
    if report.exceeds_threshold():
        out(paint("✖ findings at or above the failure threshold", "error") + "\n")
    else:
        out(paint("✔ nothing at or above the failure threshold", "green") + "\n")


def render_json(report: Report) -> str:
    payload = {
        "tool": {"name": "shieldlint", "version": __version__},
        "summary": {
            "files_scanned": report.files_scanned,
            "files_with_findings": report.files_with_findings,
            "errors": report.errors,
            "warnings": report.warnings,
            "notes": report.notes,
            "by_rule": report.counts_by_rule(),
            "fail_on": report.config.fail_on,
            "exceeds_threshold": report.exceeds_threshold(),
        },
        "findings": [f.to_dict() for f in report.findings],
    }
    return json.dumps(payload, indent=2)


def render_sarif(report: Report) -> str:
    rules = []
    for rule in RULES:
        rules.append(
            {
                "id": rule.id,
                "name": rule.slug,
                "shortDescription": {"text": rule.title},
                "fullDescription": {"text": rule.summary},
                "helpUri": rule.url,
                "help": {
                    "text": f"{rule.rationale}\n\nRemediation: {rule.remediation}"
                },
                "defaultConfiguration": {"level": rule.severity},
                "properties": {
                    "tags": ["privacy", "zcash"],
                    "references": [url for _, url in rule.refs],
                },
            }
        )
    results = []
    for finding in report.findings:
        results.append(
            {
                "ruleId": finding.rule.id,
                "level": finding.severity,
                "message": {
                    "text": finding.message + (f" — {finding.detail}" if finding.detail else "")
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": finding.path.replace(os.sep, "/"),
                                "uriBaseId": "%SRCROOT%",
                            },
                            "region": {
                                "startLine": max(1, finding.line),
                                "startColumn": max(1, finding.col),
                            },
                        }
                    }
                ],
                "partialFingerprints": {
                    "shieldlintRuleAndSnippet": f"{finding.rule.id}:{finding.snippet[:80]}"
                },
            }
        )
    sarif = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "ShieldLint",
                        "version": __version__,
                        "informationUri": "https://github.com/OWNER/REPO",
                        "rules": rules,
                    }
                },
                "results": results,
                "properties": {
                    "summary": {
                        "files_scanned": report.files_scanned,
                        "errors": report.errors,
                        "warnings": report.warnings,
                    }
                },
            }
        ],
    }
    return json.dumps(sarif, indent=2)


def render_github(report: Report) -> str:
    """GitHub Actions workflow commands (inline annotations)."""
    lines = []
    for finding in report.findings:
        command = {"error": "error", "warning": "warning", "note": "notice"}[
            finding.severity
        ]
        message = finding.message.replace("%", "%25").replace("\n", "%0A").replace("\r", "%0D")
        lines.append(
            f"::{command} file={finding.path},line={finding.line},col={finding.col},"
            f"title={finding.rule.id} {finding.rule.title}::{message}"
        )
    return "\n".join(lines)
