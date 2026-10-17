"""Rule execution, configuration and reporting."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .address import classify, iter_address_tokens
from .rules import (
    ALL_RULES,
    AddressHit,
    FileEvidence,
    Rule,
    Symbol,
    UriHit,
)
from .source import SourceFile, discover, load_file
from .uri import parse_payment_uri

__version__ = "0.1.0"

SEVERITY_ORDER = {"error": 0, "warning": 1, "note": 2}
FAIL_ON_ORDER = {"error": 0, "warning": 1, "note": 2, "never": 99, "none": 99}


@dataclass
class Finding:
    rule: Rule
    path: str
    line: int
    col: int
    message: str
    detail: str = ""
    snippet: str = ""

    @property
    def severity(self) -> str:
        return self.rule.severity

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule.id,
            "slug": self.rule.slug,
            "severity": self.severity,
            "title": self.rule.title,
            "message": self.message,
            "detail": self.detail,
            "path": self.path,
            "line": self.line,
            "column": self.col,
            "snippet": self.snippet,
            "help": self.rule.url,
            "references": [{"label": label, "url": url} for label, url in self.rule.refs],
        }


@dataclass
class Config:
    exclude: list[str] = field(default_factory=list)
    include_docs: bool = False
    fail_on: str = "error"
    disable: set[str] = field(default_factory=set)
    severity: dict[str, str] = field(default_factory=dict)
    config_path: str | None = None


@dataclass
class Report:
    findings: list[Finding]
    files_scanned: int
    files_with_findings: int
    config: Config

    @property
    def errors(self) -> int:
        return sum(1 for f in self.findings if f.severity == "error")

    @property
    def warnings(self) -> int:
        return sum(1 for f in self.findings if f.severity == "warning")

    @property
    def notes(self) -> int:
        return sum(1 for f in self.findings if f.severity == "note")

    def counts_by_rule(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for finding in self.findings:
            counts[finding.rule.id] = counts.get(finding.rule.id, 0) + 1
        return dict(sorted(counts.items()))

    def exceeds_threshold(self) -> bool:
        threshold = FAIL_ON_ORDER.get(self.config.fail_on, 0)
        if threshold >= FAIL_ON_ORDER["never"]:
            return False
        return any(SEVERITY_ORDER[f.severity] <= threshold for f in self.findings)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def _apply_table(table: dict[str, Any], config: Config) -> Config:
    exclude = table.get("exclude", [])
    if isinstance(exclude, str):
        exclude = [exclude]
    config.exclude = list(exclude)
    config.include_docs = bool(table.get("include_docs", config.include_docs))
    fail_on = str(table.get("fail_on", config.fail_on)).lower()
    if fail_on not in FAIL_ON_ORDER:
        raise ValueError(
            f"fail_on must be one of {', '.join(sorted(FAIL_ON_ORDER))}, got {fail_on!r}"
        )
    config.fail_on = fail_on
    disable = table.get("disable", [])
    if isinstance(disable, str):
        disable = [disable]
    config.disable = {str(d).upper() for d in disable}
    severity = table.get("severity", {})
    if isinstance(severity, dict):
        for rule_id, level in severity.items():
            level = str(level).lower()
            if level not in SEVERITY_ORDER:
                raise ValueError(f"invalid severity {level!r} for {rule_id}")
            config.severity[str(rule_id).upper()] = level
    return config


def load_config(path: str | Path | None) -> Config:
    config = Config()
    if path is None:
        for candidate in ("shieldlint.toml", ".shieldlint.toml", "shieldlint.json"):
            if Path(candidate).is_file():
                path = candidate
                break
    if path is None:
        return config
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"config file not found: {p}")
    config.config_path = str(p)
    if p.suffix == ".json":
        data = json.loads(p.read_text(encoding="utf-8"))
        table = data.get("shieldlint", data)
    else:
        try:
            import tomllib
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise RuntimeError(
                "TOML config requires Python 3.11+ (tomllib); use JSON instead"
            ) from exc
        data = tomllib.loads(p.read_text(encoding="utf-8"))
        table = data.get("shieldlint", data)
    if not isinstance(table, dict):
        raise ValueError("config must contain a [shieldlint] table")
    return _apply_table(table, config)


# ---------------------------------------------------------------------------
# Evidence collection
# ---------------------------------------------------------------------------


_URI_BODY_RE = re.compile(
    r"^(?:\?|(?:u|zu|tu|utest|zutest|tutest|uregtest|zuregtest|turegtest|"
    r"zs|ztestsapling|zregtestsapling|zc|zt|t1|t3|tm|t2|t))"
)


def _looks_like_payment_uri(text: str) -> bool:
    """Avoid treating prose that merely mentions ``zcash:`` as a payment URI."""
    body = text[len("zcash:") :]
    if len(body) < 2:
        return False
    if body[0] == "?":
        return True
    return bool(_URI_BODY_RE.match(body))


def _trim_uri(value: str) -> str:
    for i, ch in enumerate(value):
        if ch.isspace() or ch in "\"'`<>":
            return value[:i]
    return value


def _assignee(text: str, offset: int) -> str | None:
    import re

    prefix = text[max(0, offset - 200) : offset]
    match = re.search(
        r"([A-Za-z_]\w*)\s*(?::\s*[^=]{1,40})?=\s*[(\s]*[\"'`]*$", prefix
    )
    return match.group(1) if match else None


def build_evidence(file: SourceFile) -> FileEvidence:
    evidence = FileEvidence(file=file)
    for literal in file.literals:
        value = literal.value
        tokens = list(iter_address_tokens(value))
        if len(tokens) == 1 and tokens[0].start == 0 and tokens[0].end == len(value):
            name = _assignee(file.text, literal.start)
            if name:
                info = classify(tokens[0].text, tokens[0].kind_hint)
                line, col = file.line_col(literal.start)
                evidence.symbols[name] = Symbol(name=name, info=info, line=line, col=col)
        uri_pos = value.lower().find("zcash:")
        uri_text = ""
        uri_end = -1
        if uri_pos != -1 and literal.interpolated:
            uri_pos = -1  # dynamic URI: cannot be validated statically
        elif uri_pos != -1:
            candidate = _trim_uri(value[uri_pos:])
            if _looks_like_payment_uri(candidate):
                uri_text = candidate
            else:
                uri_pos = -1
        if uri_pos != -1:
            request = parse_payment_uri(uri_text)
            offset = literal.start + uri_pos
            line, col = file.line_col(offset)
            evidence.uris.append(
                UriHit(
                    literal=literal,
                    text=uri_text,
                    offset=offset,
                    line=line,
                    col=col,
                    request=request,
                )
            )
            uri_end = uri_pos + len(uri_text)
        for tok in iter_address_tokens(value):
            in_uri = uri_pos != -1 and uri_pos <= tok.start < uri_end
            info = classify(tok.text, tok.kind_hint)
            line, col = file.line_col(literal.start + tok.start)
            evidence.addresses.append(
                AddressHit(
                    literal=literal,
                    token=tok.text,
                    offset=literal.start + tok.start,
                    line=line,
                    col=col,
                    info=info,
                    in_uri=in_uri,
                )
            )
    return evidence


# ---------------------------------------------------------------------------
# Running
# ---------------------------------------------------------------------------


def run(
    paths: Iterable[str | Path],
    config: Config | None = None,
    root: Path | None = None,
) -> Report:
    config = config or Config()
    root = (root or Path.cwd()).resolve()
    files = discover(paths, exclude_globs=config.exclude, include_docs=config.include_docs)

    findings: list[Finding] = []
    seen: set[tuple[str, str, int, int]] = set()
    files_with_findings: set[str] = set()
    for path in files:
        source = load_file(path, root)
        if source is None:
            continue
        evidence = build_evidence(source)
        for rule_fn in ALL_RULES:
            for finding in rule_fn(evidence):
                rule = finding.rule
                if rule.id in config.disable:
                    continue
                if source.suppressed(rule.id, finding.line):
                    continue
                level = config.severity.get(rule.id)
                if level and level != rule.severity:
                    finding.rule = Rule(
                        id=rule.id,
                        slug=rule.slug,
                        severity=level,
                        title=rule.title,
                        summary=rule.summary,
                        rationale=rule.rationale,
                        remediation=rule.remediation,
                        refs=rule.refs,
                    )
                key = (finding.rule.id, finding.path, finding.line)
                if key in seen:
                    continue
                seen.add(key)
                findings.append(finding)
                files_with_findings.add(finding.path)

    findings.sort(
        key=lambda f: (
            f.path,
            f.line,
            f.col,
            SEVERITY_ORDER.get(f.severity, 9),
            f.rule.id,
        )
    )
    return Report(
        findings=findings,
        files_scanned=len(files),
        files_with_findings=len(files_with_findings),
        config=config,
    )
