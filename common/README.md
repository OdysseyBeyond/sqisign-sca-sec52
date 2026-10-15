# common — firmware project, SQIsign patches, capture scripts

## firmware/

ChipWhisperer SimpleSerial-2.1 project shared by both experiments.

* `get_sqisign.sh` clones `github.com/SQIsign/the-sqisign` at commit `6d01770`
  (branch `nist-v3`, the Round-3 reference implementation), copies the files listed in
  `sqisign_files.lst` (the quaternion and multiprecision layer that `quat_ideal_intersect_O0`
  and `quat_ideal_create_O0_inert_odd` need, variant `p324_3`) into `sqisign/{src,inc}`
  and applies the patches below. Run it before building anything.
* `patches/`
  * `0001-tvla-trigger-and-dump-hooks.patch` — `ideal.c` only. Adds, under `#ifdef`,
    GPIO trigger pairs around the four traced regions (`TVLA_TRIG_VALUEREGION` W1,
    `TVLA_TRIG_OUTREGION` W2, `TVLA_TRIG_STOREREGION` W3 in `quat_ideal_intersect_O0`;
    `TVLA_TRIG_EQUIVREGION` in `quat_ideal_create_O0_inert_odd`) and the host-side
    label-dump callbacks (`TVLA_DUMP_GAUSS`, `TVLA_DUMP_OUT`, `TVLA_DUMP_STORE`,
    `TVLA_DUMP_EQUIV`). With none of the macros defined the file compiles to the
    unmodified reference code.
  * `0002-radix8-radix16-build-support.patch` — `tutil.h`, `modqx.h`, `encoded_sizes.h`,
    `primality_test.h`, `quaternion_data.c`: digit types and precomputed constants for
    `RADIX_16` (and `RADIX_8`), so the library can be compiled with 16-bit limbs.
  * `0003-radix16-portable-division-and-invmod.patch` — `mp.c`: routes
    `mp_div_unsigned` through the schoolbook division, replaces the Lehmer
    `ibz_invmod` by a plain extended Euclid kept in `[0, mod)`, and fixes a digit-count
    helper that truncates at narrow radices. Needed only to run the *full* Intersect
    (host verification, `gauss_verify16`) at `RADIX_16`; the 16-bit firmware of 5.2.1
    measures the isolated Gaussian multiply, which does not call these routines, and
    all 32-bit builds use the unmodified `mp.c`.
* `Makefile` — variables `TARGET`, `TVLA_TARGET_SRC` (harness `.c` from
  `../../5.2.x/firmware`), `TVLA_DEFS` (trigger/dump macros), `RADIX` (`RADIX_32` /
  `RADIX_16`), `OPT=0` for the -O0 builds, `CWFIRMWARE` (path to
  `chipwhisperer/firmware/mcu`, default `../../..`). The variant tables are in the
  experiment READMEs.
* `tvla_io.h` — wire format of a serialized `ibz_t` (`u8 sign, u16 len, mag[len]`
  little-endian) and of one record; `TVLA_MAX_REC = 512`.
* `tvla_core_rk.h` — holds the fixed operands and the streamed secret `b`; the traced
  call is `quat_ideal_intersect_O0(out, a_fixed, b, split_fixed)`.
* `fixed_as.h` — the fixed `(a, split_a)` used by every capture (output of
  `5.2.1_intersection/host/tvla_gen_rk`, also linked into the host generators).
* `host_rng.c` — deterministic xoshiro-style PRNG behind `randombytes_init` /
  `prng_random_bytes` for the host builds (ideal validity comes from the generators'
  rejection loops, so reproducibility matters more than quality here).

## host/

* `capture_chunked.py` — the capture used for all 21,000-trace sets. Streams each
  record over SimpleSerial 2.1, arms the CW-Lite, records the trace between the
  trigger edges and writes 3,000-trace parts `<prefix>_<start>.npz` with `kept_idx`
  (global record indices) for label alignment; reconnects on USB errors and retries
  the current chunk. Options: `--samples`, `--offset`, `--adc-x {1,4}`, `--gain`,
  `--settle` (seconds between traces; 0.45 for the primality target), `--start/--limit`.
* `capture_single.py` — single-file capture with `--decimate N` and
  `--segments K --seg-step S` (deterministic re-run at stepped offsets) for the
  whole-region scans; `--probe N` reports the trigger-high length in ADC samples.
* `concat_parts.py <prefix>` — merges the parts of one run into `<prefix>.npz`
  sorted by `kept_idx`.

Scope settings common to all captures: `clkgen_freq = 7.37 MHz`,
`adc_src = clkgen_x4`, `gain.db ≈ 24.8` (gain 30), trigger `rising_edge` on the
target GPIO, `scope.default_setup()` otherwise.
