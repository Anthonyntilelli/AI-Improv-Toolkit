#!/usr/bin/env bash
set -euo pipefail

SHOW_DIR="/dev/show"
# Adjust majors/minors as needed
BIG_RED_MAJOR=${BIG_RED_MAJOR:-240}
BIG_RED_MINOR=${BIG_RED_MINOR:-0}
ACTOR_MAJOR=${ACTOR_MAJOR:-240}
ACTOR_MINOR=${ACTOR_MINOR:-1}

sudo mkdir -p "${SHOW_DIR}"

sudo mknod -m 660 "${SHOW_DIR}/big-red" c "${BIG_RED_MAJOR}" "${BIG_RED_MINOR}"
sudo mknod -m 660 "${SHOW_DIR}/actor"   c "${ACTOR_MAJOR}"   "${ACTOR_MINOR}"

# Change ownership to vscode user to allow non-root access
sudo chown vscode:vscode "${SHOW_DIR}/big-red" "${SHOW_DIR}/actor"
echo "Created ${SHOW_DIR}/big-red and ${SHOW_DIR}/actor (char devices)."
