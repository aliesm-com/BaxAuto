# Shared working directory for repository shell scripts (project root).
# Sourced by start.sh — use `return`, never `exit` (exit would close a sourced shell).
if [[ -z "${BAXAUTO_REPO_ROOT:-}" ]]; then
  _baxauto_this="${BASH_SOURCE[0]:-$0}"
  BAXAUTO_REPO_ROOT="$(cd "$(dirname "$_baxauto_this")" && pwd)"
  unset _baxauto_this
  cd "$BAXAUTO_REPO_ROOT" || return 1
fi
