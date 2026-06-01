#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

PYTHON_BIN="python3"
SKIP_UPDATE_MATRIX="false"
VERBOSE="false"

# Keep defaults as repo-absolute for validation/display.
VARS_FILE="${REPO_ROOT}/molecule/shared/vars.yml"
TEMPLATE_FILE="${REPO_ROOT}/templates/meta_main.yml.j2"
OUTPUT_FILE="${REPO_ROOT}/meta/main.yml"

log() {
  printf '%s\n' "$*"
}

err() {
  printf 'ERROR: %s\n' "$*" >&2
}

usage() {
  cat <<'EOF'
Usage:
  ./scripts/update_release_metadata.sh [options]

Options:
  --python <path>           Python interpreter to use (default: python3)
  --skip-update-matrix      Do not refresh molecule/shared/vars.yml before rendering
  --vars-file <path>        Shared vars file to use (default: molecule/shared/vars.yml)
  --template <path>         Metadata template to use (default: templates/meta_main.yml.j2)
  --output <path>           Output file to write (default: meta/main.yml)
  --verbose                 Enable shell tracing
  -h, --help                Show this help text

Behavior:
  1) Optionally refreshes molecule/shared/vars.yml via scripts/update_matrix.py
  2) Syntax-checks generator scripts before executing them
  3) Renders Molecule inventories from shared vars
  4) Renders meta/main.yml from templates/meta_main.yml.j2
EOF
}

# Convert an input path to repo-absolute, unless it is already absolute.
to_abs_path() {
  local path="$1"
  if [[ "$path" = /* ]]; then
    printf '%s\n' "$path"
  else
    printf '%s\n' "${REPO_ROOT}/${path}"
  fi
}

# Convert an absolute repo path to a repo-relative path for scripts that
# internally resolve from ROOT / args.path.
to_repo_rel_path() {
  local path="$1"
  path="$(to_abs_path "$path")"

  case "$path" in
    "${REPO_ROOT}/"*)
      printf '%s\n' "${path#${REPO_ROOT}/}"
      ;;
    *)
      err "Path must be inside repository root: $path"
      exit 9
      ;;
  esac
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --python)
      PYTHON_BIN="$2"
      shift 2
      ;;
    --skip-update-matrix)
      SKIP_UPDATE_MATRIX="true"
      shift
      ;;
    --vars-file)
      VARS_FILE="$(to_abs_path "$2")"
      shift 2
      ;;
    --template)
      TEMPLATE_FILE="$(to_abs_path "$2")"
      shift 2
      ;;
    --output)
      OUTPUT_FILE="$(to_abs_path "$2")"
      shift 2
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

command -v "$PYTHON_BIN" >/dev/null 2>&1 || {
  err "Python interpreter not found: $PYTHON_BIN"
  exit 3
}

UPDATE_MATRIX_SCRIPT="${REPO_ROOT}/scripts/update_matrix.py"
RENDER_INVENTORY_SCRIPT="${REPO_ROOT}/scripts/render_inventory.py"
RENDER_META_SCRIPT="${REPO_ROOT}/scripts/render_meta_main.py"

# Validate generator script presence and syntax.
GENERATOR_SCRIPTS=(
  "$RENDER_INVENTORY_SCRIPT"
  "$RENDER_META_SCRIPT"
)

if [[ "$SKIP_UPDATE_MATRIX" != "true" ]]; then
  GENERATOR_SCRIPTS+=("$UPDATE_MATRIX_SCRIPT")
fi

log '==> Syntax-checking generator scripts'
for script in "${GENERATOR_SCRIPTS[@]}"; do
  [[ -f "$script" ]] || {
    err "Required script not found: $script"
    exit 4
  }
  "$PYTHON_BIN" -m py_compile "$script"
done

if [[ "$SKIP_UPDATE_MATRIX" != "true" ]]; then
  log '==> Refreshing Molecule platform matrix'
  (cd "$REPO_ROOT" && "$PYTHON_BIN" "$UPDATE_MATRIX_SCRIPT")
else
  log '==> Skipping matrix refresh (requested)'
fi

[[ -f "$VARS_FILE" ]] || {
  err "Shared vars file not found: $VARS_FILE"
  exit 5
}

[[ -f "$TEMPLATE_FILE" ]] || {
  err "Template file not found: $TEMPLATE_FILE"
  exit 6
}

mkdir -p "$(dirname -- "$OUTPUT_FILE")"

# render_meta_main.py resolves paths as ROOT / args.path, so pass repo-relative paths.
VARS_FILE_REL="$(to_repo_rel_path "$VARS_FILE")"
TEMPLATE_FILE_REL="$(to_repo_rel_path "$TEMPLATE_FILE")"
OUTPUT_FILE_REL="$(to_repo_rel_path "$OUTPUT_FILE")"

log '==> Rendering Molecule inventories from shared matrix'
(cd "$REPO_ROOT" && "$PYTHON_BIN" "$RENDER_INVENTORY_SCRIPT")

log '==> Rendering meta/main.yml from shared matrix'
(
  cd "$REPO_ROOT" && "$PYTHON_BIN" "$RENDER_META_SCRIPT" \
    --vars-file "$VARS_FILE_REL" \
    --template "$TEMPLATE_FILE_REL" \
    --output "$OUTPUT_FILE_REL"
)

log '==> Done'
log "Shared vars : $VARS_FILE"
log "Template    : $TEMPLATE_FILE"
log "Output      : $OUTPUT_FILE"
log ''
log 'Suggested next steps:'
log '  1) git diff -- meta/main.yml molecule/'
log '  2) yamllint .'
log '  3) ansible-lint .'
log '  4) molecule test -s default'
