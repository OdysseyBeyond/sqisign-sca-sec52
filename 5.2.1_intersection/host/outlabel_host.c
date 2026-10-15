/* outlabel_host.c - host (RADIX_32) label generator for the two Intersect
 * windows after the Gaussian multiply. For each record of tvla_inputs_rk.bin it
 * runs quat_ideal_intersect_O0(a_fixed, b, split_fixed) with the dump hooks of
 * ideal.c (-DTVLA_DUMP_OUT -DTVLA_DUMP_STORE) enabled and writes, per record,
 * the low 4 bytes (little-endian magnitude) of
 *   W2 (coordinate-forming multiplies, TVLA_TRIG_OUTREGION):
 *     x2_xpre_low4.bin  x_pre = tmp.v[0]/2          (multiplicand)
 *     x2_t_low4.bin     t = (u^2+v^2)^-1 mod N2      (multiplicand)
 *     x2_low4.bin       X2 = x_pre * t mod N2        (result)
 *     y2_low4.bin       Y2                           (result)
 *   W3 (CRT recombination + materialization, TVLA_TRIG_STOREREGION):
 *     out_x_low4.bin    x of the inert representation of I_sk,chl
 *     out_y_low4.bin    y
 * Build: see build_host.sh. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "tvla_io.h"
#include "tvla_core_rk.h"
#include "fixed_as.h"

static uint8_t g_x[4], g_y[4], g_px[4], g_pt[4], g_sx[4], g_sy[4];
static int g_got = 0, g_gots = 0;

static void low4(uint8_t *dst, const ibz_t *v) {
    ibz_t a; ibz_init(&a); ibz_abs(&a, v);
    digit_t tmp[IBZ_NLIMBS]; memset(tmp, 0, sizeof(tmp));
    if (!ibz_is_zero(&a)) ibz_to_digits(tmp, &a);
    memcpy(dst, (uint8_t *)tmp, 4);
}
void tvla_dump_pre(const ibz_t *xpre, const ibz_t *t) { low4(g_px, xpre); low4(g_pt, t); }
void tvla_dump_out(const ibz_t *x, const ibz_t *y, const ibz_t *n) { (void)n; low4(g_x, x); low4(g_y, y); g_got = 1; }
void tvla_dump_store(const ibz_t *x, const ibz_t *y, const ibz_t *n) { (void)n; low4(g_sx, x); low4(g_sy, y); g_gots = 1; }

int main(int argc, char **argv) {
    const char *inp = (argc > 1) ? argv[1] : "tvla_inputs_rk.bin";
    tvla_load_fixed(FIXED_AS);
    FILE *f = fopen(inp, "rb"); if (!f) { fprintf(stderr, "no inputs %s\n", inp); return 2; }
    uint32_t magic, N; uint16_t rm;
    if (fread(&magic, 4, 1, f) != 1 || fread(&N, 4, 1, f) != 1 || fread(&rm, 2, 1, f) != 1) return 3;
    FILE *fx = fopen("x2_low4.bin", "wb"), *fy = fopen("y2_low4.bin", "wb");
    FILE *fpx = fopen("x2_xpre_low4.bin", "wb"), *fpt = fopen("x2_t_low4.bin", "wb");
    FILE *fsx = fopen("out_x_low4.bin", "wb"), *fsy = fopen("out_y_low4.bin", "wb");
    uint8_t rec[600]; uint32_t i;
    for (i = 0; i < N; i++) {
        int cls = fgetc(f); uint16_t rl = 0; (void)cls;
        if (fread(&rl, 2, 1, f) != 1) break;
        if (fread(rec, 1, rl, f) != rl) break;
        tvla_set_secret(rec); g_got = g_gots = 0;
        quat_ideal_intersect_O0(&g_out, &g_a, &g_b, &g_split);
        if (!g_got || !g_gots) { fprintf(stderr, "rec %u: hooks not fired (out=%d store=%d)\n", i, g_got, g_gots); return 6; }
        fwrite(g_x, 1, 4, fx); fwrite(g_y, 1, 4, fy); fwrite(g_px, 1, 4, fpx); fwrite(g_pt, 1, 4, fpt);
        fwrite(g_sx, 1, 4, fsx); fwrite(g_sy, 1, 4, fsy);
    }
    fclose(f); fclose(fx); fclose(fy); fclose(fpx); fclose(fpt); fclose(fsx); fclose(fsy);
    fprintf(stderr, "wrote %u records\n", i);
    return 0;
}
