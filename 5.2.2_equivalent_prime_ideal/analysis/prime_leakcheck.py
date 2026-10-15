#!/usr/bin/env python3
"""Does n = nrd(J_t) leak during its primality test (ibz_probab_prime: sieve -> Montgomery setup -> MR base 2)?
Labels: n byte0..3 (limb0, used by the Horner sieve and as MODQ limb0 bits 0-27), 2n byte0 (two_n[0] low byte).
Works on traces_prime_small.npz (offset 0) or any prime capture passed as argv[1]."""
import numpy as np, sys
import os as _os
U = _os.environ.get("SQI_DATA", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "data")) + "/"
HW = np.array([bin(i).count("1") for i in range(256)], np.int32)
N4 = np.fromfile(U + "equiv_n_low4.bin", np.uint8).reshape(-1, 4).astype(np.int32)
L = {"n b0": N4[:, 0], "n b1": N4[:, 1], "n b2": N4[:, 2], "n b3": N4[:, 3], "2n b0": ((N4[:, 0] << 1) & 0xFF)}
npz = sys.argv[1] if len(sys.argv) > 1 else "traces_prime_small.npz"
if not _os.path.isabs(npz) and not _os.path.exists(npz): npz = U + npz
d = np.load(npz); X = d["traces"].astype(np.float64); cls = d["classes"].astype(int); k = d["kept_idx"]
r = cls == 1; Xr = X[r]; kr = k[r]; S = X.shape[1]; n = int(r.sum())
floor = np.sqrt(2 * np.log(S) / n); print("%s: traces %s random=%d floor |r|~%.3f" % (npz, X.shape, n, floor))

def corr(T, lab):
    a = lab - lab.mean(); t = T - T.mean(0)
    return (t.T @ a) / len(a) / (T.std(0) * a.std() + 1e-12)

def whv(Xz, y, hs=(3, 4, 5)):
    out = np.zeros(Xz.shape[1])
    for h in hs:
        m = HW[y] == h
        if m.sum() < 30: continue
        Xx, yy = Xz[m], y[m]; cs = np.unique(yy)
        mu = np.zeros((len(cs), Xz.shape[1])); w = np.zeros(len(cs)); noi = np.zeros(Xz.shape[1])
        for i, kk in enumerate(cs): g = Xx[yy == kk]; mu[i] = g.mean(0); w[i] = len(g)
        w = w / w.sum(); gm = (w[:, None] * mu).sum(0); sig = (w[:, None] * (mu - gm) ** 2).sum(0)
        for i, kk in enumerate(cs): noi += w[i] * Xx[yy == kk].var(0)
        out += sig / (noi + 1e-12)
    return out

mu = Xr.mean(0); sd = Xr.std(0) + 1e-9; Xrz = (Xr - mu) / sd; rng = np.random.default_rng(0)
print("%-6s HW|r| peak @smp   | value-SNR peak @smp   null z   | #smp HW>floor" % "lab")
for name, lab_all in L.items():
    lab = lab_all[kr]
    ch = np.abs(corr(Xr, HW[lab].astype(float))); vs = whv(Xrz, lab)
    nulls = np.array([whv(Xrz, rng.permutation(lab)).max() for _ in range(12)]); z = (vs.max() - nulls.mean()) / (nulls.std() + 1e-12)
    print("%-6s %.3f @%5d       | %.3f @%5d        %5.1f %s | %d" % (name, ch.max(), ch.argmax(), vs.max(), vs.argmax(), z, "LEAK" if z > 3 else "    ", int((ch > floor).sum())))
