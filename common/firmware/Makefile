# Makefile - ChipWhisperer SimpleSerial 2.1 targets for the SQIsign 3.0
# side-channel experiments (Sections 5.2.1 and 5.2.2 of the paper).
#
# Check the repository out under chipwhisperer/firmware/mcu/ (or pass CWFIRMWARE,
# see bottom) and run get_sqisign.sh first to populate ./sqisign/{src,inc}.
# Then build from this directory, e.g.:
#
#   # 5.2.1 Gaussian multiply, isolated, 32-bit limbs (-Os)
#   make TARGET=sqisign-gauss-r32 TVLA_TARGET_SRC=tvla_gauss_target.c \
#        RADIX=RADIX_32 PLATFORM=CWLITEARM CRYPTO_TARGET=NONE SS_VER=SS_VER_2_1
#
#   # 5.2.1 Gaussian multiply, isolated, 16-bit limbs (-Os)  [needs 0002 patch only]
#   make TARGET=sqisign-gauss-r16 TVLA_TARGET_SRC=tvla_gauss_target.c \
#        RADIX=RADIX_16 PLATFORM=CWLITEARM CRYPTO_TARGET=NONE SS_VER=SS_VER_2_1
#
#   # 5.2.1 -O0 variants: add OPT=0.
#
#   # 5.2.1 output window (W2/W3): intersect_target_rk.c + TVLA_TRIG_OUTREGION (W2)
#   #   or TVLA_TRIG_STOREREGION (W3).
#   make TARGET=sqisign-out-r32 TVLA_TARGET_SRC=intersect_target_rk.c \
#        TVLA_DEFS=-DTVLA_TRIG_OUTREGION RADIX=RADIX_32 PLATFORM=CWLITEARM CRYPTO_TARGET=NONE SS_VER=SS_VER_2_1
#
#   # 5.2.2 EquivalentCoprimeIdeal formation window (W: gaussian product -> (x,y))
#   make TARGET=sqisign-equiv-r32 TVLA_TARGET_SRC=equiv_target.c \
#        TVLA_DEFS=-DTVLA_TRIG_EQUIVREGION RADIX=RADIX_32 PLATFORM=CWLITEARM CRYPTO_TARGET=NONE SS_VER=SS_VER_2_1
#
#   # 5.2.2 primality test of n = nrd(J_t)
#   make TARGET=sqisign-prime-r32 \
#        "TVLA_TARGET_SRC=equiv_prime_target.c host_rng.c" \
#        TVLA_DEFS=-DSQISIGN_SINGLE_THREADED RADIX=RADIX_32 PLATFORM=CWLITEARM CRYPTO_TARGET=NONE SS_VER=SS_VER_2_1
#
# (CWLITEARM is the CW-Lite Arm alias for the STM32F303 target. OPT defaults to
# the CW build system's -Os; pass OPT=0 for the -O0 builds used in the paper.)

TARGET ?= sqisign-gauss-r32

# Harness source for this build (one of the firmware/*.c under 5.2.1 / 5.2.2).
TVLA_TARGET_SRC ?= tvla_gauss_target.c
SRC += $(TVLA_TARGET_SRC)

# --- SQIsign 3.0 sources (nist-v3, commit 6d01770, variant p324_3) ---
# Populated by get_sqisign.sh into ./sqisign/{src,inc}.
VPATH += :sqisign/src:../../5.2.1_intersection/firmware:../../5.2.2_equivalent_prime_ideal/firmware
SRC += mp.c modqx.c
SRC += ideal.c dim2.c dim4.c algebra.c integers.c lattice.c finit.c stdorder.c qlapoty.c printer.c lll_applications.c
SRC += gaussian_xgcd.c lehmer_xgcd.c lll_dim4.c lll_lg2.c
SRC += quaternion_data.c

# Headers: bundled SQIsign includes + this dir + the per-experiment firmware dir.
EXTRAINCDIRS += sqisign/inc . ../../5.2.1_intersection/firmware ../../5.2.2_equivalent_prime_ideal/firmware

# Limb radix for this build: RADIX_32 (default) or RADIX_16.
RADIX ?= RADIX_32

# SQIsign build configuration for this variant. NDEBUG strips asserts so the
# traced region is exactly the arithmetic (no assert-time branches).
CDEFS += -D$(RADIX) -DSQISIGN_BUILD_TYPE_REF -DSQISIGN_GF_IMPL_REF
CDEFS += -DSQISIGN_VARIANT=p324_3 -DNDEBUG
# Trigger / dump selection for this build (see the variant table in the README).
# The isolated Gaussian-multiply target carries its own trigger, so it needs none.
TVLA_DEFS ?=
CDEFS += $(TVLA_DEFS)

CRYPTO_TARGET = NONE

# SQIsign requires C11; append last so it overrides Makefile.inc's -std=gnu99.
CFLAGS_LAST = -std=gnu11

# ---- CW build system ----
# Location of chipwhisperer/firmware/mcu. Default assumes this repository is
# checked out directly under chipwhisperer/firmware/mcu/<repo>/ ; otherwise pass
#   make CWFIRMWARE=/path/to/chipwhisperer/firmware/mcu ...
CWFIRMWARE ?= ../../..
include $(CWFIRMWARE)/simpleserial/Makefile.simpleserial
FIRMWAREPATH = $(CWFIRMWARE)
include $(FIRMWAREPATH)/Makefile.inc
