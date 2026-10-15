#!/usr/bin/env bash
# Build the host-side (x86, RADIX_32) tools of the intersection experiment
# against the patched SQIsign subset in ../../common/firmware/sqisign
# (run ../../common/firmware/get_sqisign.sh first). Output binaries: ./bin/
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; FW="$HERE/../../common/firmware"
[ -d "$FW/sqisign/src" ] || { echo "run $FW/get_sqisign.sh first" >&2; exit 1; }
CF="-O2 -w -std=gnu11 -I $FW/sqisign/inc -I $FW -I $HERE -DSQISIGN_BUILD_TYPE_REF -DSQISIGN_GF_IMPL_REF -DSQISIGN_VARIANT=p324_3 -DNDEBUG -DRADIX_32"
mkdir -p "$HERE/bin"
# input generator: fixed (a, split) + 21,000 secret ideals b (fixed/random classes)
gcc $CF "$HERE/tvla_gen_rk.c"   "$FW/host_rng.c" "$FW"/sqisign/src/*.c -o "$HERE/bin/tvla_gen_rk"
# W1 operands of the Gaussian multiply + label b.x byte 0  (needs the dump hook)
gcc $CF -DTVLA_DUMP_GAUSS "$HERE/gauss_host.c" "$FW/host_rng.c" "$FW"/sqisign/src/*.c -o "$HERE/bin/gauss_host"
# W2 / W3 labels (x_pre, t, X2, Y2 and the materialized x, y)
gcc $CF -DTVLA_DUMP_OUT -DTVLA_DUMP_STORE "$HERE/outlabel_host.c" "$FW/host_rng.c" "$FW"/sqisign/src/*.c -o "$HERE/bin/outlabel_host"
# Gaussian-multiply emulator (CRC of the product per record; build at RADIX_32 and RADIX_16 to compare)
gcc $CF "$HERE/gauss_verify.c" "$FW/host_rng.c" "$FW"/sqisign/src/*.c -o "$HERE/bin/gauss_verify32"
gcc ${CF/-DRADIX_32/-DRADIX_16} "$HERE/gauss_verify.c" "$FW/host_rng.c" "$FW"/sqisign/src/*.c -o "$HERE/bin/gauss_verify16"
echo "built: $(ls "$HERE/bin")"
