#!/usr/bin/env bash
# get_sqisign.sh - fetch the SQIsign reference sources this harness builds on
# and apply the instrumentation patches.
#
#   ./get_sqisign.sh [--with-radix16-mp] [--src <existing the-sqisign checkout>]
#
# Result: ./sqisign/{src,inc} containing the 18 C files + headers of the
# quaternion / multiprecision layer of SQIsign (github.com/SQIsign/the-sqisign,
# branch nist-v3, commit 6d01770, variant p324_3) with
#   0001  trigger / label-dump hooks in ideal.c            (always)
#   0002  RADIX_8 / RADIX_16 build support (headers, constants) (always)
#   0003  radix-portable mp_div_unsigned / ibz_invmod       (only with --with-radix16-mp;
#         needed to run the *full* Intersect at RADIX_16 on the host, see README)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
COMMIT=6d017708db403bf83977fa70770fc4f7f9e9ff21
WITH_R16MP=0; SRC=""
while [ $# -gt 0 ]; do
  case "$1" in
    --with-radix16-mp) WITH_R16MP=1 ;;
    --src) SRC="$2"; shift ;;
    *) echo "unknown option $1" >&2; exit 2 ;;
  esac; shift
done
if [ -z "$SRC" ]; then
  SRC="$HERE/.the-sqisign"
  if [ ! -d "$SRC/.git" ]; then
    git clone --filter=blob:none https://github.com/SQIsign/the-sqisign.git "$SRC"
  fi
  git -C "$SRC" checkout -q "$COMMIT"
fi
rm -rf "$HERE/sqisign"; mkdir -p "$HERE/sqisign/src" "$HERE/sqisign/inc"
while read -r loc up; do
  [ -z "$loc" ] && continue
  cp "$SRC/$up" "$HERE/sqisign/$loc"
done < "$HERE/sqisign_files.lst"
cd "$HERE/sqisign"
patch -p1 --no-backup-if-mismatch -s < "$HERE/patches/0001-tvla-trigger-and-dump-hooks.patch"
patch -p1 --no-backup-if-mismatch -s < "$HERE/patches/0002-radix8-radix16-build-support.patch"
if [ "$WITH_R16MP" = 1 ]; then
  patch -p1 --no-backup-if-mismatch -s < "$HERE/patches/0003-radix16-portable-division-and-invmod.patch"
fi
echo "sqisign/ prepared from the-sqisign@${COMMIT:0:7} (radix16-mp patch: $WITH_R16MP)"
