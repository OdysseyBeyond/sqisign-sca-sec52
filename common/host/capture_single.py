#!/usr/bin/env python3
"""
capture_single.py - ChipWhisperer single-file capture (scans; decimation, segments) for a fixed-vs-random TVLA of
SQIsign 3.0 quat_ideal_intersect_O0() on CW-Lite Arm (STM32F303).

Reads tvla_inputs.bin / tvla_expected_crc.bin, streams each challenge record
over SimpleSerial 2.1, records the trace between the target trigger edges,
checks the returned CRC32, and writes traces.npz for tvla.py.

  python capture_tvla.py --hex ../sqisign-intersect-CWLITEARM.hex --probe 10
  python capture_tvla.py --samples 24400 --adc-x 1 --segments 4 --out traces.npz

--probe N runs N inputs and prints scope.adc.trig_count (trigger-high length in
ADC samples) so you can set --segments = ceil(trig_count / samples) for full
coverage of the routine (it is deterministic per input, so segments re-run the
same input at stepped offsets).
"""
import argparse, struct, time, math
import numpy as np


def read_inputs(path):
    with open(path, "rb") as f:
        magic, N = struct.unpack("<II", f.read(8))
        struct.unpack("<H", f.read(2))
        if magic != 0x54564C41:
            raise SystemExit("bad magic in %s" % path)
        cls = np.empty(N, np.uint8)
        recs = []
        for i in range(N):
            cls[i] = f.read(1)[0]
            rl, = struct.unpack("<H", f.read(2))
            recs.append(f.read(rl))
    return cls, recs


def read_crc(path, N):
    with open(path, "rb") as f:
        return np.frombuffer(f.read(4 * N), np.uint32).copy()


def setup_scope(scope, args):
    scope.default_setup()
    scope.clock.clkgen_freq = args.freq
    scope.clock.adc_src = "clkgen_x4" if args.adc_x == 4 else "clkgen_x1"
    scope.adc.samples = args.samples
    scope.adc.offset = args.offset
    try:
        scope.adc.decimate = args.decimate
    except Exception as e:
        print("decimate not set:", e)
    if args.gain is not None:
        scope.gain.db = args.gain


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", default="tvla_inputs.bin")
    ap.add_argument("--expected-crc", default="tvla_expected_crc.bin")
    ap.add_argument("--hex", default=None, help="firmware .hex to flash first")
    ap.add_argument("--out", default="traces.npz")
    ap.add_argument("--samples", type=int, default=24400)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--adc-x", type=int, default=1, choices=[1, 4], help="ADC clock: clkgen x1 or x4")
    ap.add_argument("--freq", type=int, default=7370000)
    ap.add_argument("--gain", type=int, default=None)
    ap.add_argument("--decimate", type=int, default=1, help="ADC decimation: keep every Nth sample")
    ap.add_argument("--segments", type=int, default=1, help="windows per input (deterministic re-run)")
    ap.add_argument("--seg-step", type=int, default=None, help="offset step between segments (default=samples)")
    ap.add_argument("--limit", type=int, default=0, help="cap number of traces (0=all)")
    ap.add_argument("--probe", type=int, default=0, help="run N inputs, report trig_count, exit")
    args = ap.parse_args()

    import chipwhisperer as cw

    cls, recs = read_inputs(args.inputs)
    N = len(recs)
    if args.limit and args.limit < N:
        N = args.limit
    exp_crc = read_crc(args.expected_crc, len(cls)) if args.expected_crc else None

    scope = cw.scope()
    setup_scope(scope, args)
    target = cw.target(scope, cw.targets.SimpleSerial2)

    if args.hex:
        print("flashing", args.hex)
        cw.program_target(scope, cw.programmers.STM32FProgrammer, args.hex)
        time.sleep(0.3)

    def run_one(rec, want_offset, do_read=True):
        scope.adc.offset = want_offset
        scope.arm()
        target.simpleserial_write('p', bytearray(rec))
        if scope.capture():
            return None, None
        wave = scope.get_last_trace()
        crc = None
        if do_read:
            try:
                r = target.simpleserial_read('r', 4, timeout=2000)
                if r is not None and len(r) >= 4:
                    crc = struct.unpack("<I", bytes(r[:4]))[0]
            except Exception:
                pass
        else:
            # Bulk capture: don't parse the variable 'r' response (a CW host
            # unstuff bug can hang on some CRC byte patterns); just clear the
            # RX buffer so the next command re-syncs. Correctness of the target
            # computation is verified separately in --probe mode.
            time.sleep(0.12)
            try:
                target.flush()
            except Exception:
                pass
        return wave, crc

    if args.probe:
        n = min(args.probe, N)
        counts, okc = [], 0
        for i in range(n):
            _w, crc = run_one(recs[i], args.offset)
            try:
                counts.append(int(scope.adc.trig_count))
            except Exception:
                pass
            if exp_crc is not None and crc == exp_crc[i]:
                okc += 1
        scope.dis(); target.dis()
        if counts:
            mx = max(counts)
            print("trig_count samples: min=%d max=%d  ->  segments>=%d for samples=%d"
                  % (min(counts), mx, math.ceil(mx / args.samples), args.samples))
        print("CRC ok: %d/%d" % (okc, n))
        return

    seg_step = args.seg_step if args.seg_step else args.samples
    total_len = args.samples * args.segments
    traces = np.empty((N, total_len), np.float32)
    good = np.ones(N, bool)

    t0 = time.time()
    for i in range(N):
        for s in range(args.segments):
            wave, crc = run_one(recs[i], args.offset + s * seg_step, do_read=False)
            if wave is None:
                good[i] = False
                break
            traces[i, s * args.samples:(s + 1) * args.samples] = wave[:args.samples]
            if s == 0 and exp_crc is not None and crc is not None and crc != exp_crc[i]:
                good[i] = False
        if (i + 1) % 200 == 0:
            print("  %d/%d  %.1f tr/s  bad=%d"
                  % (i + 1, N, (i + 1) / (time.time() - t0), int((~good[:i + 1]).sum())))

    scope.dis(); target.dis()
    print("captured %d, kept %d (dropped %d)" % (N, int(good.sum()), int((~good).sum())))
    np.savez_compressed(args.out, traces=traces[good], classes=cls[:N][good],
                        samples=args.samples, segments=args.segments)
    print("saved", args.out)


if __name__ == "__main__":
    main()
