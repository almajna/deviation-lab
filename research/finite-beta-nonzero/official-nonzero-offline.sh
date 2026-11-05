#!/usr/bin/env bash
set -euo pipefail
# Isolated GitHub runner, after dropping network and all capabilities.
test "$(id -u)" -ne 0
awk '/^CapEff:/ { if ($2 !~ /^0+$/) exit 1; seen=1 } END { if (!seen) exit 1 }' /proc/self/status
test -z "$(ip -4 route show)"
test -z "$(ip -6 route show default)"
cd "$TASK_WORKSPACE/research/finite-beta-nonzero"
python official_nonzero_check.py \
  --source "$TASK_TEMP/published-source/strategic_ttc/core/game_dynamics.py" \
  --input "$TASK_TEMP/finite-beta-input.json" \
  --canonical "$TASK_TEMP/finite-beta-canonical.json" \
  --output "$TASK_TEMP/official-nonzero-results.json"
