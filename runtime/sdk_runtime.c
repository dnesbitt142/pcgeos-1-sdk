#include "pcgeos1.h"

volatile pcg_u16 pcg_key_char, pcg_key_flags;
volatile pcg_u16 pcg_pointer_x, pcg_pointer_y, pcg_pointer_info;
volatile pcg_u16 pcg_key_handled;
pcg_draw_cmd drawing[96];
pcg_u16 drawing_count;
volatile pcg_u16 pcg_request_repaint;

static void copy_text(char *d,const char*s,unsigned n){unsigned i=0;if(!s){d[0]=0;return;}while(i+1<n&&s[i]){d[i]=s[i];i++;}d[i]=0;}
void *memcpy(void*d,const void*s,unsigned n){pcg_u8*dd=d;const pcg_u8*ss=s;while(n--)*dd++=*ss++;return d;}
void *memset(void*d,int c,unsigned n){pcg_u8*p=d;while(n--)*p++=(pcg_u8)c;return d;}

void pcg_begin_frame(void){drawing_count=0;}
void pcg_rect(int x1,int y1,int x2,int y2,pcg_u16 color){pcg_draw_cmd*c;if(drawing_count>=96)return;c=&drawing[drawing_count++];c->kind=0;c->x1=x1;c->y1=y1;c->x2=x2;c->y2=y2;c->color=color;c->text[0]=0;}
void pcg_text(int x,int y,pcg_u16 color,const char *s){pcg_draw_cmd*c;if(drawing_count>=96)return;c=&drawing[drawing_count++];c->kind=1;c->x1=x;c->y1=y;c->x2=c->y2=0;c->color=color;copy_text(c->text,s,sizeof(c->text));}
void pcg_invalidate(void){pcg_request_repaint=1;}

void sdk_dispatch(unsigned action){
    pcg_request_repaint=0;
    if(action==1){app_init();}
    else if(action==2){pcg_begin_frame();app_draw();}
    else if(action==3){pcg_key_handled=0;app_key();}
    else if(action==4){app_click();}
}
