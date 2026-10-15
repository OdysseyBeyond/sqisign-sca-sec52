/* host_rng.c - minimal host RNG backend for tvla_gen (deterministic).
 * Supplies the 4 symbols the bundled SQIsign subset lacks. Validity of the
 * generated ideals is guaranteed by the generator's rejection loops, so a
 * simple reproducible PRNG suffices. */
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <prng.h>
#include <rng.h>

SQISIGN_THREAD_LOCAL prng_domain_ctx_t PRNG_default_domain;

static uint64_t S[4];
static uint64_t splitmix(uint64_t *x){ *x += 0x9E3779B97F4A7C15ULL; uint64_t z=*x;
  z=(z^(z>>30))*0xBF58476D1CE4E5B9ULL; z=(z^(z>>27))*0x94D049BB133111EBULL; return z^(z>>31); }
static inline uint64_t rotl(uint64_t x,int k){ return (x<<k)|(x>>(64-k)); }
static uint64_t nxt(void){ uint64_t r=rotl(S[1]*5,7)*9, t=S[1]<<17;
  S[2]^=S[0]; S[3]^=S[1]; S[1]^=S[2]; S[0]^=S[3]; S[2]^=t; S[3]=rotl(S[3],45); return r; }

void randombytes_init(unsigned char *entropy, unsigned char *perso, int strength){
  (void)perso; (void)strength; uint64_t x=0;
  if(entropy){ for(int i=0;i<8;i++) x=(x<<8)|entropy[i]; } else x=0xDEADBEEFCAFEULL;
  if(!x) x=1; for(int i=0;i<4;i++) S[i]=splitmix(&x);
}
int prng_seed(void){ return 0; }
int prng_random_bytes(prng_domain_ctx_t *ctx, unsigned char *out, size_t len){
  (void)ctx; size_t i=0; while(i<len){ uint64_t r=nxt(); size_t n=(len-i<8)?(len-i):8;
    memcpy(out+i,&r,n); i+=n; } return 0;
}
