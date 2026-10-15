#!/usr/bin/env bash
# Build the host-side (x86, RADIX_32) generator of the equivalent-prime-ideal
# experiment against the patched SQIsign subset in ../../common/firmware/sqisign
# (run ../../common/firmware/get_sqisign.sh first). Output: ./bin/equiv_host
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; FW="$HERE/../../common/firmware"; H1="$HERE/../../5.2.1_intersection/host"
[ -d "$FW/sqisign/src" ] || { echo "run $FW/get_sqisign.sh first" >&2; exit 1; }
CF="-O2 -w -std=gnu11 -I $FW/sqisign/inc -I $FW -I $HERE -DSQISIGN_BUILD_TYPE_REF -DSQISIGN_GF_IMPL_REF -DSQISIGN_VARIANT=p324_3 -DNDEBUG -DRADIX_32"
mkdir -p "$HERE/bin"
# Intersect(a_fixed, b, split_fixed) -> EquivalentCoprimeIdeal; dumps the exact input of
# quat_ideal_create_O0_inert_odd (device records) and the (a,b,c,d), s, t, x, y, n labels.
gcc $CF -DTVLA_DUMP_EQUIV -DSQISIGN_SINGLE_THREADED "$HERE/equiv_host.c" "$FW/host_rng.c" "$FW"/sqisign/src/*.c -o "$HERE/bin/equiv_host"
echo "built: $(ls "$HERE/bin")"
