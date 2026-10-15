#!/usr/bin/env python3
"""Emit self-contained PGFPlots figures from the measured LOVO GE curves.
fig:exp-intersection : sec521_numbers.json (R16-Os, R32-O0, R16-O0), N = 1..40
fig:exp-equivprime   : equiv_ge.json (R32-Os a,b,c,d [+ R32-O0 when present]), N = 1..40
Colour-blind-safe palette (Okabe-Ito), one axis, log-y, legend + no dual axes."""
import json, numpy as np, os as _os
RES = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'results')

def coords(ge, step=1):
    return " ".join("(%d,%.2f)" % (i + 1, max(g, 0.3)) for i, g in enumerate(ge) if (i % step == 0 or i == len(ge) - 1))

AX = r"""\begin{axis}[width=0.72\linewidth, height=0.42\linewidth, ymode=log, ymin=0.4, ymax=128,
      ytick={0.5,1,2,5,10,20,50,100}, yticklabels={0.5,1,2,5,10,20,50,100},
      xmin=1, xmax=40, xlabel={number of attack traces $N$}, ylabel={guessing entropy of byte 0},
      grid=both, grid style={black!10}, legend style={font=\scriptsize, draw=none, fill=none, at={(0.98,0.98)}, anchor=north east},
      tick label style={font=\scriptsize}, label style={font=\small}, line width=1.1pt, no markers, cycle list name=color list]
"""

# ---- fig:exp-intersection ----
s521 = json.load(open(_os.path.join(RES,"sec521_numbers.json")))
cols = {"R16-Os": "D55E00", "R32-O0": "009E73", "R16-O0": "0072B2"}
labs = {"R16-Os": "16-bit limbs, \\texttt{-Os}", "R32-O0": "32-bit limbs, \\texttt{-O0}", "R16-O0": "16-bit limbs, \\texttt{-O0}"}
f1 = ["\\begin{tikzpicture}", AX]
for tag in ("R16-Os", "R32-O0", "R16-O0"):
    f1.append("  \\addplot[color={rgb,255:red,%d;green,%d;blue,%d}] coordinates {%s};" % (int(cols[tag][0:2], 16), int(cols[tag][2:4], 16), int(cols[tag][4:6], 16), coords(s521[tag]["ge"])))
    f1.append("  \\addlegendentry{%s}" % labs[tag])
f1.append("  \\addplot[black!60, dashed, line width=0.6pt, forget plot] coordinates {(1,1) (40,1)};")
f1.append("\\end{axis}\n\\end{tikzpicture}")
open(_os.path.join(RES,"fig_exp_intersection.tex"), "w").write("\n".join(f1))

