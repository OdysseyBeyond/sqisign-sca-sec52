# 5.2.1 — Leakage from the intersection (`quat_ideal_intersect_O0`)

Target: the tail of **Intersect** as called in signing,
`quat_ideal_intersect_O0(out, a, b, split_a)` with `a = ideal_chall_two`,
`split_a = chall_split` (public, fixed here) and **`b = sk_ideal`** (the
secret, streamed per trace). Listing 1 of the paper
(`results/listing_intersection.tex`) reproduces the traced tail and marks the
three regions studied:

| Region | Code | Trigger macro (patch 0001) | Firmware target | Labels (`data/`) |
|---|---|---|---|---|
| **W1** Gaussian multiply | `ibz_vec_2_gaussian_mul(&tmp, &setter, &tmp)`, `setter = 2 b.x + (2 b.y + 1) i` | — (trigger inside `tvla_gauss_target.c`) | `firmware/tvla_gauss_target.c` | `gauss_bx0_rk.bin` = low byte of `b.x` |
| **W2** coordinate-forming multiplies | `X2 = x_pre · t mod N2`, `Y2 = …` | `TVLA_TRIG_OUTREGION` | `firmware/intersect_target_rk.c` | `x2_xpre_low4.bin`, `x2_t_low4.bin` (operands), `x2_low4.bin`, `y2_low4.bin` (results) |
| **W3** CRT recombination + materialization of `(x, y)` | `ibz_crt … quat_xyn_to_inert_ideal` | `TVLA_TRIG_STOREREGION` | `firmware/intersect_target_rk.c` | `out_x_low4.bin`, `out_y_low4.bin` |

All labels are the low 4 bytes (little-endian magnitude) of the named quantity
per input record; the analysis uses byte 0.

## Files

```
firmware/
  tvla_gauss_target.c   W1: receives the two Gaussian-multiply operands (host-computed, radix independent)
                        and runs only ibz_vec_2_gaussian_mul between trigger_high/low
  intersect_target_rk.c W2/W3: receives b, runs the full quat_ideal_intersect_O0 with a_fixed/split_fixed;
                        the trigger is inside ideal.c (TVLA_TRIG_OUTREGION or TVLA_TRIG_STOREREGION)
host/
  tvla_gen_rk.c         generates fixed_as.h and the 21,000-record secret stream tvla_inputs_rk.bin
                        (3,000 fixed = class 0, 18,000 random = class 1), classes, reference CRCs
  gauss_host.c          runs Intersect on the host with the TVLA_DUMP_GAUSS hook: W1 operand records
                        (gauss_inputs_rk.bin) + label gauss_bx0_rk.bin
  outlabel_host.c       runs Intersect with TVLA_DUMP_OUT/TVLA_DUMP_STORE: W2 and W3 labels
  gauss_verify.c        emulates the W1 firmware; built at RADIX_32 and RADIX_16 the CRCs agree
  build_host.sh         gcc build of the above (needs ../../common/firmware/sqisign, see get_sqisign.sh)
data/                   the inputs and labels actually used (regenerable byte-for-byte, see root README)
analysis/
  recovery_ge.py                 Fig. 2 / Table 4: value-SNR and LOVO guessing entropy of b.x byte 0 at W1
  operand_vs_result_control.py   W2: operands x_pre, t leak their value, the reduced result X2 does not
  output_null_test.py            W3: materialized x, y vs label-permutation null
  make_pgf_figure.py             results/sec521_numbers.json -> results/fig_exp_intersection.tex (no traces needed)
results/
  sec521_numbers.json            GE(N), N = 1..40, value-SNR, N*, for the three builds of Table 4
  fig_exp_intersection.{tex,pdf,png}, listing_intersection.tex
```

## Firmware variants (from `common/firmware`)

| Trace set (analysis name) | TARGET | TVLA_TARGET_SRC | TVLA_DEFS | RADIX | OPT | samples |
|---|---|---|---|---|---|---|
| `traces_r16gauss.npz` (16-bit, -Os) | `sqisign-gauss-r16` | `tvla_gauss_target.c` | (none) | `RADIX_16` | default (-Os) | 5000 |
| `traces_o0r16.npz` (16-bit, -O0) | `gauss-r16-o0` | `tvla_gauss_target.c` | (none) | `RADIX_16` | `OPT=0` | 8000 |
| `traces_o0r32.npz` (32-bit, -O0) | `gauss-r32-o0` | `tvla_gauss_target.c` | (none) | `RADIX_32` | `OPT=0` | 8000 |
| `traces_x2full.npz` (W2 scan, -Os) | `sqisign-out-r32` | `intersect_target_rk.c` | `-DTVLA_TRIG_OUTREGION` | `RADIX_32` | default | 5000 × decimate 16 |
| `traces_outos.npz`, `traces_outo0.npz` (W3) | `sqisign-out-r32[-o0]` | `intersect_target_rk.c` | `-DTVLA_TRIG_STOREREGION` | `RADIX_32` | default / `OPT=0` | 5000 |

The W1 firmware is fed `gauss_inputs_rk.bin`; the W2/W3 firmware is fed
`tvla_inputs_rk.bin`. The 21,000-trace sets were acquired with
`common/host/capture_chunked.py` (`--adc-x 4 --gain 30`) and merged with
`concat_parts.py`; the W2 scan used `capture_single.py --decimate 16`
(2,500 traces).

The 16-bit-limb firmware needs patch `0002` (RADIX_16 types and constants)
only: the isolated multiply uses `ibz_mul`/`ibz_add`/`ibz_sub`, none of the
routines changed by patch `0003`. Patch `0003` (radix-portable division and
modular inverse) is needed to run the *full* Intersect or the serialization
helpers at RADIX_16 on the host (`gauss_verify16`); with it the RADIX_16 and
RADIX_32 Gaussian products agree record for record.

## Running the analysis

```bash
export SQI_DATA=/path/to/dir/with/labels/and/traces   # default: ./data
python analysis/recovery_ge.py                         # -> results/sec521_numbers.json, fig_exp_intersection.{pdf,png}
python analysis/make_pgf_figure.py                     # -> results/fig_exp_intersection.tex
python analysis/operand_vs_result_control.py           # needs traces_x2full.npz
python analysis/output_null_test.py                    # needs traces_outos.npz, traces_outo0.npz
```
