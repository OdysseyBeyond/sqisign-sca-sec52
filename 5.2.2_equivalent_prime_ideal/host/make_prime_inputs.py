#!/usr/bin/env python3
"""Build tvla_inputs_prime.bin (input of equiv_prime_target.c) from tvla_inputs_equiv.bin:
each device record keeps the class byte and only the 6th serialized ibz of the
EquivalentCoprimeIdeal record, i.e. n = nrd(J_t) (same container format, same order).
  python make_prime_inputs.py ../data/tvla_inputs_equiv.bin ../data/tvla_inputs_prime.bin"""
import struct, sys
src = sys.argv[1] if len(sys.argv) > 1 else "tvla_inputs_equiv.bin"
dst = sys.argv[2] if len(sys.argv) > 2 else "tvla_inputs_prime.bin"
f = open(src, "rb"); magic, N = struct.unpack("<II", f.read(8)); rm, = struct.unpack("<H", f.read(2))
o = open(dst, "wb"); o.write(struct.pack("<II", magic, N)); o.write(struct.pack("<H", rm))
for _ in range(N):
    c = f.read(1); rl, = struct.unpack("<H", f.read(2)); rec = f.read(rl); p = 0; fields = []
    while p < len(rec):
        ln = rec[p + 1] | (rec[p + 2] << 8); fields.append(rec[p:p + 3 + ln]); p += 3 + ln
    n = fields[5]; o.write(c); o.write(struct.pack("<H", len(n))); o.write(n)
o.close(); print("wrote", dst, N, "records")
