/* intersect_target_rk.c - CW SimpleSerial 2.1 target, random-SECRET TVLA.
 * a, split compiled in (fixed_as.h); the secret ideal b is streamed per 'p'.
 * Build: make PLATFORM=CWLITEARM CRYPTO_TARGET=NONE SS_VER=SS_VER_2_1
 */
#include "hal.h"
#include "simpleserial.h"
#include <stdint.h>

#include "tvla_io.h"
#include "tvla_core_rk.h"
#include "fixed_as.h"

/* triggers relocated inside ideal.c value-region; outer trigger disabled */
static uint8_t obuf[TVLA_MAX_REC];

uint8_t
run_intersect(uint8_t cmd, uint8_t scmd, uint8_t len, uint8_t *data)
{
    (void)cmd; (void)scmd; (void)len;
    (void)obuf;
    tvla_set_secret(data);
    /* Run the measured routine. The value-region trigger fires INSIDE
       quat_ideal_intersect_O0 (ideal.c), so gaussian_mul's leakage is fully
       captured before this returns. We deliberately SKIP output serialization:
       at RADIX_16 the post-trigger result is numerically wrong, and
       serializing a wrong-bitlength ibz overflows the 240-byte digit buffer
       and obuf[512], hard-faulting the target and desyncing SimpleSerial.
       Reply with a fixed clean token so framing never desyncs; the captured
       trace, not this response, carries the measurement. */
    quat_ideal_intersect_O0(&g_out, &g_a, &g_b, &g_split);
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
    tvla_load_fixed(FIXED_AS);
    simpleserial_init();
    simpleserial_addcmd(0x01, 200, run_intersect);
    while (1)
        simpleserial_get();
}
