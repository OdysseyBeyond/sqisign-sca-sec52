#!/usr/bin/env python3
"""5.2.2, R32 -O0 long window (traces_equivlongo0_*, 24400 samples): same LOVO protocol as equiv_ge.py
(split POI: 20 by |r| with HW(bits1-7) + 4 by |r| with bit 0; bit-linear templates; GE averaged over all
byte values with >= 40 traces). Memory-aware: keeps only random-class traces in float32, standardizes and
correlates in column chunks. Writes results into equiv_ge.json under 'R32-O0' (old 8000-window result kept
as 'R32-O0-8000')."""
import numpy as np, glob, json, sys
import os as _os
U = _os.environ.get("SQI_DATA", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "data")) + "/"
RES = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "results"); _os.makedirs(RES, exist_ok=True)
HW = np.array([bin(i).count("1") for i in range(256)], np.int32)
HW7 = np.array([bin(v >> 1).count("1") for v in range(256)], float)
BITS = np.array([[(v >> i) & 1 for i in range(8)] for v in range(256)], float); PHI = np.hstack([np.ones((256, 1)), BITS])
KPOI, NMAX, NV, CH = 24, 40, 17900, 2000
ABCD = np.fromfile(U + "equiv_abcd_low4.bin", np.uint8).reshape(-1, 4, 4)
LAB = {co: ABCD[:, i, 0].astype(np.int32) for i, co in enumerate("abcd")}
prefix = sys.argv[1] if len(sys.argv) > 1 else "traces_equivlongo0"

# ---- load random-class rows only, float32 ----
ps = sorted(glob.glob(U + prefix + "_[0-9]*.npz")); Xs, ks = [], []; nfix = 0
for p in ps:
    d = np.load(p); c = d["classes"].astype(int); m = c == 1; nfix += (~m).sum()
    Xs.append(d["traces"][m]); ks.append(d["kept_idx"][m])
X = np.concatenate(Xs); k = np.concatenate(ks); del Xs
o = np.argsort(k); X = X[o]; k = k[o]
print("%s: %d parts, random %s float32, fixed dropped %d" % (prefix, len(ps), X.shape, nfix), flush=True)
nS = X.shape[1]
# ---- standardize in place (column chunks) ----
for s in range(0, nS, CH):
    blk = X[:, s:s + CH]; mu = blk.mean(0, dtype=np.float64); sd = blk.std(0, dtype=np.float64) + 1e-9
    X[:, s:s + CH] = ((blk - mu) / sd).astype(np.float32)

def corr_cols(lab, rows):  # |r| per column over the first NV profiling rows
    a = lab - lab.mean(); a = a / (a.std() + 1e-12); out = np.zeros(nS)
    for s in range(0, nS, CH):
        T = X[rows, s:s + CH].astype(np.float64); T -= T.mean(0); sdv = T.std(0) + 1e-12
        out[s:s + CH] = np.abs((T.T @ a) / len(a) / sdv)
    return out

def whv_cols(y, rows, hs=(3, 4, 5)):
    out = np.zeros(nS)
    for s in range(0, nS, CH):
        T = X[rows, s:s + CH].astype(np.float64)
        for h in hs:
            m = HW[y] == h
            if m.sum() < 40: continue
            Xx, yy = T[m], y[m]; cs = np.unique(yy)
            mu = np.zeros((len(cs), T.shape[1])); w = np.zeros(len(cs)); noi = np.zeros(T.shape[1])
            for i, kk in enumerate(cs): g = Xx[yy == kk]; mu[i] = g.mean(0); w[i] = len(g)
            w = w / w.sum(); gm = (w[:, None] * mu).sum(0); sig = (w[:, None] * (mu - gm) ** 2).sum(0)
            for i, kk in enumerate(cs): noi += w[i] * Xx[yy == kk].var(0)
            out[s:s + CH] += sig / (noi + 1e-12)
    return out

res = {}
rows = np.arange(min(NV, len(k)))
for co in "abcd":
    y = LAB[co][k]
    c7 = corr_cols(HW7[y[rows]], rows); c0 = corr_cols((y[rows] & 1).astype(float), rows); vs = whv_cols(y[rows], rows)
    POI = np.concatenate([np.argsort(c7)[::-1][:KPOI - 4], np.argsort(c0)[::-1][:4]]); Z = X[:, POI].astype(np.float64)
    cnt = np.bincount(y, minlength=256); vals = np.where(cnt >= NMAX)[0]
    R = np.zeros((len(vals), NMAX)); rng = np.random.default_rng(0)
    for i, v in enumerate(vals):
        te = rng.permutation(np.where(y == v)[0])[:NMAX]; tr = np.where(y != v)[0]
        beta, *_ = np.linalg.lstsq(PHI[y[tr]], Z[tr], rcond=None); M = PHI @ beta
        Ci = np.linalg.pinv(np.cov(Z[tr] - M[y[tr]], rowvar=False) + 1e-6 * np.eye(KPOI))
        F = Z[te]; LL = np.zeros((len(F), 256))
        for u in range(256):
            dd = F - M[u]; LL[:, u] = -0.5 * np.einsum('nd,de,ne->n', dd, Ci, dd)
        acc = np.cumsum(LL, axis=0); R[i] = (acc > acc[:, v][:, None]).sum(1)
    ge = R.mean(0); w = np.where(ge <= 1)[0]
    res[co] = dict(ge=ge.tolist(), sr40=float((R[:, -1] == 0).mean()), nstar=(int(w[0] + 1) if len(w) else None),
                   vsnr=float(vs.max()), vsnr_raw=int(vs.argmax()), nvals=int(len(vals)), nprof=int(len(k)),
                   hw7_peak=float(c7.max()), hw7_pos=int(c7.argmax()), b0_peak=float(c0.max()), b0_pos=int(c0.argmax()),
                   poi=POI.tolist(), window=int(nS))
    g = ge; print("  %s: |r|HW(b1-7)=%.3f@%d |r|b0=%.3f@%d vSNR=%.2f@%d  GE N=1 %.1f N=5 %.1f N=10 %.1f N=20 %.1f N=40 %.1f N*=%s SR@40=%.2f"
                  % (co, c7.max(), c7.argmax(), c0.max(), c0.argmax(), vs.max(), vs.argmax(), g[0], g[4], g[9], g[19], g[39], res[co]["nstar"], res[co]["sr40"]), flush=True)

_jp = _os.path.join(RES, "equiv_ge.json")
e = json.load(open(_jp)) if _os.path.exists(_jp) else {}
if "R32-O0" in e and "R32-O0-8000" not in e: e["R32-O0-8000"] = e["R32-O0"]
e["R32-O0"] = res
json.dump(e, open(_jp, "w"), indent=1)
print("equiv_ge.json updated")
