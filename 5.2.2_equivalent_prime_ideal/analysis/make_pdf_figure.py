#!/usr/bin/env python3
"""fig_exp_equivprime.pdf/png from equiv_ge.json: R32-Os (solid, 8000-sample window) vs R32-O0 (dashed, 24400-sample window)."""
import json, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import os as _os
RES = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "results")
e = json.load(open(_os.path.join(RES,"equiv_ge.json")))
col = {"a": "#0072B2", "b": "#D55E00", "c": "#009E73", "d": "#CC79A7"}
fig, ax = plt.subplots(figsize=(6.4, 3.6)); N = np.arange(1, 41)
for tag, ls in (("R32-Os", "-"), ("R32-O0", "--")):
    for co in "abcd":
        ax.plot(N, np.array(e[tag][co]["ge"]), color=col[co], ls=ls, lw=1.6, label="$%s$, %s" % (co, tag.replace("R32-", "-")))
ax.axhline(1, color="#555", lw=0.8, ls="--"); ax.text(1.15, 1.12, "GE = 1", fontsize=8, color="#555")
ax.set_yscale("log"); ax.set_ylim(0.4, 128); ax.set_yticks([0.5, 1, 2, 5, 10, 20, 50, 100]); ax.set_yticklabels(["0.5", "1", "2", "5", "10", "20", "50", "100"])
ax.set_xlim(1, 41); ax.set_xlabel("number of attack traces $N$"); ax.set_ylabel("guessing entropy of byte 0")
ax.grid(alpha=0.25, lw=0.5, which="both"); ax.legend(frameon=False, fontsize=7, ncol=2, loc="upper right")
for s in ("top", "right"): ax.spines[s].set_visible(False)
fig.tight_layout(); fig.savefig(_os.path.join(RES,"fig_exp_equivprime.pdf")); fig.savefig(_os.path.join(RES,"fig_exp_equivprime.png"), dpi=200)
print("saved")
