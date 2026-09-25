# Quick Reference

```text
pcgeos1 doctor
pcgeos1 new DIR --name "Name" --permanent-name name --token ABC1
pcgeos1 build project.json --gwp GWP2.zip [--toolchain auto|gnu|llvm]
pcgeos1 inspect APP.GEO
pcgeos1 scan-target --gwp GWP2.zip --output target.json
```

Basic C callbacks:

```c
void app_init(void);
void app_draw(void);
void app_key(void);
void app_click(void);
```

Drawing:

```c
pcg_rect(x1,y1,x2,y2,color);
pcg_text(x,y,color,"text");
pcg_invalidate();
```

Input globals:

```c
pcg_key_char
pcg_key_flags
pcg_key_handled
pcg_pointer_x
pcg_pointer_y
pcg_pointer_info
```

Target 0.1:

```text
Kernel protocol 622.3
UI protocol 693.0
CPU: 80386+
```
