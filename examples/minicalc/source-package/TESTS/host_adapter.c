/* Linux file-service adapter for hosted tests, never linked into the geode. */
#define _GNU_SOURCE
#include "calc.h"
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <termios.h>
#include <sys/stat.h>
static int fail_write,fail_rename,fail_close,write_calls,rename_calls,close_calls;
void test_faults(int w,int r,int c){fail_write=w;fail_rename=r;fail_close=c;write_calls=rename_calls=close_calls=0;}
static int err(int e){return e==ENOENT?-2:e==EEXIST?-80:e==EACCES?-5:e==ENOSPC?-39:-31;}
int file_open(const char*p){int f=open(p,O_RDONLY);return f<0?err(errno):f;}
int file_create_new(const char*p){int f=open(p,O_WRONLY|O_CREAT|O_EXCL,0600);return f<0?err(errno):f;}
int file_read(int f,void*b,unsigned n){int r=(int)read(f,b,n);return r<0?err(errno):r;}
int file_write(int f,const void*b,unsigned n){int r;if(++write_calls==fail_write){if(n>1)return (int)write(f,b,n/2);return -39;}r=(int)write(f,b,n);return r<0?err(errno):r;}
int file_close(int f){int result=close(f);if(++close_calls==fail_close)return -31;return result<0?err(errno):0;}
int file_remove(const char*p){int r=unlink(p);return r<0?err(errno):0;}
int file_rename(const char*a,const char*b){if(++rename_calls==fail_rename)return -5;/* Same-directory no-clobber rename, like DOS function 56h. */
 if(renameat2(AT_FDCWD,a,AT_FDCWD,b,RENAME_NOREPLACE)<0)return err(errno);return 0;}
