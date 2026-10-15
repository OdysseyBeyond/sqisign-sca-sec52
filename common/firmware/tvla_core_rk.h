/* tvla_core_rk.h - random-secret variant: a, split are fixed (compiled in),
 * the SECRET ideal b is streamed per trace. Traced call is unchanged:
 * quat_ideal_intersect_O0(out, a_fixed, b, split_fixed).
 */
#ifndef TVLA_CORE_RK_H
#define TVLA_CORE_RK_H

#include "tvla_io.h"
#include <quaternion.h>

static quat_ideal_t  g_a, g_b, g_out;
static quat_alg_elem_t g_split;

/* Load fixed public operands: a(x,y,norm) then split(v0,v1). */
static inline void
tvla_load_fixed(const uint8_t *fa)
{
    const uint8_t *p = fa;
    quat_ideal_init(&g_a);
    quat_ideal_init(&g_b);
    quat_ideal_init(&g_out);
    quat_alg_elem_init(&g_split);
    tvla_de_ibz(&p, &g_a.x);
    tvla_de_ibz(&p, &g_a.y);
    tvla_de_ibz(&p, &g_a.norm);
    tvla_de_ibz(&p, &g_split.coord.v[0]);
    tvla_de_ibz(&p, &g_split.coord.v[1]);
    ibz_set(&g_split.coord.v[2], 0, 1);
    ibz_set(&g_split.coord.v[3], 0, 1);
    ibz_set(&g_split.denom, 1, 2);
}

/* Parse one streamed record into the secret ideal b = (b.x,b.y,b.norm). */
static inline void
tvla_set_secret(const uint8_t *rec)
{
    const uint8_t *p = rec;
    tvla_de_ibz(&p, &g_b.x);
    tvla_de_ibz(&p, &g_b.y);
    tvla_de_ibz(&p, &g_b.norm);
}

static inline int
tvla_compute(uint8_t *obuf, void (*trig_hi)(void), void (*trig_lo)(void))
{
    if (trig_hi) trig_hi();
    quat_ideal_intersect_O0(&g_out, &g_a, &g_b, &g_split);
    if (trig_lo) trig_lo();
    int o = 0;
    o += tvla_ser_ibz(obuf + o, &g_out.x);
    o += tvla_ser_ibz(obuf + o, &g_out.y);
    o += tvla_ser_ibz(obuf + o, &g_out.norm);
    return o;
}

#endif
