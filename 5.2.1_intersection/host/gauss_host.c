/* gauss_host.c - R32 host harness: for each input record, run the intersect
 * (which fires the TVLA_DUMP_GAUSS hook just before the measured gaussian_mul)
 * and dump its two operands (setter.v0,v1, tmp.v0,v1). Also record b.x low byte.
 * Output: a TVLA container of gaussian-mul operand records + a byte0 label file.
 * Values are radix-independent, so R32 (correct) feeds the RADIX_16 firmware. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "tvla_io.h"
#include "tvla_core_rk.h"
#include "fixed_as.h"

static uint8_t g_dumpbuf[2048];
static int g_dumplen = 0;

void tvla_dump_gauss(const ibz_vec_2_t *setter, const ibz_vec_2_t *tmp){
    int o = 0;
    o += tvla_ser_ibz(g_dumpbuf + o, &setter->v[0]);
    o += tvla_ser_ibz(g_dumpbuf + o, &setter->v[1]);
    o += tvla_ser_ibz(g_dumpbuf + o, &tmp->v[0]);
    o += tvla_ser_ibz(g_dumpbuf + o, &tmp->v[1]);
    g_dumplen = o;
}

int main(int argc, char**argv){
    const char*inp = (argc>1)?argv[1]:"tvla_inputs_rk.bin";
    const char*out = (argc>2)?argv[2]:"gauss_inputs_rk.bin";
    const char*lab = (argc>3)?argv[3]:"gauss_bx0_rk.bin";
    tvla_load_fixed(FIXED_AS);
    FILE*f=fopen(inp,"rb"); if(!f){fprintf(stderr,"no inputs %s\n",inp);return 2;}
    uint32_t magic,N; if(fread(&magic,4,1,f)!=1||fread(&N,4,1,f)!=1)return 3;
    uint16_t rm; fread(&rm,2,1,f);
    FILE*fo=fopen(out,"wb"); FILE*fl=fopen(lab,"wb");
    fwrite(&magic,4,1,fo); fwrite(&N,4,1,fo); fwrite(&rm,2,1,fo);
    uint8_t rec[600]; int maxrec=0; uint32_t i;
    for(i=0;i<N;i++){
        int cls=fgetc(f); uint16_t rl=0;
        if(fread(&rl,2,1,f)!=1) break;
        if(fread(rec,1,rl,f)!=rl) break;
        tvla_set_secret(rec);
        g_dumplen=0;
        quat_ideal_intersect_O0(&g_out, &g_a, &g_b, &g_split);  /* fires dump hook */
        if(g_dumplen==0){ fprintf(stderr,"rec %u: hook not fired!\n",i); return 6; }
        uint8_t bx0 = (uint8_t)(g_b.x.limbs[0] & 0xff);
        fwrite(&bx0,1,1,fl);
        uint8_t c=(uint8_t)cls; uint16_t ol=(uint16_t)g_dumplen;
        fwrite(&c,1,1,fo); fwrite(&ol,2,1,fo); fwrite(g_dumpbuf,1,ol,fo);
        if(g_dumplen>maxrec)maxrec=g_dumplen;
    }
    fclose(f);fclose(fo);fclose(fl);
    fprintf(stderr,"wrote %u records, maxrec=%d bytes\n",i,maxrec);
    return 0;
}
