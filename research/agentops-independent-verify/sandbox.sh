#!/usr/bin/env bash
set -euo pipefail
test "$(id -u)" -ne 0
test -z "$(ip -4 route show)"
test -z "$(ip -6 route show default)"
awk '/^CapEff:/ {if ($2 !~ /^0+$/) exit 1; n++} END {if (n != 1) exit 1}' /proc/self/status
python3 /tmp/aob-independent-input/verify.py /tmp/aob-independent-input/pilot.tar.gz /tmp/aob-independent-output/results.json
