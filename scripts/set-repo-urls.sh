#!/usr/bin/env bash
# Point the repository at your GitHub account.
#
#   ./scripts/set-repo-urls.sh zksnarks_/shieldlint            # rewrite URLs
#   ./scripts/set-repo-urls.sh zksnarks_/shieldlint --remote   # also set origin
#
# Replaces the OWNER/REPO placeholder in pyproject.toml, shieldlint/output.py,
# README.md and this repository's docs, then commits the change.
set -euo pipefail

target="${1:-}"
if [[ -z "$target" || "$target" != */* ]]; then
  echo "usage: $0 OWNER/REPO [--remote]" >&2
  exit 2
fi

cd "$(dirname "$0")/.."

files=(
  pyproject.toml
  shieldlint/output.py
  README.md
  SUBMISSION.md
)

for f in "${files[@]}"; do
  [[ -f "$f" ]] || continue
  python3 - "$f" "$target" <<'PY'
import pathlib, sys
path, target = pathlib.Path(sys.argv[1]), sys.argv[2]
text = path.read_text(encoding="utf-8")
updated = text.replace("OWNER/REPO", target).replace("zksnarks_/shieldlint", target)
if updated != text:
    path.write_text(updated, encoding="utf-8")
    print(f"  updated {path}")
PY
done

git add -A
if ! git diff --cached --quiet; then
  git -c user.name="${GIT_AUTHOR_NAME:-ShieldLint}" \
      -c user.email="${GIT_AUTHOR_EMAIL:-shieldlint@users.noreply.github.com}" \
      commit -qm "chore: point repository URLs at ${target}"
  echo "committed URL update for ${target}"
else
  echo "no changes (already pointing at ${target})"
fi

if [[ "${2:-}" == "--remote" ]]; then
  if git remote get-url origin >/dev/null 2>&1; then
    git remote set-url origin "https://github.com/${target}.git"
  else
    git remote add origin "https://github.com/${target}.git"
  fi
  echo "origin -> https://github.com/${target}.git"
fi

echo
echo "next: gh repo create ${target##*/} --public --source=. --remote=origin --push"
