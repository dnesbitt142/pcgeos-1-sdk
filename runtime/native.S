/* PC/GEOS 1.x SDK 0.1 generic native adapter. Experimental, 386+.
 * GEOS-facing entry points stay on the native stack. Instrumented C runs on
 * a private stack in an appended resource and periodically returns to a safe
 * interrupt/scheduler window via native_poll.
 */
.intel_syntax noprefix
.code16
.section .native,"ax"
.equ D_WINDOW,0x180
.equ D_CPU,0x182
.equ D_BUSY,0x183
.equ D_DIALOG,0x186
.equ E_SS,6
.equ E_SP,8
.equ E_ESP,10
.equ E_DS,14
.equ STACK_TOP,0xffe0
.macro K ordinal
 .byte 0x9a
 .globl krel_\@
 krel_\@: .word \ordinal,0
.endm
.macro ENGINE_AX
 .byte 0xb8
 .globl rrel_\@
 rrel_\@: .word ENGINE_RESOURCE_ID
.endm

.globl cpu_probe
cpu_probe:
 push dx
 pushf
 pop dx
 mov ax,dx
 and ax,0x0fff
 push ax
 popf
 pushf
 pop ax
 and ax,0xf000
 cmp ax,0xf000
 je cpu_bad
 mov ax,dx
 or ax,0x7000
 push ax
 popf
 pushf
 pop ax
 and ax,0x7000
 cmp ax,0x7000
 jne cpu_bad
 push dx
 popf
 pop dx
 clc
 ret
cpu_bad:
 push dx
 popf
 pop dx
 stc
 ret

.globl native_open
native_open:
 push ax
 push cx
 push dx
 push bp
 push es
 pop ds
 mov byte ptr [D_CPU],0
 mov byte ptr [D_BUSY],0
 mov word ptr [D_WINDOW],0
 mov word ptr [D_DIALOG],0
 call cpu_probe
 jc open_super
 mov byte ptr [D_CPU],1
 mov ax,1
 call engine_enter
open_super:
 pop bp
 pop dx
 pop cx
 pop ax
 mov di,0x40
 K 489
 retf

.globl native_attach
native_attach:
 mov di,0x40
 K 489
 retf

.globl native_close
native_close:
 xor cx,cx
 retf

.globl native_view_closed
native_view_closed:
 cmp cx,word ptr [D_WINDOW]
 jne vc_super
 mov word ptr [D_WINDOW],0
vc_super:
 mov di,0x40
 K 489
 retf

.globl native_expose
native_expose:
 mov word ptr [D_WINDOW],cx
 mov di,cx
 or di,di
 jz expose_done
 mov ax,2
 call engine_enter
 K 211
 K 446
 call draw_native
 K 447
 K 212
expose_done:
 retf

.globl native_select
native_select:
 cmp byte ptr [D_CPU],0
 je select_done
 cmp byte ptr [D_BUSY],0
 jne select_done
 mov byte ptr [D_BUSY],1
 push es
 ENGINE_AX
 mov es,ax
 mov word ptr es:[pcg_pointer_x],cx
 mov word ptr es:[pcg_pointer_y],dx
 mov word ptr es:[pcg_pointer_info],bp
 pop es
 mov ax,4
 call engine_enter
 call maybe_repaint
 mov byte ptr [D_BUSY],0
select_done:
 mov ax,0x8000
 retf

.globl native_key
native_key:
 cmp byte ptr [D_CPU],0
 je key_super
 cmp byte ptr [D_BUSY],0
 jne key_super
 push ax
 push cx
 push dx
 push bp
 mov byte ptr [D_BUSY],1
 push es
 ENGINE_AX
 mov es,ax
 mov word ptr es:[pcg_key_char],cx
 mov word ptr es:[pcg_key_flags],dx
 pop es
 mov ax,3
 call engine_enter
 push es
 ENGINE_AX
 mov es,ax
 cmp word ptr es:[pcg_key_handled],0
 pop es
 je key_unhandled
 call maybe_repaint
 mov byte ptr [D_BUSY],0
 pop bp
 pop dx
 pop cx
 pop ax
 retf
