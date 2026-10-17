# CI integration

ShieldLint is designed to be the cheapest job in your pipeline: Python, no
network, no services, deterministic output.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | no findings at or above `--fail-on` |
| `1` | at least one finding at or above the threshold |
| `2` | usage error (missing path, bad config, unreadable file) |

`--fail-on` accepts `error` (default), `warning`, `note` or `never`. A common
rollout is:

1. start with `--fail-on never` and read the report,
2. fix the `error` findings,
3. flip to the default and make the job blocking,
4. tighten to `--fail-on warning` once the tree is clean.

## GitHub Actions — annotations

```yaml
name: privacy
on: [pull_request]

jobs:
  shieldlint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pipx install .
      - run: shieldlint check src --format github
```

Findings appear inline on the pull request, one per file/line, with the rule id
as the annotation title.

## GitHub Actions — SARIF / code scanning

```yaml
name: privacy
on:
  push:
    branches: [main]
  pull_request:
  schedule:
    - cron: "0 4 * * 1"          # weekly drift check

permissions:
  contents: read
  security-events: write

jobs:
  shieldlint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pipx install .
      - run: shieldlint check . --format sarif -o shieldlint.sarif
      - uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: shieldlint.sarif
          category: shieldlint
```

Use `if: always()` so the SARIF is uploaded even when the lint step fails; the
job still fails, but the findings land in the Security tab.

## Composite action

This repository ships [`action.yml`](../action.yml):

```yaml
- uses: owner/shieldlint@v0.1.0        # the action lives at the repository root
  with:
    paths: src
    fail-on: warning
    format: github
```

Or from a checkout of this repository:

```yaml
- uses: ./
  with:
    paths: src
```

## GitLab CI

```yaml
shieldlint:
  image: python:3.12-slim
  script:
    - pip install .
    - shieldlint check src --format json -o shieldlint.json || true
    - python - <<'PY'
import json, sys
report = json.load(open("shieldlint.json"))
for f in report["findings"]:
    print(f'{f["path"]}:{f["line"]}: {f["rule"]} {f["message"]}')
sys.exit(1 if report["summary"]["errors"] else 0)
PY
  artifacts:
    when: always
    paths: [shieldlint.json]
```

## pre-commit

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: shieldlint
        name: shieldlint
        entry: shieldlint check
        language: system
        types: [file]
        pass_filenames: true
        args: ["--fail-on", "error"]
```

`check` accepts explicit file paths, so pre-commit only lints staged files.

## Config in CI

Commit a `shieldlint.toml` so local runs and CI agree:

```toml
[shieldlint]
fail_on = "error"
exclude = ["tests/fixtures/**", "vendor/**", "**/generated/**"]
```

Inline suppression is preferred for one-off exceptions; the config is for
structural exclusions (fixtures, generated code, vendored SDKs).

## Baseline / incremental adoption

There is no baseline file yet (see the roadmap). Until then:

* exclude legacy directories in the config and expand coverage over time;
* or run with `--fail-on never` in a non-blocking job and alert on the error
  count instead of failing the build.

## Docker

```dockerfile
FROM python:3.12-slim
WORKDIR /src
RUN pip install --no-cache-dir shieldlint
ENTRYPOINT ["shieldlint"]
```

```bash
docker run --rm -v "$PWD:/src" shieldlint check src --no-color
```
