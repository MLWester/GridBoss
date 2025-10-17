#!/usr/bin/env bash

set -euo pipefail

SOURCE_DIR="${1:-.}"
IMAGE="zricethezav/gitleaks:latest"

if command -v gitleaks >/dev/null 2>&1; then
  gitleaks detect --source "$SOURCE_DIR" --no-banner --redact
  exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "gitleaks is not installed and Docker is unavailable. Install one of them to scan for secrets." >&2
  exit 1
fi

docker run --rm \
  -v "${PWD}:/repo" \
  -w /repo \
  "$IMAGE" detect \
  --source "$SOURCE_DIR" \
  --no-banner \
  --redact
