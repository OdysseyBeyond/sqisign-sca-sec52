#!/usr/bin/env python3
"""Concatenate the chunked parts written by capture_chunked.py into one .npz,
sorted by global record index (kept_idx), as consumed by the analysis scripts.
  python concat_parts.py <prefix>        # e.g. traces_equivos -> traces_equivos.npz"""
import glob, sys, numpy as np
prefix = sys.argv[1]
ps = sorted(glob.glob(prefix + "_[0-9]*.npz"))
if not ps: raise SystemExit("no parts for " + prefix)
Xs, ks, cs = [], [], []
for p in ps:
    d = np.load(p); Xs.append(d["traces"]); ks.append(d["kept_idx"]); cs.append(d["classes"])
X = np.concatenate(Xs); k = np.concatenate(ks); c = np.concatenate(cs); o = np.argsort(k)
np.savez_compressed(prefix + ".npz", traces=X[o].astype(np.float32), classes=c[o], kept_idx=k[o], samples=X.shape[1])
print("%s.npz: %d parts -> %s" % (prefix, len(ps), X[o].shape))
