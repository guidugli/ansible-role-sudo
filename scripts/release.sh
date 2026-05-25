#!/usr/bin/env bash
set -euo pipefail

# release.sh
#
# Purpose:
#   Prepare and publish a new tag-based release for the Ansible role.
#
# What it does:
#   1) Validates working tree is clean (unless --allow-dirty is used)
#   2) Refreshes generated metadata/inventories via scripts/update_release_metadata.sh
#   3) Runs Molecule default scenario
#   4) Stages generated changes
#   5) Commits release-prep changes (optional if nothing changed)
#   6) Creates an annotated Git tag
#   7) Pushes commit(s) and tag to origin
#
# Usage examples:
#   ./scripts/release.sh --version v1.1.0 --message "Reworked code and molecule tests"
#   ./scripts/release.sh --version v1.1.0 --message "Release v1.1.0" --dry-run
#   ./scripts/release.sh --version v1.1.0 --message "Release v1.1.0" --allow-dirty
#
# Notes:
#   - The GitHub release workflow is triggered by pushing the tag.
#   - Use semantic version tags like v1.2.3.
#   - Test tags should use a different prefix (example: test-v1.2.3) and should NOT use this script.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
UPDATE_SCRIPT="${SCRIPT_DIR}/update_release_metadata.sh"

VERSION=""
TAG_MESSAGE=""
COMMIT_MESSAGE=""
REMOTE="origin"
SCENARIO="default"
ALLOW_DIRTY="false"
SKIP_PUSH="false"
SKIP_COMMIT="false"
SKIP_TESTS="false"
DRY_RUN="false"
VERBOSE="false"

log() {
  printf '%s\n' "$*"
}

err() {
  printf 'ERROR: %s\n' "$*" >&2
}

usage() {
  sed -n '1,120p' "$0"
}

run_cmd() {
  if [[ "$DRY_RUN" == "true" ]]; then
    printf '[dry-run] %s\n' "$*"
  else
    eval "$@"
  fi
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    err "Required command not found: $1"
    exit 2
  }
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version)
      VERSION="$2"
      shift 2
      ;;
    --message)
      TAG_MESSAGE="$2"
      shift 2
      ;;
    --commit-message)
      COMMIT_MESSAGE="$2"
      shift 2
      ;;
    --remote)
      REMOTE="$2"
      shift 2
      ;;
    --scenario)
      SCENARIO="$2"
      shift 2
      ;;
    --allow-dirty)
      ALLOW_DIRTY="true"
      shift
      ;;
    --skip-push)
      SKIP_PUSH="true"
      shift
      ;;
    --skip-commit)
      SKIP_COMMIT="true"
      shift
      ;;
    --skip-tests)
      SKIP_TESTS="true"
      shift
      ;;
    --dry-run)
      DRY_RUN="true"
      shift
      ;;
    --verbose)
      VERBOSE="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      err "Unknown argument: $1"
      exit 2
      ;;
  esac
done

if [[ "$VERBOSE" == "true" ]]; then
  set -x
fi

require_cmd git
require_cmd bash

if [[ -z "$VERSION" ]]; then
  err "--version is required (example: v1.1.0)"
  exit 2
fi

if [[ -z "$TAG_MESSAGE" ]]; then
  TAG_MESSAGE="Release ${VERSION}"
fi

if [[ -z "$COMMIT_MESSAGE" ]]; then
  COMMIT_MESSAGE="Prepare release ${VERSION}"
fi

if [[ ! "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  err "Version must match vX.Y.Z (got: $VERSION)"
  exit 2
fi

cd "$REPO_ROOT"

if [[ ! -f "$UPDATE_SCRIPT" ]]; then
  err "Missing update script: $UPDATE_SCRIPT"
  exit 3
fi

# Refresh index and check worktree cleanliness.
git update-index -q --refresh || true

if [[ "$ALLOW_DIRTY" != "true" ]]; then
  if ! git diff --quiet || ! git diff --cached --quiet; then
    err "Working tree is not clean. Commit/stash your changes first or use --allow-dirty." 
    git status --short
    exit 4
  fi
fi

if git rev-parse "$VERSION" >/dev/null 2>&1; then
  err "Tag already exists locally: $VERSION"
  exit 5
fi

if git ls-remote --tags "$REMOTE" "refs/tags/$VERSION" | grep -q "$VERSION"; then
  err "Tag already exists on remote '$REMOTE': $VERSION"
  exit 6
fi

log "==> Refreshing generated metadata/inventories"
run_cmd '"$UPDATE_SCRIPT"'

if [[ "$SKIP_TESTS" != "true" ]]; then
  require_cmd molecule
  log "==> Running Molecule scenario: $SCENARIO"
  run_cmd "molecule test -s '$SCENARIO'"
else
  log "==> Skipping tests (requested)"
fi

log "==> Staging generated release artifacts"
# Stage all changes produced by the metadata refresh. If nothing changed, that's fine.
run_cmd "git add meta/main.yml molecule/ templates/ scripts/ README.md .github/workflows/ 2>/dev/null || git add -A"

changed="false"
if ! git diff --cached --quiet; then
  changed="true"
fi

if [[ "$changed" == "true" && "$SKIP_COMMIT" != "true" ]]; then
  log "==> Creating release-prep commit"
  run_cmd "git commit -m '$COMMIT_MESSAGE'"
else
  if [[ "$changed" == "true" && "$SKIP_COMMIT" == "true" ]]; then
    log "==> Changes staged but commit skipped (requested)"
  else
    log "==> No staged changes to commit"
  fi
fi

log "==> Creating annotated tag: $VERSION"
run_cmd "git tag -a '$VERSION' -m '$TAG_MESSAGE'"

if [[ "$SKIP_PUSH" != "true" ]]; then
  # Push current branch first, then push tag.
  current_branch="$(git rev-parse --abbrev-ref HEAD)"
  log "==> Pushing branch '$current_branch' to '$REMOTE'"
  run_cmd "git push '$REMOTE' '$current_branch'"
  log "==> Pushing tag '$VERSION' to '$REMOTE'"
  run_cmd "git push '$REMOTE' '$VERSION'"
else
  log "==> Skipping push (requested)"
fi

log "==> Release preparation complete"
log "Version      : $VERSION"
log "Tag message  : $TAG_MESSAGE"
log "Commit msg   : $COMMIT_MESSAGE"
log "Remote       : $REMOTE"
if [[ "$SKIP_PUSH" == "true" ]]; then
  log "Next step    : push branch/tag manually when ready"
else
  log "Next step    : monitor GitHub Actions Release workflow and Galaxy import"
fi
