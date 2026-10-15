/* equiv_target.c - CW SimpleSerial 2.1 target for the 5.2.2 experiment.
 * Measures the formation of the inert representation of the equivalent prime
 * ideal J_t (EquivalentCoprimeIdeal tail): quat_ideal_create_O0_inert_odd().
 * Per 'p' command the host streams the function's exact input
 *   gen = (coord[0..3], denom), norm = n(J_t)   (6 serialized ibz)
 * as produced on the host by the full EquivalentCoprimeIdeal run; the device
 * re-runs the real library function from its entry, so the (a,b,c,d) reaching
 * the Gaussian multiply are identical to the host-dumped labels.
 * Trigger TRIG3 (TVLA_TRIG_EQUIVREGION) is inside ideal.c around
 * gaussian_mul ... quat_xyn_to_inert_ideal.
 * Build: make TVLA_TARGET_SRC=equiv_target.c TVLA_DEFS=-DTVLA_TRIG_EQUIVREGION \
 *             TARGET=sqisign-equiv-r32 PLATFORM=CWLITEARM CRYPTO_TARGET=NONE SS_VER=SS_VER_2_1
 */
#include "hal.h"
#include "simpleserial.h"
#include <stdint.h>
#include <quaternion.h>
#include "tvla_io.h"

static quat_alg_elem_t g_gen;
static quat_ideal_t g_out;
static ibz_t g_n;

uint8_t
run_equiv(uint8_t cmd, uint8_t scmd, uint8_t len, uint8_t *data)
{
    (void)cmd; (void)scmd; (void)len;
    const uint8_t *p = data;
    tvla_de_ibz(&p, &g_gen.coord.v[0]);
    tvla_de_ibz(&p, &g_gen.coord.v[1]);
    tvla_de_ibz(&p, &g_gen.coord.v[2]);
    tvla_de_ibz(&p, &g_gen.coord.v[3]);
    tvla_de_ibz(&p, &g_gen.denom);
    tvla_de_ibz(&p, &g_n);
    quat_ideal_create_O0_inert_odd(&g_out, &g_gen, &g_n);
    uint8_t r[4] = { 0xCA, 0xFE, 0xE9, 0x01 };
    simpleserial_put('r', 4, r);
    return 0x00;
}

int
main(void)
{
    platform_init();
    init_uart();
    trigger_setup();
    quat_alg_elem_init(&g_gen);
    quat_ideal_init(&g_out);
    ibz_init(&g_n);
    simpleserial_init();
    simpleserial_addcmd(0x01, 200, run_equiv);
    while (1)
        simpleserial_get();
}
