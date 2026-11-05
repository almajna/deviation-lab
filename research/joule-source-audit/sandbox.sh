#!/usr/bin/env bash
set -euo pipefail
test "$(id -u)" -ne 0
awk '/^Cap(Eff|Prm|Amb|Bnd):/ {if ($2 !~ /^0+$/) exit 1; n++} END {if (n != 4) exit 1}' /proc/self/status
test -z "$(ip -4 route show default)"
test -z "$(ip -6 route show default)"
exec /usr/bin/python3 /tmp/joule-source/check_source.py
