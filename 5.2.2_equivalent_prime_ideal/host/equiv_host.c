/* equiv_host.c - host (R32) generator for the 5.2.2 experiment.
 * For each record of tvla_inputs_rk.bin (class byte + secret ideal b):
 *   I = Intersect(a_fixed, b, split_fixed);  (gen, J_t) = EquivalentCoprimeIdeal(I, prime)
 * with a PRNG re-seeded from the record bytes (so the fixed class is deterministic).
 * Hooks placed inside quat_ideal_create_O0_inert_odd (ideal.c, -DTVLA_DUMP_EQUIV) record
 *   - the function's exact input (gen coords, denom, norm)  -> device record (tvla_inputs_equiv.bin)
 *   - the (a,b,c,d), s, t at the Gaussian multiply          -> labels equiv_abcd_low4.bin, equiv_s_low4.bin, equiv_t_low4.bin
 *   - the output (x,y) and n                                -> labels equiv_x_low4.bin, equiv_y_low4.bin, equiv_n_low4.bin
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <quaternion.h>
#include <prng.h>
#include "tvla_io.h"
#include "tvla_core_rk.h"
#include "fixed_as.h"

void randombytes_init(unsigned char *entropy, unsigned char *perso, int strength);

static uint8_t g_rec[TVLA_MAX_REC]; static int g_rl = 0, g_in = 0, g_gen = 0, g_outd = 0;
static uint8_t g_abcd[16], g_s[4], g_t[4], g_x[4], g_y[4], g_n[4];
static int g_maxrl = 0;

static void low4(uint8_t *dst, const ibz_t *v) {
    ibz_t a; ibz_init(&a); ibz_abs(&a, v);
    digit_t tmp[IBZ_NLIMBS]; memset(tmp, 0, sizeof(tmp));
    if (!ibz_is_zero(&a)) ibz_to_digits(tmp, &a);
    memcpy(dst, (uint8_t *)tmp, 4);
}
void tvla_dump_equiv_in(const quat_alg_elem_t *gen, const ibz_t *n) {
    int o = 0;
    for (int i = 0; i < 4; i++) o += tvla_ser_ibz(g_rec + o, &gen->coord.v[i]);
    o += tvla_ser_ibz(g_rec + o, &gen->denom);
    o += tvla_ser_ibz(g_rec + o, n);
    g_rl = o; g_in = 1; if (o > g_maxrl) g_maxrl = o;
}
void tvla_dump_equiv_gen(const quat_alg_elem_t *g, const ibz_t *s, const ibz_t *t, const ibz_t *n) {
    (void)n; for (int i = 0; i < 4; i++) low4(g_abcd + 4 * i, &g->coord.v[i]);
    low4(g_s, s); low4(g_t, t); g_gen = 1;
}
void tvla_dump_equiv_out(const ibz_t *x, const ibz_t *y, const ibz_t *n) {
    low4(g_x, x); low4(g_y, y); low4(g_n, n); g_outd = 1;
}

int main(int argc, char **argv) {
    const char *inp = (argc > 1) ? argv[1] : "tvla_inputs_rk.bin";
    const char *outp = (argc > 2) ? argv[2] : "tvla_inputs_equiv.bin";
    uint32_t limit = (argc > 3) ? (uint32_t)atoi(argv[3]) : 0;
    tvla_load_fixed(FIXED_AS);
    FILE *f = fopen(inp, "rb"); if (!f) { fprintf(stderr, "no inputs\n"); return 2; }
    uint32_t magic, N; uint16_t rm;
    if (fread(&magic, 4, 1, f) != 1 || fread(&N, 4, 1, f) != 1 || fread(&rm, 2, 1, f) != 1) return 3;
    if (limit && limit < N) N = limit;
    FILE *fo = fopen(outp, "wb");
    fwrite(&magic, 4, 1, fo); fwrite(&N, 4, 1, fo); fwrite(&rm, 2, 1, fo);
    FILE *fa = fopen("equiv_abcd_low4.bin", "wb"), *fs = fopen("equiv_s_low4.bin", "wb"), *ft = fopen("equiv_t_low4.bin", "wb");
    FILE *fx = fopen("equiv_x_low4.bin", "wb"), *fy = fopen("equiv_y_low4.bin", "wb"), *fn = fopen("equiv_n_low4.bin", "wb");
    FILE *fc = fopen("equiv_classes.bin", "wb");
    uint8_t rec[600]; uint32_t i; int maxbits_n = 0;
    quat_alg_elem_t gen; quat_ideal_t equiv; ibz_t zero;
    quat_alg_elem_init(&gen); quat_ideal_init(&equiv); ibz_init(&zero);
    for (i = 0; i < N; i++) {
        int cls = fgetc(f); uint16_t rl = 0;
        if (fread(&rl, 2, 1, f) != 1) break;
        if (fread(rec, 1, rl, f) != rl) break;
        tvla_set_secret(rec);
        /* deterministic per-record seed: fixed records (identical bytes) get identical gamma */
        uint32_t c1 = tvla_crc32(rec, rl), c2 = tvla_crc32(rec + 1, rl - 1) ^ 0xA5A5A5A5u;
        unsigned char ent[8]; memcpy(ent, &c1, 4); memcpy(ent + 4, &c2, 4);
        randombytes_init(ent, NULL, 256);
        quat_ideal_intersect_O0(&g_out, &g_a, &g_b, &g_split);
        g_in = g_gen = g_outd = 0;
        int ok = quat_ideal_small_equivalent_coprime(&gen, &equiv, &g_out, &zero, &PRNG_default_domain);
        if (!ok || !g_in || !g_gen || !g_outd) { fprintf(stderr, "rec %u: ok=%d in=%d gen=%d out=%d\n", i, ok, g_in, g_gen, g_outd); return 6; }
        int nb = ibz_bitsize(&equiv.norm); if (nb > maxbits_n) maxbits_n = nb;
        fputc(cls, fo); uint16_t orl = (uint16_t)g_rl; fwrite(&orl, 2, 1, fo); fwrite(g_rec, 1, g_rl, fo);
        fwrite(g_abcd, 1, 16, fa); fwrite(g_s, 1, 4, fs); fwrite(g_t, 1, 4, ft);
        fwrite(g_x, 1, 4, fx); fwrite(g_y, 1, 4, fy); fwrite(g_n, 1, 4, fn); fputc(cls, fc);
        if ((i + 1) % 1000 == 0) fprintf(stderr, "  %u/%u  (max rec %d B, max n %d bits)\n", i + 1, N, g_maxrl, maxbits_n);
    }
    fclose(f); fclose(fo); fclose(fa); fclose(fs); fclose(ft); fclose(fx); fclose(fy); fclose(fn); fclose(fc);
    fprintf(stderr, "wrote %u records; max device record %d bytes; max n(J_t) %d bits\n", i, g_maxrl, maxbits_n);
    return 0;
}
