#!/usr/bin/env bash
set -euo pipefail

: "${DASHBOARD_STORAGE_HOST_PATH:?Set the private build-time workspace path}"
: "${DASHBOARD_PUBLICATION_HOST_ROOT:?Set the host publication release root}"
: "${DASHBOARD_PUBLICATION_RELEASE_ID:?Set a unique public release id}"

case "${DASHBOARD_PUBLICATION_RELEASE_ID}" in
  *[!A-Za-z0-9._-]* | "")
    echo "DASHBOARD_PUBLICATION_RELEASE_ID contains unsupported characters" >&2
    exit 2
    ;;
esac

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}/apps/dashboard"

# Build first. The short-lived generator receives the private workspace;
# the long-running dashboard service never does.
docker compose -f deploy/docker-compose.yml build dashboard
mkdir -p "${DASHBOARD_PUBLICATION_HOST_ROOT}"
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --mount "type=bind,src=${DASHBOARD_STORAGE_HOST_PATH},dst=/workspace,readonly" \
  --mount "type=bind,src=${DASHBOARD_PUBLICATION_HOST_ROOT},dst=/publication" \
  trading-dashboard:local \
  python -m dashboard_app.publication.release \
  --storage-root /workspace \
  --release-root /publication \
  --release-id "${DASHBOARD_PUBLICATION_RELEASE_ID}"

selected_release="$(tr -d '\r\n' < "${DASHBOARD_PUBLICATION_HOST_ROOT}/CURRENT")"
if [[ "${selected_release}" != "${DASHBOARD_PUBLICATION_RELEASE_ID}" ]]; then
  echo "Generated release was not atomically selected" >&2
  exit 3
fi

export DASHBOARD_PUBLICATION_HOST_PATH="${DASHBOARD_PUBLICATION_HOST_ROOT}/releases/${selected_release}"
docker compose -f deploy/docker-compose.yml up -d
