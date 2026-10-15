#!/usr/bin/env python3
"""5.2.2 small test: inert-representation formation of J_t (quat_ideal_create_O0_inert_odd tail).
Window: 8000 samples @ offset 0 = start of ibz_vec_2_gaussian_mul((a,b),(c,-d)).
Labels (byte0): generator coords a,b,c,d (operands), t (multiplier later), x,y (outputs), n.
Metrics: CPA-style HW|r| and value|r| with noise floor; within-HW value-SNR + permutation null z."""
import numpy as np
import os as _os
U = _os.environ.get("SQI_DATA", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "data")) + "/"
HW = np.array([bin(i).count("1") for i in range(256)], np.int32)
ABCD = np.fromfile(U + "equiv_abcd_low4.bin", np.uint8).reshape(-1, 4, 4)
L = {"a": ABCD[:, 0, 0], "b": ABCD[:, 1, 0], "c": ABCD[:, 2, 0], "d": ABCD[:, 3, 0],
     "t": np.fromfile(U + "equiv_t_low4.bin", np.uint8).reshape(-1, 4)[:, 0],
     "x": np.fromfile(U + "equiv_x_low4.bin", np.uint8).reshape(-1, 4)[:, 0],
     "y": np.fromfile(U + "equiv_y_low4.bin", np.uint8).reshape(-1, 4)[:, 0],
     "n": np.fromfile(U + "equiv_n_low4.bin", np.uint8).reshape(-1, 4)[:, 0]}
d = np.load(U + "traces_equiv_small.npz")
X = d["traces"].astype(np.float64); cls = d["classes"].astype(int); k = d["kept_idx"]
r = cls == 1; Xr = X[r]; kr = k[r]; S = X.shape[1]; n = int(r.sum())
floor = np.sqrt(2 * np.log(S) / n)
print("traces %s random=%d fixed=%d  noise floor |r| ~ %.3f" % (X.shape, n, (~r).sum(), floor))

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

mu = Xr.mean(0); sd = Xr.std(0) + 1e-9; Xrz = (Xr - mu) / sd
rng = np.random.default_rng(0)
print("%-4s  HW|r| peak @smp   value|r| peak @smp   | value-SNR peak @smp  null(mean±sd)   z" % "lab")
for name, lab_all in L.items():
    lab = lab_all[kr].astype(np.int32)
    ch = np.abs(corr(Xr, HW[lab].astype(float))); cv = np.abs(corr(Xr, lab.astype(float)))
    vs = whv(Xrz, lab); nulls = np.array([whv(Xrz, rng.permutation(lab)).max() for _ in range(12)])
    z = (vs.max() - nulls.mean()) / (nulls.std() + 1e-12)
    print("%-4s  %.3f @%5d       %.3f @%5d        |  %.3f @%5d      %.3f±%.3f   %5.1f %s"
          % (name, ch.max(), ch.argmax(), cv.max(), cv.argmax(), vs.max(), vs.argmax(), nulls.mean(), nulls.std(), z, "<-- LEAK" if z > 3 else ""))
