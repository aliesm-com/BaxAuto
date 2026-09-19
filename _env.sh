# Shared working directory for repository shell scripts (project root).
if [[ -z "${BAXAUTO_REPO_ROOT:-}" ]]; then
  BAXAUTO_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  cd "$BAXAUTO_REPO_ROOT" || exit 1
fi
