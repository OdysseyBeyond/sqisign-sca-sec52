#!/usr/bin/env python3
"""fig:exp-equivprime as PGFPlots from results/equiv_ge.json:
R32-Os a,b,c,d (solid, 8000-sample window); R32-O0 a,b,c,d (dashed, 24400-sample window)."""
import json, os as _os
RES = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "results")

def coords(ge):
    return " ".join("(%d,%.2f)" % (i + 1, max(g, 0.3)) for i, g in enumerate(ge))

AX = r"""\begin{axis}[width=0.72\linewidth, height=0.42\linewidth, ymode=log, ymin=0.4, ymax=128,
      ytick={0.5,1,2,5,10,20,50,100}, yticklabels={0.5,1,2,5,10,20,50,100},
      xmin=1, xmax=40, xlabel={number of attack traces $N$}, ylabel={guessing entropy of byte 0},
      grid=both, grid style={black!10}, legend style={font=\scriptsize, draw=none, fill=none, at={(0.98,0.98)}, anchor=north east, legend columns=2},
      tick label style={font=\scriptsize}, label style={font=\small}, line width=1.1pt, no markers, cycle list name=color list]
"""
e = json.load(open(_os.path.join(RES, "equiv_ge.json")))
cc = {"a": (0, 114, 178), "b": (213, 94, 0), "c": (0, 158, 115), "d": (204, 121, 167)}
f = ["\\begin{tikzpicture}", AX]
for tag, style in (("R32-Os", "solid"), ("R32-O0", "dashed")):
    if tag not in e:
        continue
    for co in "abcd":
        r, g, b = cc[co]
        f.append("  \\addplot[%s, color={rgb,255:red,%d;green,%d;blue,%d}] coordinates {%s};" % (style, r, g, b, coords(e[tag][co]["ge"])))
        f.append("  \\addlegendentry{$%s$, \\texttt{%s}}" % (co, tag.replace("R32-", "-")))
f.append("  \\addplot[black!60, dashed, line width=0.6pt, forget plot] coordinates {(1,1) (40,1)};")
f.append("\\end{axis}\n\\end{tikzpicture}")
open(_os.path.join(RES, "fig_exp_equivprime.tex"), "w").write("\n".join(f))
print("fig_exp_equivprime.tex written; series:", sum(1 for l in f if "addlegendentry" in l))
