#!/usr/bin/env bash
set -euo pipefail
test "$(id -u)" -ne 0
test -z "$(ip -4 route show)"
test -z "$(ip -6 route show default)"
awk '/^CapEff:/ {if ($2 !~ /^0+$/) exit 1; seen=1} END {if (!seen) exit 1}' /proc/self/status
python3 /tmp/aob-input/audit.py /tmp/aob-input/pilot.tar.gz /tmp/aob-output/results.json /tmp/aob-output/members.json
