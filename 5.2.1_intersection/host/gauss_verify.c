/* gauss_verify.c - emulate the firmware: read gauss_inputs record, deserialize
 * the 4 operands, run ibz_vec_2_gaussian_mul, print crc of the serialized result
 * (b.v0||b.v1). Build at R16 and R32; results must match (R16 multiply correct),
 * confirming the firmware computes the same b the real intersect does. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "tvla_io.h"
#include <quaternion.h>
int main(int argc,char**argv){
    long which=(argc>1)?atol(argv[1]):0;
    FILE*f=fopen("gauss_inputs_rk.bin","rb"); if(!f){return 2;}
    uint32_t magic,N; fread(&magic,4,1,f); fread(&N,4,1,f);
    uint16_t rm; fread(&rm,2,1,f);
    uint8_t rec[600]; int cls=0; uint16_t rl=0;
    for(long i=0;i<=which;i++){ cls=fgetc(f); if(fread(&rl,2,1,f)!=1)return 4; if(fread(rec,1,rl,f)!=rl)return 5; }
    ibz_vec_2_t setter,tmp; ibz_vec_2_init(&setter); ibz_vec_2_init(&tmp);
    const uint8_t*p=rec;
    tvla_de_ibz(&p,&setter.v[0]); tvla_de_ibz(&p,&setter.v[1]);
    tvla_de_ibz(&p,&tmp.v[0]);    tvla_de_ibz(&p,&tmp.v[1]);
    ibz_vec_2_gaussian_mul(&tmp,&setter,&tmp);
    static uint8_t ob[1024]; int o=0;
    o+=tvla_ser_ibz(ob+o,&tmp.v[0]); o+=tvla_ser_ibz(ob+o,&tmp.v[1]);
    printf("rec=%ld rl=%u b.v0.low=%02x crc=%08x\n",which,rl,ob[3],tvla_crc32(ob,o));
    return 0;
}
