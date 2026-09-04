#!/usr/bin/env bash
# Sourced only from the isolated WORKFLOW checkout, never the deployment clone.

require_release_host() {
  [[ "$(hostname -f)" == "$EXPECTED_HOST" ]] || {
    echo "Expected runner host $EXPECTED_HOST, found $(hostname -f)." >&2; exit 1;
  }
}

validate_release_clone() {
  require_release_host
  if [[ ! -d "$DEPLOY_DIR/.git" || -L "$DEPLOY_DIR" || -L "$DEPLOY_DIR/.git" ||
        "$(realpath -e "$DEPLOY_DIR")" != "$DEPLOY_DIR" ]]; then
    echo "Deployment clone must be a canonical directory with a real .git directory." >&2
    exit 1
  fi
  git -C "$DEPLOY_DIR" config --local --name-only --list |
    awk 'BEGIN {IGNORECASE=1}
         /^(core\.(repositoryformatversion|filemode|bare|logallrefupdates|ignorecase|precomposeunicode)|remote\.origin\.(url|fetch)|branch\..+\.(remote|merge))$/ {next}
         {print "Unsupported local Git configuration: " $0 > "/dev/stderr"; invalid=1}
         END {exit invalid}'
  local origin_url
  origin_url=$(git -C "$DEPLOY_DIR" remote get-url origin)
  [[ "$origin_url" == "https://github.com/cardano-foundation/cardano-rosetta-java.git" ]] || {
    echo "Unexpected deployment clone origin: $origin_url" >&2; exit 1;
  }
}

# Inputs are validated centrally; mutable clone identity is checked at each boundary.
# fetch: initial checkout; checkout: reset at a job boundary; assert: no mutation.
# The caller must use set -euo pipefail and must not call this in a conditional.
release_source() {
  local mode=$1 resolved_sha
  validate_release_clone
  if [[ "$mode" == fetch ]]; then
    git -C "$DEPLOY_DIR" fetch --tags --prune origin
  fi
  resolved_sha=$(git -C "$DEPLOY_DIR" rev-parse "refs/tags/${PRERELEASE_TAG%-pre-release}^{commit}")
  [[ "$resolved_sha" == "$SOURCE_SHA" ]] || {
    echo "Release source mismatch: expected $SOURCE_SHA, found $resolved_sha." >&2; exit 1;
  }
  case "$mode" in
    fetch|checkout)
      git -C "$DEPLOY_DIR" checkout --detach --force "$SOURCE_SHA"
      git -C "$DEPLOY_DIR" clean -ffdx
      ;;
    assert) [[ "$(git -C "$DEPLOY_DIR" rev-parse HEAD)" == "$SOURCE_SHA" ]] ;;
    *) echo "Unknown release source operation: $mode" >&2; exit 1 ;;
  esac
}

require_protected_file() {
  local file=$1 mode
  test -f "$file"
  mode=$(stat -c '%a' "$file")
  [[ "$mode" == 600 || "$mode" == 400 ]] || {
    echo "$file must have mode 600 or 400, found $mode." >&2; exit 1;
  }
}

require_single_value() {
  local file=$1 key=$2 count
  count=$(awk -F= -v key="$key" \
    '$1 == key && length(substr($0, index($0, "=") + 1)) > 0 {count++} END {print count + 0}' "$file")
  [[ "$count" == 1 ]] || {
    echo "Expected exactly one non-empty $key in $file, found $count." >&2; exit 1;
  }
}
