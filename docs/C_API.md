# Experimental C API

Header: `include/pcgeos1.h`

The API is intentionally small in SDK 0.1.

## Types

`pcg_u8`, `pcg_u16`, `pcg_u32`, `pcg_i16` are fixed-width-style aliases for the compiler model used by the SDK.

Do not pass C pointers directly to arbitrary GEOS APIs. Native services use segmented addresses and calling conventions that must be bridged explicitly.

## Application callbacks

```c
void app_init(void);
void app_draw(void);
void app_key(void);
void app_click(void);
```

### app_init

Called once after the 386 CPU probe succeeds during application open.

### app_draw

Called before the native view is redrawn. Emit drawing commands using the functions below.

### app_key

Called for native keyboard-character messages delivered to the view. Inputs:

```c
pcg_key_char
pcg_key_flags
```

Set:

```c
pcg_key_handled = 1;
```

to consume the message.

### app_click

Called for the view selection message. Inputs:

```c
pcg_pointer_x
pcg_pointer_y
pcg_pointer_info
```

## Drawing

```c
void pcg_begin_frame(void);
void pcg_rect(int x1,int y1,int x2,int y2,pcg_u16 color);
void pcg_text(int x,int y,pcg_u16 color,const char *text);
void pcg_invalidate(void);
```

`app_draw()` is automatically preceded by `pcg_begin_frame()` by the SDK dispatcher.

`pcg_invalidate()` requests a redraw after the current input callback returns to the native GEOS context.

## Colors

The current renderer exposes a small set of indexed-color constants. These are target-era GEOS color values, not RGB.

## Limits

- 96 drawing commands per frame.
- Text commands store at most 63 characters plus terminator.
- The basic renderer supports only filled rectangles and text.
- No GState or graphics handle is exposed to C in SDK 0.1.
