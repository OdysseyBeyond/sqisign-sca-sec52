#!/usr/bin/env python3
"""5.2.2 recovery: leave-one-value-out GE(N) with bit-linear templates (12 POIs by within-HW value-SNR),
averaged over all 256 byte values, for the low byte of each generator coordinate a,b,c,d of J_t,
on the R32 -Os and R32 -O0 full captures (traces_equivos_*, traces_equivo0_*; 8000 samples @ offset 0).
Also the matched-N value-SNR peak. Figure fig:exp-equivprime + numbers JSON."""
import numpy as np, glob, json, sys, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import os as _os
U = _os.environ.get("SQI_DATA", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "data")) + "/"
RES = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "results"); _os.makedirs(RES, exist_ok=True)
HW = np.array([bin(i).count("1") for i in range(256)], np.int32)
BITS = np.array([[(v >> i) & 1 for i in range(8)] for v in range(256)], float); PHI = np.hstack([np.ones((256, 1)), BITS])
KPOI, NMAX = 24, 40
ABCD = np.fromfile(U + "equiv_abcd_low4.bin", np.uint8).reshape(-1, 4, 4)
LAB = {"a": ABCD[:, 0, 0].astype(np.int32), "b": ABCD[:, 1, 0].astype(np.int32), "c": ABCD[:, 2, 0].astype(np.int32), "d": ABCD[:, 3, 0].astype(np.int32)}

def concat(prefix):
    ps = sorted(glob.glob(U + prefix + "_[0-9]*.npz"))
    if not ps: return None
    Xs, ks, cs = [], [], []
    for p in ps:
        dd = np.load(p); Xs.append(dd["traces"]); ks.append(dd["kept_idx"]); cs.append(dd["classes"])
    X = np.concatenate(Xs); k = np.concatenate(ks); c = np.concatenate(cs); o = np.argsort(k)
    return X[o].astype(np.float64), c[o].astype(int), k[o], len(ps)

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

def lovo_curve(X, cls, k, lab_all, nv=17900, seed=0):
    lab = lab_all[k]; r = np.where(cls == 1)[0]; Xr = X[r]; y = lab[r]
    mu = Xr.mean(0); sd = Xr.std(0) + 1e-9; Xz = (Xr - mu) / sd
    vs = whv(Xz[:nv], y[:nv])
    HW7 = np.array([bin(v >> 1).count("1") for v in range(256)], float)
    def corr(T, lab):
        a = lab - lab.mean(); t = T - T.mean(0); return (t.T @ a) / len(a) / (T.std(0) * a.std() + 1e-12)
    c7 = np.abs(corr(Xz[:nv], HW7[y[:nv]])); c0 = np.abs(corr(Xz[:nv], (y[:nv] & 1).astype(float)))
    POI = np.concatenate([np.argsort(c7)[::-1][:KPOI - 4], np.argsort(c0)[::-1][:4]]); Z = Xz[:, POI]
    cnt = np.bincount(y, minlength=256); vals = np.where(cnt >= NMAX)[0]
    R = np.zeros((len(vals), NMAX)); rng = np.random.default_rng(seed)
    for i, v in enumerate(vals):
        te = rng.permutation(np.where(y == v)[0])[:NMAX]; tr = np.where(y != v)[0]
        beta, *_ = np.linalg.lstsq(PHI[y[tr]], Z[tr], rcond=None); M = PHI @ beta
        Ci = np.linalg.pinv(np.cov(Z[tr] - M[y[tr]], rowvar=False) + 1e-6 * np.eye(KPOI))
        F = Z[te]; LL = np.zeros((len(F), 256))
        for u in range(256):
            dd = F - M[u]; LL[:, u] = -0.5 * np.einsum('nd,de,ne->n', dd, Ci, dd)
        acc = np.cumsum(LL, axis=0); R[i] = (acc > acc[:, v][:, None]).sum(1)
    ge = R.mean(0); w = np.where(ge <= 1)[0]
    return dict(ge=ge.tolist(), sr40=float((R[:, -1] == 0).mean()), nstar=(int(w[0] + 1) if len(w) else None),
                vsnr=float(vs.max()), vsnr_raw=int(vs.argmax()), nvals=int(len(vals)), nprof=int(len(r)),
                hw7_peak=float(c7.max()), hw7_pos=int(c7.argmax()), b0_peak=float(c0.max()), b0_pos=int(c0.argmax()))

builds = [("R32-Os", "traces_equivos"), ("R32-O0", "traces_equivo0")]
if len(sys.argv) > 1: builds = [b for b in builds if b[0] in sys.argv[1:]]
res = {}
for tag, prefix in builds:
    got = concat(prefix)
    if got is None: print(tag, "no parts yet"); continue
    X, cls, k, nparts = got; print("%s: %d parts -> %s random=%d fixed=%d" % (tag, nparts, X.shape, (cls == 1).sum(), (cls == 0).sum()))
    res[tag] = {}
    for co in ("a", "b", "c", "d"):
        rr = lovo_curve(X, cls, k, LAB[co]); res[tag][co] = rr; g = rr["ge"]
        print("  %s %s: |r|HW(b1-7)=%.3f@%d |r|b0=%.3f@%d  GE N=1 %.1f  N=5 %.1f  N=10 %.1f  N=20 %.1f  N=40 %.1f  N*=%s  SR@40=%.2f"
              % (tag, co, rr["hw7_peak"], rr["hw7_pos"], rr["b0_peak"], rr["b0_pos"], g[0], g[4], g[9], g[19], g[39], rr["nstar"], rr["sr40"]))
_jp = _os.path.join(RES, "equiv_ge.json")
_old = json.load(open(_jp)) if _os.path.exists(_jp) else {}
_old.update(res); json.dump(_old, open(_jp, "w"), indent=1)   # merge: keep builds not re-run

if res:
    col = {"R32-Os": "#D55E00", "R32-O0": "#0072B2"}; ls = {"a": "-", "b": "--", "c": "-.", "d": ":"}
    fig, ax = plt.subplots(figsize=(6.4, 3.6)); N = np.arange(1, NMAX + 1)
    for tag in res:
        for co in ("a", "b", "c", "d"):
            g = np.array(res[tag][co]["ge"]); ax.plot(N, g, color=col[tag], ls=ls[co], lw=1.6, label="%s, %s" % (tag.replace("R32-", "32-bit "), co))
    ax.axhline(1, color="#555", lw=0.8, ls="--"); ax.text(1.15, 1.12, "GE = 1", fontsize=8, color="#555")
    ax.set_yscale("log"); ax.set_ylim(0.4, 128); ax.set_yticks([0.5, 1, 2, 5, 10, 20, 50, 100]); ax.set_yticklabels(["0.5", "1", "2", "5", "10", "20", "50", "100"])
    ax.set_xlim(1, NMAX + 1); ax.set_xlabel("number of attack traces $N$"); ax.set_ylabel("guessing entropy of byte 0")
    ax.grid(alpha=0.25, lw=0.5, which="both"); ax.legend(frameon=False, fontsize=7, ncol=2, loc="upper right")
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    fig.tight_layout(); fig.savefig(_os.path.join(RES, "fig_exp_equivprime_quicklook.pdf"))
    print("saved fig_exp_equivprime.pdf/png")
