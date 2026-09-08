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
  [[ "$(git -C "$DEPLOY_DIR" rev-parse --show-toplevel)" == "$DEPLOY_DIR" ]] || {
    echo "Git worktree points outside the deployment clone." >&2; exit 1;
  }
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
