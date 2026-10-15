#!/usr/bin/env python3
"""Chunked, USB-resilient capture. Captures records in chunks, saving each chunk
to its own npz immediately (so a mid-run USB error never loses prior work), and
on a USB error reconnects the scope and retries the current chunk. Each saved
part carries global record indices (kept_idx) for label alignment."""
import argparse, struct, time, sys
import numpy as np
import chipwhisperer as cw

def read_inputs(path):
    with open(path,"rb") as f:
        magic,N=struct.unpack("<II",f.read(8)); struct.unpack("<H",f.read(2))
        if magic!=0x54564C41: raise SystemExit("bad magic")
        cls=np.empty(N,np.uint8); recs=[]
        for i in range(N):
            cls[i]=f.read(1)[0]; rl,=struct.unpack("<H",f.read(2)); recs.append(f.read(rl))
    return cls,recs

def connect(args):
    scope=cw.scope(); scope.default_setup()
    scope.clock.clkgen_freq=args.freq
    scope.clock.adc_src="clkgen_x4" if args.adc_x==4 else "clkgen_x1"
    scope.adc.samples=args.samples; scope.adc.offset=args.offset
    if args.gain is not None: scope.gain.db=args.gain
    try: scope.adc.timeout=args.cap_timeout
    except Exception: pass
    target=cw.target(scope,cw.targets.SimpleSerial2)
    return scope,target

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--inputs",required=True); ap.add_argument("--hex",default=None)
    ap.add_argument("--outprefix",default="part"); ap.add_argument("--samples",type=int,default=5000)
    ap.add_argument("--offset",type=int,default=0); ap.add_argument("--adc-x",type=int,default=4)
    ap.add_argument("--freq",type=int,default=7370000); ap.add_argument("--gain",type=int,default=30)
    ap.add_argument("--settle",type=float,default=0.12); ap.add_argument("--cap-timeout",type=float,default=3.0)
    ap.add_argument("--chunk",type=int,default=3000); ap.add_argument("--start",type=int,default=0)
    ap.add_argument("--limit",type=int,default=0); ap.add_argument("--retries",type=int,default=4)
    args=ap.parse_args()

    cls,recs=read_inputs(args.inputs); N=len(recs)
    end=N if args.limit==0 else min(N,args.start+args.limit)
    scope,target=connect(args)
    if args.hex:
        print("flashing",args.hex,flush=True)
        cw.program_target(scope,cw.programmers.STM32FProgrammer,args.hex); time.sleep(0.3)

    def cap_one(rec):
        scope.arm(); target.simpleserial_write('p',bytearray(rec))
        if scope.capture(): return None
        w=scope.get_last_trace(); time.sleep(args.settle)
        try: target.flush()
        except Exception: pass
        return w

    t0=time.time(); done=0
    cs=args.start
    while cs<end:
        ce=min(cs+args.chunk,end)
        n=ce-cs
        buf=np.empty((n,args.samples),np.float32); good=np.ones(n,bool)
        attempt=0
        i=0
        while i<n:
            try:
                w=cap_one(recs[cs+i])
                if w is None: good[i]=False
                else: buf[i]=w[:args.samples]
                i+=1; done+=1
                if done%200==0:
                    print("  %d/%d  %.1f tr/s  chunk[%d:%d]"%(done,end-args.start,done/(time.time()-t0),cs,ce),flush=True)
            except Exception as e:
                attempt+=1
                print("  USB/err at rec %d (attempt %d): %r -> reconnect"%(cs+i,attempt,e),flush=True)
                try: scope.dis(); target.dis()
                except Exception: pass
                time.sleep(2.0)
                if attempt>args.retries:
                    print("  chunk[%d:%d] giving up after %d retries; saving partial"%(cs,ce,attempt),flush=True)
                    break
                try:
                    scope,target=connect(args)   # no reflash; firmware persists
                except Exception as e2:
                    print("  reconnect failed: %r; sleep+retry"%e2,flush=True); time.sleep(3.0)
                # continue from same i (retry this record)
        idx=np.arange(cs,cs+i)[good[:i]]
        out="../%s_%05d.npz"%(args.outprefix,cs)
        np.savez_compressed(out,traces=buf[:i][good[:i]],classes=cls[cs:cs+i][good[:i]],
                            kept_idx=idx,samples=args.samples)
        print("SAVED %s rows=%d (chunk %d:%d, dropped %d)"%(out,int(good[:i].sum()),cs,ce,int((~good[:i]).sum())),flush=True)
        cs=ce
    try: scope.dis(); target.dis()
    except Exception: pass
    print("ALLCHUNKS done=%d"%done,flush=True)

if __name__=="__main__": main()
