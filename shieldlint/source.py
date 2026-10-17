"""Source discovery, lightweight lexing and inline suppression.

The lexer does not try to be a compiler front-end.  It blanks out comments
and string *contents* while preserving offsets and line numbers, which is
enough to run privacy rules that are driven by (a) identifiers in code and
(b) the exact string literals that carry addresses, keys and memos.
"""

from __future__ import annotations

import bisect
import fnmatch
import os
import re
from functools import lru_cache
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

DEFAULT_SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "target",
    "build",
    "dist",
    "out",
    "vendor",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".next",
    ".nuxt",
    "coverage",
    ".idea",
    ".vscode",
}

DEFAULT_EXCLUDE_GLOBS = [
    "*.min.js",
    "*.min.css",
    "*.map",
    "*.lock",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "Cargo.lock",
    "poetry.lock",
    "*.svg",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.ico",
    "*.pdf",
]

EXTENSIONS = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "javascript",
    ".tsx": "javascript",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
    ".kt": "java",
    ".kts": "java",
    ".cs": "csharp",
    ".c": "c",
    ".h": "c",
    ".cpp": "c",
    ".hpp": "c",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".env": "shell",
    ".conf": "shell",
    ".ini": "shell",
}

MAX_FILE_BYTES = 2 * 1024 * 1024

