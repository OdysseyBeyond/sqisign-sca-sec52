#!/usr/bin/env python3
"""5.2.2 whole-region scan (traces_equiv_fullwin.npz: 8000 samples, decimate 32 -> covers 256k raw >= region 170k).
Which byte0 labels leak anywhere in the formation of J_t's inert representation?
Operands a,b,c,d (gaussian multiply), t (multiplier of the x,y products), outputs x,y, modulus n."""
import numpy as np, json, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import os as _os
U = _os.environ.get("SQI_DATA", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "data")) + "/"
RES = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "results"); _os.makedirs(RES, exist_ok=True)
DEC = 32
HW = np.array([bin(i).count("1") for i in range(256)], np.int32)
ABCD = np.fromfile(U + "equiv_abcd_low4.bin", np.uint8).reshape(-1, 4, 4)
L = {"a": ABCD[:, 0, 0], "b": ABCD[:, 1, 0], "c": ABCD[:, 2, 0], "d": ABCD[:, 3, 0]}
for nm in ("t", "x", "y", "n"): L[nm] = np.fromfile(U + "equiv_%s_low4.bin" % nm, np.uint8).reshape(-1, 4)[:, 0]
d = np.load(U + "traces_equiv_fullwin.npz")
X = d["traces"].astype(np.float64); cls = d["classes"].astype(int); k = d["kept_idx"]
r = cls == 1; Xr = X[r]; kr = k[r]; S = X.shape[1]; n = int(r.sum())
floor = np.sqrt(2 * np.log(S) / n)
print("traces %s random=%d  noise floor |r| ~ %.3f  (raw span %d)" % (X.shape, n, floor, DEC * S))

def corr(T, lab):
    a = lab - lab.mean(); t = T - T.mean(0)
    return (t.T @ a) / len(a) / (T.std(0) * a.std() + 1e-12)

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

mu = Xr.mean(0); sd = Xr.std(0) + 1e-9; Xrz = (Xr - mu) / sd
rng = np.random.default_rng(0); res = {}; C = {}; V = {}
print("%-3s  HW|r| peak @raw      | value-SNR peak @raw     null z" % "lab")
for name, lab_all in L.items():
    lab = lab_all[kr].astype(np.int32)
    ch = np.abs(corr(Xr, HW[lab].astype(float))); vs = whv(Xrz, lab)
    nulls = np.array([whv(Xrz, rng.permutation(lab)).max() for _ in range(15)])
    z = (vs.max() - nulls.mean()) / (nulls.std() + 1e-12)
    C[name] = ch; V[name] = vs
    res[name] = dict(hw_peak=float(ch.max()), hw_raw=int(DEC * ch.argmax()), vsnr=float(vs.max()), vsnr_raw=int(DEC * vs.argmax()), z=float(z))
    print("%-3s  %.3f @%6d       |  %.3f @%6d        %5.1f %s" % (name, ch.max(), DEC * ch.argmax(), vs.max(), DEC * vs.argmax(), z, "LEAK" if z > 3 else ""))
json.dump(dict(n=n, floor=floor, res=res), open(_os.path.join(RES, "equiv_fullwin.json"), "w"), indent=1)

xs = DEC * np.arange(S)
fig, ax = plt.subplots(3, 1, figsize=(13, 8), sharex=True)
ax[0].plot(xs, Xr.mean(0), lw=0.4, color="#444"); ax[0].set_ylabel("mean trace")
ax[0].set_title("Formation of the inert representation of $J_t$ (R32 -Os, decimate 32, %d random traces)" % n, fontsize=10)
cols = {"a": "#0072B2", "b": "#D55E00", "c": "#009E73", "d": "#CC79A7", "t": "#E69F00", "x": "#56B4E9", "y": "#F0E442", "n": "#999999"}
for nm in ("a", "b", "c", "d"): ax[1].plot(xs, C[nm], lw=0.6, color=cols[nm], label="HW " + nm)
for nm in ("x", "y"): ax[1].plot(xs, C[nm], lw=0.6, color=cols[nm], label="HW " + nm, alpha=0.8)
ax[1].axhline(floor, ls=":", color="k", lw=0.8); ax[1].set_ylabel("|r| (HW)"); ax[1].legend(fontsize=7, ncol=6, loc="upper right")
for nm in ("a", "b", "c", "d", "x", "y", "t"): ax[2].plot(xs, V[nm], lw=0.6, color=cols[nm], label=nm, alpha=0.9)
ax[2].set_ylabel("within-HW value-SNR"); ax[2].legend(fontsize=7, ncol=7, loc="upper right"); ax[2].set_xlabel("raw ADC sample after trigger (Gaussian multiply starts at 0)")
fig.tight_layout(); fig.savefig(_os.path.join(RES, "equiv_fullwin_scan.png"), dpi=130); print("saved equiv_fullwin_scan.png")
