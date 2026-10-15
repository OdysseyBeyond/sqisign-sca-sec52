#!/usr/bin/env python3
"""Positive control on the SAME traces (traces_x2full.npz, X2/Y2 formation region, decimate 16):
   operand labels  x_pre = tmp.v[0]/2 and t   (multiplicands of ibz_mul(&x,&x,&t) at the aligned start)
   vs result label X2 = (x_pre*t) mod N2    (division result, only stored).
If operands leak and the result does not, the null is about the quantity, not the measurement."""
import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import os as _os
U = _os.environ.get("SQI_DATA", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "data")) + "/"
RES = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "results"); _os.makedirs(RES, exist_ok=True)
DEC = 16
HW = np.array([bin(i).count("1") for i in range(256)], np.int32)
L = {"X2 (result)": np.fromfile(U + "x2_low4.bin", np.uint8).reshape(-1, 4),
     "x_pre (operand)": np.fromfile(U + "x2_xpre_low4.bin", np.uint8).reshape(-1, 4),
     "t (operand)": np.fromfile(U + "x2_t_low4.bin", np.uint8).reshape(-1, 4)}
d = np.load(U + "traces_x2full.npz")
X = d["traces"].astype(np.float64); cls = d["classes"].astype(int); k = d["kept_idx"]
r = cls == 1; Xr = X[r]; kr = k[r]; S = X.shape[1]; n = int(r.sum())
floor = np.sqrt(2 * np.log(S) / n)
print("random n=%d  samples=%d  max-|r| noise floor ~ %.3f\n" % (n, S, floor))

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
rng = np.random.default_rng(1); res = {}
print("%-16s %-4s  HW|r| peak @raw      (null z)   | value-SNR peak @raw     (null z)" % ("label", "byte"))
for name, lab4 in L.items():
    for b in (0, 1):
        lab = lab4[kr, b].astype(np.int32)
        c = np.abs(corr(Xr, HW[lab].astype(float))); cj = int(c.argmax())
        cn = np.array([np.abs(corr(Xr, HW[rng.permutation(lab)].astype(float))).max() for _ in range(12)])
        cz = (c.max() - cn.mean()) / (cn.std() + 1e-12)
        vs = whv(Xrz, lab); vj = int(vs.argmax())
        vn = np.array([whv(Xrz, rng.permutation(lab)).max() for _ in range(12)])
        vz = (vs.max() - vn.mean()) / (vn.std() + 1e-12)
        print("%-16s b%d    %.3f @%6d   (z=%5.1f)   |   %.3f @%6d   (z=%5.1f)  %s"
              % (name, b, c.max(), DEC * cj, cz, vs.max(), DEC * vj, vz, "<-- LEAK" if (cz > 3 or vz > 3) else ""))
        if b == 0: res[name] = dict(hw=c, vs=vs)

xs = DEC * np.arange(S)
fig, ax = plt.subplots(3, 1, figsize=(14, 8.5), sharex=True)
ax[0].plot(xs, Xr.mean(0), lw=0.4, color="#444"); ax[0].set_ylabel("mean trace")
ax[0].set_title("Same traces, three labels: operands of ibz_mul(&x,&x,&t) vs its reduced result X2  (R32 -Os, n=%d)" % n, fontsize=10)
cols = {"X2 (result)": "#D55E00", "x_pre (operand)": "#0072B2", "t (operand)": "#009E73"}
for name in L:
    ax[1].plot(xs, res[name]["hw"], lw=0.6, color=cols[name], label="HW b0: " + name)
    ax[2].plot(xs, res[name]["vs"], lw=0.6, color=cols[name], label="b0: " + name)
ax[1].axhline(floor, ls=":", color="k", lw=0.8); ax[1].set_ylabel("|r| (HW)"); ax[1].legend(fontsize=8, loc="upper right")
ax[2].set_ylabel("within-HW value-SNR"); ax[2].legend(fontsize=8, loc="upper right"); ax[2].set_xlabel("raw ADC sample after trigger (X2 multiply starts at 0)")
fig.tight_layout(); fig.savefig(_os.path.join(RES, "x2full_control.png"), dpi=130); print("\nsaved x2full_control.png")
