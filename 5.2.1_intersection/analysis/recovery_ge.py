#!/usr/bin/env python3
"""Numbers for Section 5.2.1 (leakage from the intersection), gaussian_mul operand b.x byte0.
Metric: leave-one-value-out GE(N) with bit-linear templates (12 POIs by within-HW value-SNR), averaged over all byte values.
Also: matched-N within-HW value-SNR peak, single-trace CV rank, and N* = first N with GE <= 1.
Outputs: fig_exp_intersection.{pdf,png}, sec521_numbers.json"""
import numpy as np, json, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import os as _os
U = _os.environ.get("SQI_DATA", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "data")) + "/"
RES = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "results"); _os.makedirs(RES, exist_ok=True)
HW = np.array([bin(i).count("1") for i in range(256)], np.int32)
BITS = np.array([[(v >> i) & 1 for i in range(8)] for v in range(256)], float); PHI = np.hstack([np.ones((256, 1)), BITS])
KPOI, NMAX = 12, 40
bx0 = np.fromfile(U + "gauss_bx0_rk.bin", np.uint8).astype(np.int32)

def whv(Xz, y, hs=(3, 4, 5)):
    out = np.zeros(Xz.shape[1])
    for h in hs:
        m = HW[y] == h
        if m.sum() < 40: continue
        Xx, yy = Xz[m], y[m]; cs = np.unique(yy)
        mu = np.zeros((len(cs), Xz.shape[1])); w = np.zeros(len(cs)); noi = np.zeros(Xz.shape[1])
        for i, kk in enumerate(cs): g = Xx[yy == kk]; mu[i] = g.mean(0); w[i] = len(g)
        w = w / w.sum(); gm = (w[:, None] * mu).sum(0); sig = (w[:, None] * (mu - gm) ** 2).sum(0)
        for i, kk in enumerate(cs): noi += w[i] * Xx[yy == kk].var(0)
        out += sig / (noi + 1e-12)
    return out

def lovo_curve(X, cls, k, nv=17900, seed=0):
    lab = bx0[k]; r = np.where(cls == 1)[0]
    Xr = X[r]; y = lab[r]
    mu = Xr.mean(0); sd = Xr.std(0) + 1e-9; Xz = (Xr - mu) / sd
    vs = whv(Xz[:nv], y[:nv]); POI = np.argsort(vs)[::-1][:KPOI]; Z = Xz[:, POI]
    cnt = np.bincount(y, minlength=256); vals = np.where(cnt >= NMAX)[0]
    R = np.zeros((len(vals), NMAX)); rng = np.random.default_rng(seed)
    for i, v in enumerate(vals):
        te = rng.permutation(np.where(y == v)[0])[:NMAX]; tr = np.where(y != v)[0]
        beta, *_ = np.linalg.lstsq(PHI[y[tr]], Z[tr], rcond=None); M = PHI @ beta
        Ci = np.linalg.pinv(np.cov(Z[tr] - M[y[tr]], rowvar=False) + 1e-6 * np.eye(KPOI))
        F = Z[te]; LL = np.zeros((len(F), 256))
        for u in range(256):
            dd = F - M[u]; LL[:, u] = -0.5 * np.einsum('nd,de,ne->n', dd, Ci, dd)
        acc = np.cumsum(LL, axis=0)
        R[i] = (acc > acc[:, v][:, None]).sum(1)
    ge = R.mean(0); sr = (R == 0).mean(0)
    w = np.where(ge <= 1)[0]; nstar = int(w[0] + 1) if len(w) else None
    return dict(ge=ge, sr=sr, nstar=nstar, vsnr=float(vs.max()), vsnr_pos=int(vs.argmax()), nvals=len(vals),
                nprof=int(len(r)), nfix=int((cls == 0).sum()))

sets = [("R16-Os", "traces_r16gauss.npz", "16-bit limbs, \\texttt{-Os}"),
        ("R16-O0", "traces_o0r16.npz", "16-bit limbs, \\texttt{-O0}"),
        ("R32-O0", "traces_o0r32.npz", "32-bit limbs, \\texttt{-O0}")]
res = {}
for tag, npz, _ in sets:
    d = np.load(U + npz); res[tag] = lovo_curve(d["traces"].astype(np.float64), d["classes"].astype(int), d["kept_idx"])
    g = res[tag]["ge"]
    print("%-7s nprof=%d nfix=%d vals=%d  vSNR=%.3f@%d  GE: N=1 %.1f  N=5 %.1f  N=10 %.1f  N=20 %.1f  N=40 %.1f   N*(GE<=1)=%s  SR@40=%.2f"
          % (tag, res[tag]["nprof"], res[tag]["nfix"], res[tag]["nvals"], res[tag]["vsnr"], res[tag]["vsnr_pos"],
             g[0], g[4], g[9], g[19], g[39], res[tag]["nstar"], res[tag]["sr"][39]))

json.dump({t: {kk: (vv.tolist() if hasattr(vv, "tolist") else vv) for kk, vv in r_.items()} for t, r_ in res.items()},
          open(_os.path.join(RES, "sec521_numbers.json"), "w"), indent=1)

# Figure: GE(N), one axis, fixed hue order, legend + direct end labels (dataviz method)
col = {"R16-Os": "#D55E00", "R16-O0": "#0072B2", "R32-O0": "#009E73"}
lab = {"R16-Os": "16-bit limbs, -Os", "R16-O0": "16-bit limbs, -O0", "R32-O0": "32-bit limbs, -O0"}
fig, ax = plt.subplots(figsize=(6.4, 3.6))
N = np.arange(1, NMAX + 1)
for tag in ("R16-Os", "R32-O0", "R16-O0"):
    g = res[tag]["ge"]; ax.plot(N, g, color=col[tag], lw=2, label=lab[tag])
    ax.text(NMAX + 0.6, g[-1], "%.1f" % g[-1], fontsize=8, va="center", color="#333")
ax.axhline(1, color="#555", lw=0.8, ls="--"); ax.text(1.2, 2.2, "GE = 1", fontsize=8, color="#555")
ax.set_xlim(1, NMAX + 4); ax.set_ylim(0, 115); ax.set_yticks([0, 25, 50, 75, 100])
ax.set_xlabel("number of attack traces $N$"); ax.set_ylabel("guessing entropy of byte 0")
ax.grid(alpha=0.25, lw=0.5); ax.legend(frameon=False, fontsize=8, loc="upper right")
for s in ("top", "right"): ax.spines[s].set_visible(False)
fig.tight_layout()
fig.savefig(_os.path.join(RES, "fig_exp_intersection.pdf")); fig.savefig(_os.path.join(RES, "fig_exp_intersection.png"), dpi=200)
print("saved fig_exp_intersection.pdf/png")
