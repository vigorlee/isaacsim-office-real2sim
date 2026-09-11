#!/usr/bin/env bash
set -euo pipefail
SCENE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export OMNI_KIT_ACCEPT_EULA="${OMNI_KIT_ACCEPT_EULA:-YES}"
PYTHON_BIN="${ISAACSIM_PYTHON:-python3}"
exec "$PYTHON_BIN" "$SCENE_DIR/run_office.py" "$@"
