/* tvla_gen_rk.c - random-SECRET TVLA input generator for quat_ideal_intersect_O0.
 *
 * Directly probes secret-dependence: the public operands a, split are FIXED
 * (compiled into the target); the SECRET ideal b is toggled between classes.
 *   class 0 (fixed)  : b = b0            (one fixed secret)
 *   class 1 (random) : b = fresh random  (coprime to n(a), n(split))
 * A leak here means the trace distribution depends on the secret b itself.
 *
 * Emits:
 *   fixed_as.h            a_fixed (x,y,norm) + split_fixed (v0,v1) for the target
 *   tvla_inputs_rk.bin    records = serialized (b.x,b.y,b.norm)
 *   tvla_expected_crc_rk.bin, tvla_classes_rk.bin
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <quaternion.h>
#include <mp.h>
#include <prng.h>
#include <rng.h>
#include "tvla_io.h"

#define NORM_BITS 160
#define PD (&PRNG_default_domain)

static void gen_ideal_coprime(quat_ideal_t *out, const ibz_t *avoid)
{
    ibz_t p, g; ibz_init(&p); ibz_init(&g);
    for (;;) {
        ibz_generate_random_prime(&p, 0, NORM_BITS);
        if (!quat_random_ideal_O0_given_prime_norm(out, &p, PD)) continue;
        if (avoid) { ibz_gcd(&g, &out->norm, avoid); if (!ibz_is_one(&g)) continue; }
        return;
    }
}

/* split fixed (u,v) small; require gcd(u^2+v^2, n(b))==1 for the given b. */
static int split_ok(const quat_alg_elem_t *split, const ibz_t *bnorm)
{
    ibz_t u2, v2, s, g; ibz_init(&u2); ibz_init(&v2); ibz_init(&s); ibz_init(&g);
    ibz_mul(&u2, &split->coord.v[0], &split->coord.v[0]);
    ibz_mul(&v2, &split->coord.v[1], &split->coord.v[1]);
    ibz_add(&s, &u2, &v2); ibz_gcd(&g, &s, bnorm);
    return ibz_is_one(&g);
}

static int ser_b(uint8_t *buf, const quat_ideal_t *b)
{
    int o = 0;
    o += tvla_ser_ibz(buf + o, &b->x);
    o += tvla_ser_ibz(buf + o, &b->y);
    o += tvla_ser_ibz(buf + o, &b->norm);
    return o;
}

int main(int argc, char **argv)
{
    long N = (argc > 1) ? atol(argv[1]) : 5000;
    unsigned gseed = (argc > 2) ? (unsigned)atol(argv[2]) : 7;

    uint32_t seed[12];
    for (int i = 0; i < 12; i++) seed[i] = 0x5A5A0000u + gseed * 131u + i;
    randombytes_init((unsigned char *)seed, NULL, 256);
    if (prng_seed() != 0) { fprintf(stderr, "prng_seed failed\n"); return 1; }
    srand(gseed);

    quat_ideal_t a_fixed, b0, b_rand, out;
    quat_alg_elem_t split_fixed;
    quat_ideal_init(&a_fixed); quat_ideal_init(&b0); quat_ideal_init(&b_rand); quat_ideal_init(&out);
    quat_alg_elem_init(&split_fixed);

    gen_ideal_coprime(&a_fixed, NULL);
    /* fixed small split with u=2,v=1 (as in the reference test) */
    quat_alg_elem_set(&split_fixed, 1, 2, 1, 0, 0);
    /* fixed secret b0, coprime to a and valid for the fixed split */
    do { gen_ideal_coprime(&b0, &a_fixed.norm); } while (!split_ok(&split_fixed, &b0.norm));

    /* fixed_as.h : a_fixed (x,y,norm) then split (v0,v1) */
    {
        uint8_t sb[6 * (3 + IBZ_NLIMBS * sizeof(digit_t))]; int n = 0;
        n += tvla_ser_ibz(sb + n, &a_fixed.x);
        n += tvla_ser_ibz(sb + n, &a_fixed.y);
        n += tvla_ser_ibz(sb + n, &a_fixed.norm);
        n += tvla_ser_ibz(sb + n, &split_fixed.coord.v[0]);
        n += tvla_ser_ibz(sb + n, &split_fixed.coord.v[1]);
        FILE *h = fopen("fixed_as.h", "w");
        fprintf(h, "/* auto-gen: a_fixed(x,y,norm) + split(v0,v1) for random-secret TVLA */\n");
        fprintf(h, "#ifndef FIXED_AS_H\n#define FIXED_AS_H\n#include <stdint.h>\n");
        fprintf(h, "#define FIXED_AS_LEN %d\n", n);
        fprintf(h, "static const uint8_t FIXED_AS[FIXED_AS_LEN] = {");
        for (int i = 0; i < n; i++) fprintf(h, "%s0x%02x,", (i % 12 == 0 ? "\n  " : ""), sb[i]);
        fprintf(h, "\n};\n#endif\n");
        fclose(h);
    }

    uint8_t *cls = malloc((size_t)N);
    for (long i = 0; i < N; i++) cls[i] = (uint8_t)((i % 7 == 0) ? 0 : 1);
    for (long i = N - 1; i > 0; i--) { long j = rand() % (i + 1); uint8_t t = cls[i]; cls[i] = cls[j]; cls[j] = t; }

    FILE *fin = fopen("tvla_inputs_rk.bin", "wb");
    FILE *fcr = fopen("tvla_expected_crc_rk.bin", "wb");
    FILE *fcl = fopen("tvla_classes_rk.bin", "wb");
    FILE *flb = fopen("labels_rk.bin", "wb");
    uint32_t magic = TVLA_MAGIC, n32 = (uint32_t)N; uint16_t recmax = TVLA_MAX_REC;
    fwrite(&magic, 4, 1, fin); fwrite(&n32, 4, 1, fin); fwrite(&recmax, 2, 1, fin);
    fwrite(cls, 1, (size_t)N, fcl);

    uint8_t rec[TVLA_MAX_REC], exb[TVLA_MAX_REC];
    for (long i = 0; i < N; i++) {
        quat_ideal_t *b;
        if (cls[i] == 0) { b = &b0; }
        else { do { gen_ideal_coprime(&b_rand, &a_fixed.norm); } while (!split_ok(&split_fixed, &b_rand.norm)); b = &b_rand; }
        int rl = ser_b(rec, b);
        { uint8_t lb = (rec[1] | rec[2]) ? rec[3] : 0; fputc(lb, flb); }
        quat_ideal_intersect_O0(&out, &a_fixed, b, &split_fixed);
        int el = 0;
        el += tvla_ser_ibz(exb + el, &out.x);
        el += tvla_ser_ibz(exb + el, &out.y);
        el += tvla_ser_ibz(exb + el, &out.norm);
        uint32_t crc = tvla_crc32(exb, el);
        fputc(cls[i], fin);
        uint16_t rl16 = (uint16_t)rl; fwrite(&rl16, 2, 1, fin); fwrite(rec, 1, (size_t)rl, fin);
        fwrite(&crc, 4, 1, fcr);
    }
    fclose(fin); fclose(fcr); fclose(fcl); fclose(flb); free(cls);
    fprintf(stderr, "rk: wrote inputs (N=%ld), a.norm=%d b0.norm=%d bits\n",
            N, ibz_bitsize(&a_fixed.norm), ibz_bitsize(&b0.norm));
    return 0;
}
