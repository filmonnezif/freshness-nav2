#!/usr/bin/env bash
# Build the container and run a fresh ROS campaign into evidence/<name>.
#
#   scripts/run_campaign.sh <name> [probe.py options...]
#
# Examples:
#   scripts/run_campaign.sh reproduction --repeats 5
#   scripts/run_campaign.sh availability-rerun --repeats 20 \
#       --cases healthy benign_stamp_lag repeated_command --seed 20261013
#
# Uses podman if available, otherwise docker. The output folder must not exist.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
NAME="${1:?usage: scripts/run_campaign.sh <name> [probe options]}"
shift
IMAGE=freshness-nav2:jazzy
ENGINE=$(command -v podman || command -v docker || true)
[[ -n "$ENGINE" ]] || { echo 'Install podman or docker.' >&2; exit 1; }
[[ ! -e "$ROOT/evidence/$NAME" ]] || { echo "evidence/$NAME already exists." >&2; exit 1; }

"$ENGINE" build -t "$IMAGE" -f "$ROOT/docker/Containerfile" "$ROOT/docker"

USERNS=()
[[ "$(basename "$ENGINE")" == podman ]] && USERNS=(--userns=keep-id)
"$ENGINE" run --rm "${USERNS[@]}" --shm-size=512m \
  --volume "$ROOT:/workspace:rw" \
  --env ROS_DOMAIN_ID=143 --env ROS_LOG_DIR=/tmp/ros-logs \
  "$IMAGE" /ros_entrypoint.sh python3 /workspace/research/freshness_contracts/probe.py \
  --out "/workspace/evidence/$NAME" "$@"

echo "Campaign written to evidence/$NAME. Audit it with:"
echo "  python3 research/freshness_contracts/build_assets.py --evidence evidence/$NAME --audit-only [--expected-repeats N] [--cases ...]"