_DIRECTIVE_RE = re.compile(
    r"shieldlint:\s*(ignore|disable-file)\b(?:\s*\[([A-Za-z0-9_,\s]+)\])?",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Lexing
# ---------------------------------------------------------------------------

@dataclass
class Literal:
    """A string literal (contents only) with its position in the file."""

    value: str
    start: int  # offset of first character of the value
    end: int  # offset just past the last character
    line: int
    col: int
    quote: str
    language: str
    interpolated: bool = False


@dataclass
class ScanResult:
    masked: str
    literals: list[Literal]


def _spec(lang: str) -> dict:
    if lang == "python":
        return {"line": ("#",), "block": (), "quotes": ("'", '"'), "triple": True, "prefixes": True}
    if lang == "javascript":
        return {"line": ("//",), "block": (("/*", "*/"),), "quotes": ("'", '"', "`"), "triple": False, "prefixes": False}
    if lang == "rust":
        return {"line": ("//",), "block": (("/*", "*/"),), "quotes": ('"',), "triple": False, "prefixes": True, "nested_block": True}
    if lang == "go":
        return {"line": ("//",), "block": (("/*", "*/"),), "quotes": ('"', "`"), "triple": False, "prefixes": False}
    if lang == "ruby":
        return {"line": ("#",), "block": (), "quotes": ("'", '"'), "triple": False, "prefixes": False}
    if lang == "php":
        return {"line": ("//", "#"), "block": (("/*", "*/"),), "quotes": ("'", '"'), "triple": False, "prefixes": False}
    if lang in {"json"}:
        return {"line": (), "block": (), "quotes": ('"',), "triple": False, "prefixes": False}
    if lang in {"yaml", "toml"}:
        return {"line": ("#",), "block": (), "quotes": ('"', "'"), "triple": False, "prefixes": False}
    if lang == "shell":
        return {"line": ("#",), "block": (), "quotes": ('"', "'"), "triple": False, "prefixes": False}
    # java, csharp, c, swift
    return {
        "line": ("//",),
        "block": (("/*", "*/"),),
        "quotes": ('"', "'"),
        "triple": False,
        "prefixes": False,
        "nested_block": lang == "swift",
    }


_CHAR_LIT_RE = re.compile(r"'(?:\\u\{[0-9a-fA-F]{1,6}\}|\\.|[^\\'\n])'")
_JS_REGEX_PREV = set("([{:;,=!&|?+-*%^~<>")
_JS_REGEX_KEYWORDS = ("return", "typeof", "case", "instanceof", "in", "of", "new", "delete", "void", "yield", "await")


def _regex_allowed(text: str, i: int) -> bool:
    """Heuristic: can a '/' at ``i`` start a regex literal in JavaScript?"""
    j = i - 1
    while j >= 0 and text[j] in " \t\r\n":
        j -= 1
    if j < 0:
        return True
    prev = text[j]
    if prev in _JS_REGEX_PREV:
        return True
    if prev.isalnum() or prev in "_$":
        word = re.search(r"[A-Za-z_$][A-Za-z0-9_$]*$", text[max(0, j - 20) : j + 1])
        return bool(word and word.group(0) in _JS_REGEX_KEYWORDS)
    return False


@lru_cache(maxsize=None)
def _opener_re(lang: str) -> re.Pattern[str]:
    """Regex that finds the next construct worth handling in ``lang``."""
    spec = _spec(lang)
    alts: list[str] = []
    for marker in spec["line"]:
        alts.append(re.escape(marker) + r"[^\n]*")
    for opener, _closer in spec["block"]:
        alts.append(re.escape(opener))
    if lang == "python":
        alts.append('"""')
        alts.append("'''")
    if lang == "rust":
        alts.append(r'(?<![A-Za-z0-9_])(?:b?r)(#*)?"')
    quotes = "".join(re.escape(q) for q in spec["quotes"])
    if quotes:
        alts.append("[" + quotes + "]")
    if lang == "javascript":
        alts.append("/")  # last: "//" and "/*" win at the same position
    return re.compile("|".join(alts))


def scan(text: str, lang: str) -> ScanResult:
    """Blank comments and string bodies, collecting string literals.

    The scanner jumps from one interesting construct to the next with a
    single regex, so cost is proportional to the number of comments/strings
    rather than to the number of characters.
    """
    spec = _spec(lang)
    pattern = _opener_re(lang)
    out = list(text)
    literals: list[Literal] = []
    n = len(text)

    line_starts = [0]
    for idx, ch in enumerate(text):
        if ch == "\n":
            line_starts.append(idx + 1)

    def position(offset: int) -> tuple[int, int]:
        line_idx = bisect.bisect_right(line_starts, offset) - 1
        return line_idx + 1, offset - line_starts[line_idx] + 1

    def blank(a: int, b: int) -> None:
        for k in range(a, min(b, n)):
            if out[k] != "\n":
                out[k] = " "

    i = 0
    while i < n:
        match = pattern.search(text, i)
        if not match:
            break
        start, end, tok = match.start(), match.end(), match.group(0)

        # -- line comments (the regex consumes to end of line) ---------------
        if any(tok.startswith(marker) for marker in spec["line"]):
            blank(start, end)
            i = end
            continue

        # -- block comments ---------------------------------------------------
        block = next(((o, c) for o, c in spec["block"] if tok == o), None)
        if block is not None:
            opener, closer = block
            j = end
            depth = 1
            while j < n and depth:
                if spec.get("nested_block") and text.startswith(opener, j):
                    depth += 1
                    j += len(opener)
                elif text.startswith(closer, j):
                    depth -= 1
                    j += len(closer)
                else:
                    j += 1
            blank(start, j)
            i = j
            continue

        # -- Python triple-quoted strings (docstrings): treated as prose ------
        if tok in ('"""', "'''"):
            close = text.find(tok, end)
            close = n if close == -1 else close + 3
            blank(start, close)
            i = close
            continue

        # -- Rust raw / byte-raw strings --------------------------------------
        if lang == "rust" and tok[0] in "rb" and tok.endswith('"'):
            hashes = tok.count("#")
            terminator = '"' + "#" * hashes
            body_start = end
            close = text.find(terminator, body_start)
            close = n if close == -1 else close
            literals.append(
                Literal(
                    text[body_start:close],
                    body_start,
                    close,
                    *position(body_start),
                    '"',
                    lang,
                )
            )
            blank(body_start, close)
            i = min(n, close + len(terminator))
            continue

        # -- JavaScript regex literals ----------------------------------------
        if tok == "/":
            if not _regex_allowed(text, start):
                i = start + 1
                continue
            j = start + 1
            in_class = False
            while j < n:
                c = text[j]
                if c == "\\":
                    j += 2
                    continue
                if c == "[":
                    in_class = True
                elif c == "]":
                    in_class = False
                elif c == "/" and not in_class:
                    j += 1
                    break
                elif c == "\n":
                    break
                j += 1
            while j < n and text[j].isalpha():
                j += 1  # flags
            blank(start, j)
            i = j
            continue

        # -- character literals that contain a quote ('"', '\'') --------------
        if tok == "'" and lang in {"rust", "c", "java", "csharp", "swift"}:
            char_match = _CHAR_LIT_RE.match(text, start)
            if char_match:
                blank(start, char_match.end())
                i = char_match.end()
                continue
            if lang == "rust":
                i = start + 1  # a lifetime or label, not a string
                continue

        # -- ordinary strings ---------------------------------------------------
        prefix = ""
        if lang == "python":
            k = 0
            while (
                k < 2
                and start - k - 1 >= 0
                and text[start - k - 1] in "rRbBuUfF"
                and (
                    start - k - 2 < 0
                    or not (text[start - k - 2].isalnum() or text[start - k - 2] == "_")
                )
            ):
                k += 1
            prefix = text[start - k : start] if k else ""
        raw = "r" in prefix.lower()
        interpolated = "f" in prefix.lower()
        allow_newline = tok == "`"
        if tok == "`":
            interpolated = interpolated or lang == "javascript"
            raw = lang == "go"
        body_start = start + 1
        close = _find_string_end(
            text, body_start, tok, False, raw, allow_newline=allow_newline
        )
        literals.append(
            Literal(
                text[body_start:close],
                body_start,
                close,
                *position(body_start),
                tok,
                lang,
                interpolated,
            )
        )
        if not interpolated:
            blank(body_start, close)
        i = close + 1

    if lang in {"python", "c"}:
        literals = _merge_adjacent(text, literals)
    return ScanResult("".join(out), literals)


def _find_string_end(
    text: str,
    start: int,
    quote: str,
    triple: bool,
    raw: bool,
    allow_newline: bool = False,
) -> int:
    n = len(text)
    i = start
    delim = quote * 3 if triple else quote
    while i < n:
        if text.startswith(delim, i):
            return i
        if text[i] == "\\" and not raw:
            i += 2
            continue
        if text[i] == "\n" and not triple and not allow_newline:
            return i  # unterminated single-line string: stop at newline
        i += 1
    return n




def _merge_adjacent(text: str, literals: list[Literal]) -> list[Literal]:
    """Merge Python/C implicit string concatenation into one literal.

    Long keys and addresses are frequently split across lines inside
    parentheses; without this pass a viewing key would be seen as several
    truncated fragments (and reported as malformed).
    """
    merged: list[Literal] = []
    for lit in literals:
        if merged:
            prev = merged[-1]
            gap = text[prev.end : lit.start]
            if prev.quote == lit.quote and re.fullmatch(r"[\"'\s]{1,8}", gap or ""):
                merged[-1] = Literal(
                    value=prev.value + lit.value,
                    start=prev.start,
                    end=lit.end,
                    line=prev.line,
                    col=prev.col,
                    quote=prev.quote,
                    language=prev.language,
                    interpolated=prev.interpolated or lit.interpolated,
                )
                continue
        merged.append(lit)
    return merged


# ---------------------------------------------------------------------------
# SourceFile
# ---------------------------------------------------------------------------


@dataclass
class SourceFile:
    path: Path
    rel: str
    lang: str
    text: str
    masked: str
    literals: list[Literal]
    line_starts: list[int] = field(default_factory=list)
    _ignore: dict[int, set[str] | None] = field(default_factory=dict)
    _disabled: set[str] | None = None  # None = nothing disabled

    def __post_init__(self) -> None:
        starts = [0]
        for idx, ch in enumerate(self.text):
            if ch == "\n":
                starts.append(idx + 1)
        self.line_starts = starts
        self._parse_directives()

    # -- positions ---------------------------------------------------------
    def line_col(self, offset: int) -> tuple[int, int]:
        offset = max(0, min(offset, len(self.text)))
        lo, hi = 0, len(self.line_starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self.line_starts[mid] <= offset:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1, offset - self.line_starts[lo] + 1

    def line_text(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.line_starts):
            start = self.line_starts[lineno - 1]
            end = self.text.find("\n", start)
            return self.text[start : end if end != -1 else len(self.text)]
        return ""

    def masked_line(self, lineno: int) -> str:
        text = self.line_text(lineno)
        if not text:
            return ""
        start = self.line_starts[lineno - 1]
        return self.masked[start : start + len(text)]

    def context(self, lineno: int, before: int = 2, after: int = 1) -> str:
        """Masked code around a line, whitespace-normalised."""
        parts = []
        for n in range(max(1, lineno - before), min(len(self.line_starts), lineno + after) + 1):
            parts.append(self.masked_line(n))
        return re.sub(r"\s+", " ", " ".join(parts)).strip()

    # -- suppression ---------------------------------------------------------
    def _parse_directives(self) -> None:
        for idx, raw in enumerate(self.text.splitlines(), start=1):
            for match in _DIRECTIVE_RE.finditer(raw):
                kind = match.group(1).lower()
                rules = match.group(2)
                rule_set = (
                    {r.strip().upper() for r in rules.split(",") if r.strip()}
                    if rules
                    else None
                )
                if kind == "disable-file":
                    if rule_set is None:
                        self._disabled = {"*"}
                    else:
                        self._disabled = (self._disabled or set()) | rule_set
                else:  # ignore
                    for target in (idx, idx + 1):
                        existing = self._ignore.get(target)
                        if rule_set is None:
                            self._ignore[target] = None
                        elif existing is None and target in self._ignore:
                            continue
                        else:
                            self._ignore[target] = (existing or set()) | rule_set

    def suppressed(self, rule_id: str, lineno: int) -> bool:
        if self._disabled is not None:
            if "*" in self._disabled or rule_id.upper() in self._disabled:
                return True
        if lineno in self._ignore:
            entry = self._ignore[lineno]
            if entry is None or rule_id.upper() in entry:
                return True
        return False


def load_file(path: Path, root: Path) -> SourceFile | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in data[:4096]:
        return None
    text = data.decode("utf-8", errors="replace")
    lang = EXTENSIONS.get(path.suffix.lower(), "text")
    result = scan(text, lang)
    rel = os.path.relpath(path, root) if root else str(path)
    return SourceFile(path=path, rel=Path(rel).as_posix(), lang=lang, text=text, masked=result.masked, literals=result.literals)


def discover(
    paths: Iterable[str | Path],
    exclude_globs: Iterable[str] = (),
    include_docs: bool = False,
) -> list[Path]:
    globs = list(DEFAULT_EXCLUDE_GLOBS) + list(exclude_globs)
    found: list[Path] = []
    for entry in paths:
        p = Path(entry)
        if p.is_file():
            if p.suffix.lower() in EXTENSIONS and not _excluded(p, globs):
                found.append(p)
            continue
        for dirpath, dirnames, filenames in os.walk(p):
            dirnames[:] = sorted(
                d for d in dirnames if d not in DEFAULT_SKIP_DIRS and not d.startswith(".")
            )
            for name in sorted(filenames):
                f = Path(dirpath) / name
                if f.suffix.lower() not in EXTENSIONS:
                    continue
                if not include_docs and f.suffix.lower() in {".md", ".mdx", ".rst", ".txt"}:
                    continue
                if _excluded(f, globs):
                    continue
                try:
                    if f.stat().st_size > MAX_FILE_BYTES:
                        continue
                except OSError:
                    continue
                found.append(f)
    # de-duplicate while preserving order
    seen: set[str] = set()
    unique = []
    for f in found:
        key = str(f.resolve())
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


def _excluded(path: Path, globs: list[str]) -> bool:
    name = path.name
    posix = path.as_posix()
    return any(fnmatch.fnmatch(name, g) or fnmatch.fnmatch(posix, g) for g in globs)
