/* equiv_prime_target.c - CW SimpleSerial 2.1 target: primality test of n = nrd(J_t)
 * as executed by EquivalentCoprimeIdeal on the accepted candidate (ibz_probab_prime).
 * Per 'p' the host streams one serialized ibz (n). The trigger brackets the whole
 * call; the traced start (small-prime sieve, Montgomery setup, base-2 Miller-Rabin)
 * is identical for any reps >= 24, so reps = 24 keeps the per-trace time short.
 * Build: make TVLA_TARGET_SRC=equiv_prime_target.c TVLA_DEFS= TARGET=sqisign-prime-r32 \
 *             PLATFORM=CWLITEARM CRYPTO_TARGET=NONE SS_VER=SS_VER_2_1
 */
#include "hal.h"
#include "simpleserial.h"
#include <stdint.h>
#include <quaternion.h>
#include "tvla_io.h"

void randombytes_init(unsigned char *entropy, unsigned char *perso, int strength);
static ibz_t g_n;
static volatile int g_res;

uint8_t
run_prime(uint8_t cmd, uint8_t scmd, uint8_t len, uint8_t *data)
{
    (void)cmd; (void)scmd; (void)len;
    const uint8_t *p = data;
    tvla_de_ibz(&p, &g_n);
    trigger_high();
    g_res = ibz_probab_prime(&g_n, 24);
    trigger_low();
    uint8_t r[4] = { 0xCA, 0xFE, 0x9E, (uint8_t)(g_res & 0xff) };
    simpleserial_put('r', 4, r);
    return 0x00;
}

int
main(void)
{
    platform_init();
    init_uart();
    trigger_setup();
    ibz_init(&g_n);
    randombytes_init(0, 0, 0);
    simpleserial_init();
    simpleserial_addcmd(0x01, 200, run_prime);
    while (1)
        simpleserial_get();
}
