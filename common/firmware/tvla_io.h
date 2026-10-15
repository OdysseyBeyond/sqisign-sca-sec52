/* tvla_io.h - portable (host + STM32 target) serialization of SQIsign 3.0
 * ibz_t operands for a TVLA leakage assessment of quat_ideal_intersect_O0.
 *
 * Wire format of one ibz value (little-endian magnitude + explicit sign):
 *     u8  sign      (1 if value < 0, else 0)
 *     u16 len       (number of magnitude bytes, little-endian on the wire)
 *     u8  mag[len]  (little-endian magnitude)
 *
 * One input RECORD streamed to the target, in call order of
 *   quat_ideal_intersect_O0(out, a, b, split_a) with a=challenge, b=secret:
 *     a.x, a.y, a.norm, split.coord[0], split.coord[1]
 * (b = secret-key ideal is fixed and compiled into the target; split.denom==1.)
 *
 * ibz_copy_bits / ibz_to_digits are in the SQIsign mp module and behave
 * identically on x86 and Cortex-M4 (both little-endian), so this one file
 * compiles unchanged on host and target.
 */
#ifndef TVLA_IO_H
#define TVLA_IO_H

#include <stdint.h>
#include <string.h>
#include <mp.h>          /* ibz_t, ibz_copy_bits, ibz_to_digits, ibz_neg ... */

#define TVLA_MAGIC   0x54564C41u   /* "TVLA" */
#define TVLA_MAX_REC 512           /* upper bound on one serialized record   */

/* CRC32 (reflected, poly 0xEDB88320) - used to verify the target's output
 * cheaply over the wire (4 bytes) against the host reference. */
static inline uint32_t
tvla_crc32(const uint8_t *p, int n)
{
    uint32_t c = 0xFFFFFFFFu;
    for (int i = 0; i < n; i++) {
        c ^= p[i];
        for (int k = 0; k < 8; k++)
            c = (c >> 1) ^ (0xEDB88320u & (uint32_t)(-(int32_t)(c & 1)));
    }
    return c ^ 0xFFFFFFFFu;
}

/* --- single ibz -------------------------------------------------------- */

/* Serialize *v into buf (>= 3 + IBZ_NLIMBS*sizeof(digit_t)); returns #bytes. */
static inline int
tvla_ser_ibz(uint8_t *buf, const ibz_t *v)
{
    ibz_t a;
    ibz_init(&a);
    ibz_abs(&a, v);
    uint8_t sign = (uint8_t)((!ibz_is_positive(v)) && (!ibz_is_zero(v)));
    int nbytes = ibz_is_zero(&a) ? 0 : ibz_size_in_base(&a, 256);

    digit_t tmp[IBZ_NLIMBS];
    memset(tmp, 0, sizeof(tmp));
    if (nbytes > 0)
        ibz_to_digits(tmp, &a);          /* little-endian magnitude */

    int o = 0;
    buf[o++] = sign;
    buf[o++] = (uint8_t)(nbytes & 0xff);
    buf[o++] = (uint8_t)((nbytes >> 8) & 0xff);
    memcpy(buf + o, (const uint8_t *)tmp, (size_t)nbytes);
    o += nbytes;
    return o;
}

/* Deserialize one ibz from *pp (advanced past it) into *v. */
static inline void
tvla_de_ibz(const uint8_t **pp, ibz_t *v)
{
    const uint8_t *p = *pp;
    uint8_t sign = p[0];
    int nbytes = (int)p[1] | ((int)p[2] << 8);
    p += 3;

    digit_t tmp[IBZ_NLIMBS];
    memset(tmp, 0, sizeof(tmp));
    if (nbytes > 0)
        memcpy((uint8_t *)tmp, p, (size_t)nbytes);   /* little-endian */
    p += nbytes;

    ibz_copy_bits(v, tmp, nbytes > 0 ? 8 * nbytes : 1);
    if (sign)
        ibz_neg(v, v);
    *pp = p;
}

#endif /* TVLA_IO_H */