key_unhandled:
 mov byte ptr [D_BUSY],0
 pop bp
 pop dx
 pop cx
 pop ax
key_super:
 mov di,0x40
 K 489
 retf

/* The basic shell has one application command: title-bar Help -> 0x0c0a. */
.globl native_command
native_command:
 cmp ax,0x0c0a
 jne command_done
 mov si,0xa0
 mov ax,0x4197
 call ui_call
command_done:
 retf

ui_call:
 push bx
 push di
 mov bx,3
 K 150
 mov di,0x8000
 K 169
 pop di
 pop bx
 ret

maybe_repaint:
 push ax
 push es
 ENGINE_AX
 mov es,ax
 cmp word ptr es:[pcg_request_repaint],0
 je mr_done
 mov word ptr es:[pcg_request_repaint],0
 pop es
 pop ax
 call repaint
 ret
mr_done:
 pop es
 pop ax
 ret

repaint:
 mov di,word ptr [D_WINDOW]
 or di,di
 jz repaint_done
 mov ax,2
 call engine_enter
 K 211
 call draw_native
 K 212
repaint_done:
 ret

.globl engine_enter
engine_enter:
 pushf
 cli
 pushad
 push ds
 push es
 mov si,ax
 mov bx,ds
 mov cx,ss
 mov dx,sp
 ENGINE_AX
 mov ds,ax
 mov es,ax
 mov word ptr [E_SS],cx
 mov word ptr [E_SP],dx
 mov word ptr [E_DS],bx
 mov ss,ax
 mov esp,STACK_TOP
 xor ebp,ebp
 cld
 movzx eax,si
 push eax
 .code16gcc
 call sdk_dispatch
 .code16
 add esp,4
 mov ax,word ptr [E_SS]
 mov dx,word ptr [E_SP]
 mov ss,ax
 mov sp,dx
 pop es
 pop ds
 popad
 popf
 ret

.globl native_poll
native_poll:
 pushfd
 pushad
 push ds
 push es
 mov dword ptr [E_ESP],esp
 mov ax,word ptr [E_SS]
 mov dx,word ptr [E_SP]
 mov ss,ax
 mov sp,dx
 sti
 nop
 nop
 cli
 mov ax,ds
 mov ss,ax
 mov esp,dword ptr [E_ESP]
 pop es
 pop ds
 popad
 popfd
 .byte 0x66,0xc3

draw_native:
 push ax
 push bx
 push cx
 push dx
 push si
 push bp
 push ds
 push es
 cmp byte ptr [D_CPU],0
 je draw_done
 ENGINE_AX
 mov ds,ax
 mov cx,0x1a00
 mov dx,10
 xor ah,ah
 K 366
 mov si,OFFSET drawing
 mov bp,word ptr [drawing_count]
 cmp bp,96
 jbe draw_loop
 mov bp,96
draw_loop:
 or bp,bp
 jz draw_done
 push si
 push bp
 cmp word ptr [si],0
 jne draw_text
 mov ax,word ptr [si+10]
 K 355
 mov ax,word ptr [si+2]
 mov bx,word ptr [si+4]
 mov cx,word ptr [si+6]
 mov dx,word ptr [si+8]
 K 336
 jmp draw_next
draw_text:
 mov ax,word ptr [si+10]
 K 359
 mov ax,word ptr [si+2]
 mov bx,word ptr [si+4]
 add si,12
 xor cx,cx
 K 330
draw_next:
 pop bp
 pop si
 add si,76
 dec bp
 jmp draw_loop
draw_done:
 pop es
 pop ds
 pop bp
 pop si
 pop dx
 pop cx
 pop bx
 pop ax
 ret
.section .note.GNU-stack,"",@progbits
