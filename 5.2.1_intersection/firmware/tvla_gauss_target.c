/* tvla_gauss_target.c - minimal CW SimpleSerial 2.1 target measuring ONLY the
 * secret-dependent gaussian multiply ibz_vec_2_gaussian_mul(&tmp,&setter,&tmp)
 * from quat_ideal_intersect_O0 (ideal.c:476). The two operands (setter, tmp)
 * are precomputed on the host (radix-independent values) and streamed per 'p',
 * so the target skips the slow/buggy pre-gaussian intersect entirely. The trace
 * between trigger_high/low is the identical multiply, now with RADIX_16 limbs
 * (b.x bytes 0-1 stored as one 16-bit limb, separated from bytes 2-3).
 * Build: make PLATFORM=CWLITEARM CRYPTO_TARGET=NONE SS_VER=SS_VER_2_1
 */
#include "hal.h"
#include "simpleserial.h"
#include <stdint.h>

#include "tvla_io.h"       /* tvla_de_ibz, ibz_t */
#include <quaternion.h>    /* ibz_vec_2_t, ibz_vec_2_init, ibz_vec_2_gaussian_mul */

static ibz_vec_2_t g_setter, g_tmp;

uint8_t
run_gauss(uint8_t cmd, uint8_t scmd, uint8_t len, uint8_t *data)
{
    (void)cmd; (void)scmd; (void)len;
    const uint8_t *p = data;
    tvla_de_ibz(&p, &g_setter.v[0]);
    tvla_de_ibz(&p, &g_setter.v[1]);
    tvla_de_ibz(&p, &g_tmp.v[0]);
    tvla_de_ibz(&p, &g_tmp.v[1]);

    trigger_high();
    ibz_vec_2_gaussian_mul(&g_tmp, &g_setter, &g_tmp);
    trigger_low();

    uint8_t r[4] = { 0xCA, 0xFE, 0x4E, 0x72 };
    simpleserial_put('r', 4, r);
    return 0x00;
}

int
main(void)
{
    platform_init();
    init_uart();
    trigger_setup();
    ibz_vec_2_init(&g_setter);
    ibz_vec_2_init(&g_tmp);
    simpleserial_init();
    simpleserial_addcmd(0x01, 200, run_gauss);
    while (1)
        simpleserial_get();
}
