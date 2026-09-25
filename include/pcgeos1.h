#ifndef PCGEOS1_H
#define PCGEOS1_H
/* PC/GEOS 1.x SDK 0.1 - experimental freestanding C API.
 * This is not an official GeoWorks header and does not claim ABI completeness.
 */
typedef unsigned char pcg_u8;
typedef unsigned short pcg_u16;
typedef unsigned long pcg_u32;
typedef signed short pcg_i16;

#define PCG_COLOR_BLACK 0x0000
#define PCG_COLOR_WHITE 0x0f00
#define PCG_COLOR_LIGHT_GREY 0x0700
#define PCG_COLOR_DARK_GREY 0x0800
#define PCG_COLOR_BLUE 0x0100
#define PCG_COLOR_GREEN 0x0200
#define PCG_COLOR_CYAN 0x0300
#define PCG_COLOR_RED 0x0400

#define PCG_KEY_ENTER 13
#define PCG_KEY_ESCAPE 27

typedef struct {
    pcg_u16 kind;   /* 0 rectangle, 1 text */
    pcg_i16 x1,y1,x2,y2;
    pcg_u16 color;
    char text[64];
} pcg_draw_cmd;

extern volatile pcg_u16 pcg_key_char, pcg_key_flags;
extern volatile pcg_u16 pcg_pointer_x, pcg_pointer_y, pcg_pointer_info;
extern volatile pcg_u16 pcg_key_handled;

void pcg_begin_frame(void);
void pcg_rect(int x1,int y1,int x2,int y2,pcg_u16 color);
void pcg_text(int x,int y,pcg_u16 color,const char *text);
void pcg_invalidate(void);

/* Application callbacks. app_draw() should emit pcg_* drawing commands. */
void app_init(void);
void app_draw(void);
void app_key(void);
void app_click(void);

#endif
