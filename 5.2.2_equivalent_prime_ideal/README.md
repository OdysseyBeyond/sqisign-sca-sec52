# 5.2.2 — Leakage from the equivalent prime ideal (`EquivalentCoprimeIdeal`)

Target: the routine that turns the accepted generator into the inert
representation `(n, (x, y))` of the odd-prime-norm ideal `J_t ~ I_sk,chl`,
`quat_ideal_create_O0_inert_odd` (tail of
`quat_ideal_small_equivalent_coprime`). With the reduced generator
`gamma' = a + b i + c j + d k` (coordinates mod `n`) it computes
`s = c^2 + d^2`, `t = (2s)^-1`, the Gaussian product `(a + b i)(c - d i)` and
`x' = (ac + bd) t`, `y' = (bc - ad - s) t` (all mod `n`). Listing 2 of the paper
(`results/listing_equivprime.tex`) shows the traced tail; the acquisition window
(`TVLA_TRIG_EQUIVREGION`, patch 0001) opens right before the Gaussian product,
i.e. after the variable-time inversion, and closes after
`quat_xyn_to_inert_ideal`.

**Host streams the exact input.** The enumeration and the primality test of
`EquivalentCoprimeIdeal` are far too slow for the M4, so `host/equiv_host.c`
runs `Intersect(a_fixed, b, split_fixed)` followed by the full
`quat_ideal_small_equivalent_coprime` on the host for every record of
`5.2.1_intersection/data/tvla_inputs_rk.bin`, with the PRNG re-seeded from the
record (so the fixed class maps to one fixed `J_t`), and dumps

* the exact input `(gen = (coord[0..3], denom), norm = n)` of
  `quat_ideal_create_O0_inert_odd` → `data/tvla_inputs_equiv.bin` (device records),
* the values at the Gaussian product `(a, b, c, d)`, `s`, `t` → `equiv_abcd_low4.bin`,
  `equiv_s_low4.bin`, `equiv_t_low4.bin`,
* the outputs `x`, `y` and `n` → `equiv_x_low4.bin`, `equiv_y_low4.bin`, `equiv_n_low4.bin`,
* the class of each record → `equiv_classes.bin`.

The device then runs the unmodified library function from its entry, so the
`(a, b, c, d)` reaching the traced multiply are the host-dumped labels.

## Files

```
firmware/
  equiv_target.c        receives (gen, n), runs quat_ideal_create_O0_inert_odd; trigger TRIG3 inside ideal.c
  equiv_prime_target.c  receives n, runs ibz_probab_prime(n, 24) between trigger_high/low
                        (primality test of n = nrd(J_t) as executed by EquivalentCoprimeIdeal)
host/
  equiv_host.c          generator described above (-DTVLA_DUMP_EQUIV)
  make_prime_inputs.py  tvla_inputs_prime.bin = the n field of every record of tvla_inputs_equiv.bin
  build_host.sh         gcc build (needs ../../common/firmware/sqisign)
data/                   device input streams and labels actually used (regenerable byte-for-byte)
analysis/
  recovery_ge.py             LOVO GE of byte 0 of a, b, c, d, -Os (8,000-sample window) [and the 8,000-sample -O0 run]
  recovery_ge_longwindow.py  same protocol for the 24,400-sample -O0 run (memory-aware), Table 5 -O0 rows
  leakcheck.py               first look: |r| with bit 0 and with HW, value-SNR + permutation null, all labels
  fullwindow_scan.py         whole-region scan (decimated capture covering the ~170k-sample formation): x, y, t, n null
  prime_leakcheck.py         does n leak during its primality test (sieve / Montgomery set-up / MR)?
  make_pgf_figure.py         results/equiv_ge.json -> results/fig_exp_equivprime.tex   (no traces needed)
  make_pdf_figure.py         results/equiv_ge.json -> results/fig_exp_equivprime.{pdf,png}
results/
  equiv_ge.json              GE(N), |r| peaks and positions, POIs, for R32-Os, R32-O0 (24,400 window)
                             and R32-O0-8000 (the superseded short-window -O0 run)
  fig_exp_equivprime.{tex,pdf,png}, listing_equivprime.tex
```

## Template design (why `split POI`)

The `O0` basis forces `a ≡ d` and `b ≡ c (mod 2)`, and the parity bit of each
pair shifts the whole waveform (|r| ≈ 0.82–0.83 over > 1,000 samples: a
data-dependent timing difference). With points of interest chosen by value-SNR
alone the parity samples crowd out everything else and the attack stalls at one
recovered bit. `recovery_ge*.py` therefore selects 20 points by |r| with
HW(bits 1–7) and 4 by |r| with bit 0, then fits bit-linear templates.

## Firmware variants (from `common/firmware`)

| Trace set | TARGET | TVLA_TARGET_SRC | TVLA_DEFS | OPT | samples | input stream |
|---|---|---|---|---|---|---|
| `traces_equivos_*.npz` | `sqisign-equiv-r32` | `equiv_target.c` | `-DTVLA_TRIG_EQUIVREGION` | default (-Os) | 8000 | `tvla_inputs_equiv.bin` |
| `traces_equivlongo0_*.npz` | `sqisign-equiv-r32-o0` | `equiv_target.c` | `-DTVLA_TRIG_EQUIVREGION` | `OPT=0` | 24400 | `tvla_inputs_equiv.bin` |
| `traces_equivo0_*.npz` (superseded) | `sqisign-equiv-r32-o0` | `equiv_target.c` | `-DTVLA_TRIG_EQUIVREGION` | `OPT=0` | 8000 | `tvla_inputs_equiv.bin` |
| `traces_equiv_fullwin.npz` | `sqisign-equiv-r32` | `equiv_target.c` | `-DTVLA_TRIG_EQUIVREGION` | default | 8000 × decimate 32 | `tvla_inputs_equiv.bin` |
| `traces_prime_os.npz` | `sqisign-prime-r32` | `equiv_prime_target.c host_rng.c` | `-DSQISIGN_SINGLE_THREADED` | default | 8000 | `tvla_inputs_prime.bin` |

All at `RADIX_32`, 21,000 records for the recovery sets (`capture_chunked.py`,
`--adc-x 4 --gain 30`), 2,500 / 5,000 records for the scans (`capture_single.py`).
The -O0 Gaussian product is longer than the -Os one: the Hamming-weight leakage
point of `c` moves from sample 4,634 (-Os) to 21,014 (-O0), which is why the
-O0 recovery set was re-acquired with a 24,400-sample window. The primality
target computes for ≈ 0.2 s per record; use `--settle 0.45` so the scope is not
re-armed while the device is still busy.

## Running the analysis

```bash
export SQI_DATA=/path/to/dir/with/labels/and/traces   # default: ./data
python analysis/recovery_ge.py R32-Os                  # traces_equivos_*.npz   -> results/equiv_ge.json
python analysis/recovery_ge_longwindow.py              # traces_equivlongo0_*.npz -> results/equiv_ge.json (R32-O0)
python analysis/make_pgf_figure.py                     # -> results/fig_exp_equivprime.tex
python analysis/make_pdf_figure.py                     # -> results/fig_exp_equivprime.{pdf,png}
python analysis/fullwindow_scan.py                     # traces_equiv_fullwin.npz
python analysis/prime_leakcheck.py traces_prime_os.npz # traces in $SQI_DATA
```
