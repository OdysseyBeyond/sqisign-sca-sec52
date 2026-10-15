#!/usr/bin/env python3
"""Null test: are the output-coefficient 'recoveries' real or chance?
Compare real value-SNR peak and GE to label-permuted nulls."""
import numpy as np
import os as _os
U = _os.environ.get("SQI_DATA", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "data")) + "/"
HW = np.array([bin(i).count("1") for i in range(256)], np.int32)
ox = np.fromfile(U + "out_x_low4.bin", np.uint8).reshape(-1, 4)[:, 0].astype(np.int32)
oy = np.fromfile(U + "out_y_low4.bin", np.uint8).reshape(-1, 4)[:, 0].astype(np.int32)

def whv(Xz, y, hs=(3, 4, 5)):
    S = Xz.shape[1]; out = np.zeros(S)
    for h in hs:
        m = HW[y] == h
        if m.sum() < 40: continue
        Xx, yy = Xz[m], y[m]; cs = np.unique(yy)
        mu = np.zeros((len(cs), S)); w = np.zeros(len(cs)); noi = np.zeros(S)
        for i, kk in enumerate(cs): g = Xx[yy == kk]; mu[i] = g.mean(0); w[i] = len(g)
        w = w / w.sum(); gm = (w[:, None] * mu).sum(0); sig = (w[:, None] * (mu - gm) ** 2).sum(0)
        for i, kk in enumerate(cs): noi += w[i] * Xx[yy == kk].var(0)
        out += sig / (noi + 1e-12)
    return out

def test(tag, npz, lab_all):
    d = np.load(U + npz); X = d["traces"].astype(np.float64); cls = d["classes"].astype(int); k = d["kept_idx"]
    lab = lab_all[k]; r = cls == 1
    mu = X[r].mean(0); sd = X[r].std(0) + 1e-9; Xrz = (X[r] - mu) / sd; yr = lab[r]
    real = whv(Xrz, yr).max()
    rng = np.random.default_rng(0); nulls = []
    for _ in range(20):
        yp = rng.permutation(yr); nulls.append(whv(Xrz, yp).max())
    nulls = np.array(nulls)
    z = (real - nulls.mean()) / (nulls.std() + 1e-12)
    print("%-14s value-SNR real=%.4f  null=%.4f±%.4f  z=%.1f  %s" %
          (tag, real, nulls.mean(), nulls.std(), z, "LEAK" if z > 3 else "no sig."))

print("=== out.x byte0 ===")
test("out.x -Os", "traces_outos.npz", ox)
test("out.x -O0", "traces_outo0.npz", ox)
print("=== out.y byte0 ===")
test("out.y -Os", "traces_outos.npz", oy)
test("out.y -O0", "traces_outo0.npz", oy)
