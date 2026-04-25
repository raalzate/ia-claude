#!/usr/bin/env bash
# install-hooks.sh — copy the IIKit pre-commit hook into .git/hooks/.
#
# Constitution Integrity Section: "Pre-Commit Hook Enforcement
# (NON-NEGOTIABLE)". Every contributor MUST run this once after cloning so
# assertion-integrity verification fires before each commit. The hook is
# the local mirror of the server-side gate in
# .github/workflows/assertion-integrity.yml.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$REPO_ROOT" ]]; then
    echo "error: not inside a git checkout" >&2
    exit 2
fi

cd "$REPO_ROOT"

SOURCE=".tessl/tiles/tessl-labs/intent-integrity-kit/skills/iikit-core/scripts/bash/pre-commit-hook.sh"
TARGET=".git/hooks/pre-commit"

if [[ ! -f "$SOURCE" ]]; then
    echo "error: hook source not found at $SOURCE" >&2
    echo "run: tessl install   (re-fetches the IIKit tile)" >&2
    exit 3
fi

mkdir -p .git/hooks
cp "$SOURCE" "$TARGET"
chmod +x "$TARGET"

# Sanity-check the hook is the IIKit version, not a stale stub.
if ! grep -q "IIKIT-PRE-COMMIT" "$TARGET"; then
    echo "error: installed hook does not look like the IIKit hook" >&2
    exit 4
fi

echo "[ok] pre-commit hook installed at $TARGET"
echo "     verify with: ls -l $TARGET"
echo "     bypass attempts with --no-verify will be rejected by CI."
