#include "pcgeos1.h"
static int clicks;
void app_init(void){clicks=0;}
void app_draw(void){
    pcg_rect(0,0,499,299,PCG_COLOR_WHITE);
    pcg_text(20,24,PCG_COLOR_BLACK,"Hello from PC/GEOS 1.x SDK 0.1");
    pcg_text(20,44,PCG_COLOR_DARK_GREY,"Click the view or press Enter.");
    if(clicks) pcg_text(20,72,PCG_COLOR_BLUE,"Input received - native callback reached C code.");
}
void app_click(void){clicks++;pcg_invalidate();}
void app_key(void){
    if((pcg_key_char & 0xff)==PCG_KEY_ENTER){clicks++;pcg_key_handled=1;pcg_invalidate();}
}
