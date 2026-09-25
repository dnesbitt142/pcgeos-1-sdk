/* Freestanding compiler support. The 16-bit DOS target has no libc/libgcc.
   Restoring unsigned division; callers use bounded fixed-point intermediates. */
#include "calc.h"
u64 __udivdi3(u64 n,u64 d){u64 q=0,r=0;int i;if(!d)return 0;for(i=63;i>=0;i--){u64 bit=(n>>i)&1;int carry=(int)(r>>63);r=(r<<1)|bit;if(carry||r>=d){r-=d;q|=(u64)1<<i;}}return q;}
i64 __divdi3(i64 n,i64 d){int sign=(n<0)!=(d<0);u64 a=n<0?0-(u64)n:(u64)n,b=d<0?0-(u64)d:(u64)d,q=__udivdi3(a,b);return sign?(i64)(0-q):(i64)q;}
u64 __umoddi3(u64 n,u64 d){return n-__udivdi3(n,d)*d;}
i64 __moddi3(i64 n,i64 d){return n-__divdi3(n,d)*d;}
void *memcpy(void*d,const void*s,unsigned n){return m_copy(d,s,n);}
void *memset(void*d,int c,unsigned n){u8*p=d;while(n--)*p++=(u8)c;return d;}
