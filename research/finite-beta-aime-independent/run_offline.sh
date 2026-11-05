#!/usr/bin/env bash
set -euo pipefail
test "$(id -u)" -ne 0
awk '/^CapEff:/ { if ($2 !~ /^0+$/) exit 1; seen=1 } END { if (!seen) exit 1 }' /proc/self/status
test -z "$(ip -4 route show)"
test -z "$(ip -6 route show default)"
cd "$TASK_WORKSPACE"
python3 research/finite-beta-aime-independent/prepare.py "$TASK_ARCHIVE" "$TASK_RESULT_DIR/curves.txt"
g++ --version > "$TASK_RESULT_DIR/compiler-version.txt"
g++ -O3 -std=c++17 research/finite-beta-aime-independent/exhaustive.cpp -o "$TASK_RESULT_DIR/exhaustive"
"$TASK_RESULT_DIR/exhaustive" "$TASK_RESULT_DIR/curves.txt" | tee "$TASK_RESULT_DIR/exhaustive-output.txt"
python3 research/finite-beta-aime-independent/check.py "$TASK_ARCHIVE" "$TASK_RESULT_DIR/exhaustive-output.txt"
sha256sum research/finite-beta-aime-independent/* "$TASK_RESULT_DIR/curves.txt" "$TASK_RESULT_DIR/exhaustive-output.txt" > "$TASK_RESULT_DIR/verification-sha256.txt"
