/* Native 1.x process methods and kernel adapters. All public entry points use
 * the 16-bit GEOS ABI. Pure C executes in short interrupt-masked slices; native
 * polling restores the REAL GEOS stack and saves all 32-bit registers before
 * reenabling interrupts. No DOS, BIOS, interrupt hooks, or external executable.
 */
.intel_syntax noprefix
.code16
.section .native,"ax"
.equ D_WINDOW,0x180
.equ D_CPU,0x182
.equ D_BUSY,0x183
.equ D_RESTORED,0x184
.equ E_SS,6
.equ E_SP,8
.equ E_ESP,10
.equ E_DS,14
.equ E_ACTION,24
.equ STACK_TOP,0xffe0
.macro K ordinal
 .byte 0x9a
 .globl krel_\@
 krel_\@: .word \ordinal,0
.endm
.macro ENGINE_AX
 .byte 0xb8
 .globl rrel_\@
 rrel_\@: .word 11
.endm
/* 8086-safe probe, before ANY 386 instruction. CF means unsupported CPU. */
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
 mov byte ptr [D_RESTORED],0
 mov word ptr [D_DIALOG],0
 call cpu_probe
 jc open_super
 mov byte ptr [D_CPU],1
 /* BP is a GEOS session-state handle, or zero. */
 or bp,bp
 jz open_init
 push ds
 push es
 mov bx,bp
 K 5
 mov ds,ax
 cmp word ptr [0],0x434d
 jne state_bad
 cmp word ptr [2],0x324e
 jne state_bad
 cmp word ptr [4],0x0201
 jne state_bad
 cmp word ptr [20],OFFSET __engine_used
 jne state_bad
 cmp dword ptr [28],STATE_TAG
 jne state_bad
 ENGINE_AX
 mov es,ax
 xor si,si
 xor di,di
 mov cx,OFFSET __engine_used
 cld
 rep movsb
 pop es
 pop ds
 mov byte ptr [D_RESTORED],1
 jmp state_unlock
state_bad:
 pop es
 pop ds
state_unlock:
 mov bx,bp
 K 6
open_init:
 cmp byte ptr [D_RESTORED],0
 jne open_path_ready
 mov ax,5
 K 0x4c
 push es
 mov cx,0
 jc open_path_set
 inc cx
open_path_set:
 ENGINE_AX
 mov es,ax
 mov word ptr es:[native_path_ok],cx
 push ds
 mov ds,ax
 mov si,OFFSET sheet_dir
 mov cx,104
 K 0x4b
 mov word ptr [sheet_disk],bx
 pop ds
 pop es
open_path_ready:
 xor ax,ax
 cmp byte ptr [D_RESTORED],0
 je open_engine
 mov ax,13
open_engine:
 call engine_enter
open_super:
 pop bp
 pop dx
 pop cx
 pop ax
 mov di,0x40
 K 489
 cmp byte ptr [D_CPU],0
 je open_done
 call sync_editor
open_done:
 retf

.globl native_attach
native_attach:
 mov di,0x40
 K 489
 retf

.globl native_close
native_close:
 /* GEOS owns the returned state handle. This is session restoration, NOT
    a substitute for a user-saved MCS file or a crash-safe autosave. */
 xor cx,cx
 cmp byte ptr [D_CPU],0
 je close_done
 call get_entry
 mov ax,28
 call engine_enter
 push ds
 mov ax,OFFSET __engine_used
 mov cx,0x6050
 K 0
 jc close_failed
 mov es,ax
 push bx
 ENGINE_AX
 mov ds,ax
 xor si,si
 xor di,di
 mov cx,OFFSET __engine_used
 cld
 rep movsb
 pop bx
 K 6
 mov cx,bx
 pop ds
 retf
close_failed:
 pop ds
 xor cx,cx
close_done:
 retf

.globl native_view_closed
native_view_closed:
 cmp cx,word ptr [D_WINDOW]
 jne closed_super
 mov word ptr [D_WINDOW],0
closed_super:
 mov di,0x40
 K 489
 retf

.globl native_expose
native_expose:
 mov word ptr [D_WINDOW],cx
 mov di,cx
 or di,di
 jz expose_done
 K 211
 K 446
 call draw_native
 K 447
 K 212
expose_done:
 retf

/* Real native 1.x object messages. The constants are recovered from the
 * supplied UI.GEO/VIEWER.GEO, not taken from a later 2.x SDK. */
.equ D_DIALOG,0x186
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
 mov word ptr es:[pointer_x],cx
 mov word ptr es:[pointer_y],dx
 mov word ptr es:[pointer_info],bp
 pop es
 call get_entry
 mov ax,14
 call engine_enter
 call finish_action
 mov byte ptr [D_BUSY],0
select_done:
 mov ax,0x8000
 retf

/* Native MSG_META_KBD_CHAR is delivered by the focusable GenView. The
 * process keeps unhandled shortcuts on the normal superclass path. */
.globl native_key
native_key:
 cmp byte ptr [D_CPU],0
 je key_super
 cmp byte ptr [D_BUSY],0
 jne key_super
 cmp word ptr [D_DIALOG],0
 jne key_super
 push ax
 push cx
 push dx
 push bp
 mov byte ptr [D_BUSY],1
 push es
 ENGINE_AX
 mov es,ax
 mov word ptr es:[key_char],cx
 mov word ptr es:[key_flags],dx
 pop es
 call get_entry
 mov ax,30
 call engine_enter
 push es
 ENGINE_AX
 mov es,ax
 cmp word ptr es:[key_handled],0
 pop es
 je key_unhandled
 call finish_action
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

.globl native_command
native_command:
 cmp byte ptr [D_CPU],0
 je command_done
 cmp byte ptr [D_BUSY],0
 jne command_done
 mov byte ptr [D_BUSY],1
 sub ax,0x0c00
 cmp ax,19
 je activate_open
 cmp ax,20
 je accept_save
 cmp ax,21
 je selected_file
 cmp ax,25
 je save_selection
 push ax
 call get_entry
 pop ax
 cmp ax,15
 jne not_goto
 push ax
 mov si,0x2c
 mov dx,OFFSET address_entry
 call read_text
 pop ax
not_goto:
 cmp ax,18
 jne generic_action
 push ax
 mov si,0x82
 mov dx,OFFSET aux_entry
 call read_text
 pop ax
generic_action:
 call engine_enter
 call finish_action
 jmp command_end
activate_open:
 cmp word ptr [D_DIALOG],0x60
 jne command_end
 /* Let the selector interpret directories/drives itself. Activation, not
    simple selection, sends our 0xc15 notification for a file. */
 mov si,0x62
 mov ax,0x4200
 xor cx,cx
 call ui_call
 mov cx,bp
 and ch,7
 mov ax,0x421a
 mov byte ptr [D_BUSY],0
 call ui_call
 jmp command_done
selected_file:
 cmp word ptr [D_DIALOG],0x60
 jne command_end
 test bp,0x2000
 jz command_end
 test bp,0xc000
 jnz command_end
 mov si,0x62
 call selector_path
 mov ax,0x4200
 ENGINE_AX
 mov cx,ax
 mov dx,OFFSET dialog_file
 mov ax,0x4200
 call ui_call
 mov ax,26
 call engine_enter
 call finish_action
 jmp command_end
save_selection:
 cmp word ptr [D_DIALOG],0x70
 jne command_end
 test bp,0xc000
 jnz command_end
 /* Highlighting a file fills the filename field, but NEVER saves it. */
 mov si,0x72
 ENGINE_AX
 mov cx,ax
 mov dx,OFFSET dialog_file
 mov ax,0x4200
 call ui_call
 push es
 ENGINE_AX
 mov es,ax
 cmp byte ptr es:[dialog_file],0
 pop es
 je command_end
 mov si,0x74
 mov bp,OFFSET dialog_file
 call write_text
 jmp command_end
accept_save:
 cmp word ptr [D_DIALOG],0x70
 jne command_end
 mov si,0x74
 mov dx,OFFSET dialog_file
 call read_text
 mov si,0x72
 call selector_path
 mov ax,27
 call engine_enter
 call finish_action
command_end:
 mov byte ptr [D_BUSY],0
command_done:
 retf

/* SI object chunk; AX message; CX/DX/BP according to that object's ABI. */
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

get_entry:
 push si
 push dx
 mov si,0x3a
 mov dx,OFFSET entry
 call read_text
 pop dx
 pop si
 ret

/* Each genuine GenText field has a smaller maximum than its destination.
 * 2204 with nonzero CX copies to CX:DX; an empty object returns without
 * copying, hence the explicit NUL initialization. */
read_text:
 push ax
 push bx
 push cx
 push dx
 push si
 push di
 push bp
 push es
 ENGINE_AX
 mov es,ax
 mov di,dx
 mov byte ptr es:[di],0
 mov cx,ax
 mov ax,0x2204
 call ui_call
 pop es
 pop bp
 pop di
 pop si
 pop dx
 pop cx
 pop bx
 pop ax
 ret

/* SI object; BP text offset in the fixed engine resource. */
write_text:
 push ax
 push cx
 push dx
 push bp
 ENGINE_AX
 mov dx,ax
 xor cx,cx
 mov ax,0x2200
 call ui_call
 pop bp
 pop dx
 pop cx
 pop ax
 ret

/* Focus is a native generic message. Replacement text leaves its caret at
 * the end. Native Shift+Home selects the contents of our single-line field.
 * This avoids writing specific-UI instance data or using a 2.x text API. */
focus_text:
 push ax
 push cx
 push dx
 push bp
 mov ax,0x418c
 call ui_call
 mov ax,0x007b
 mov cx,0xff94
 mov dx,0x0804
 xor bp,bp
 call ui_call
 pop bp
 pop dx
 pop cx
 pop ax
 ret

selector_path:
 push ax
 push cx
 push dx
 push bp
 push es
 ENGINE_AX
 mov cx,ax
 mov dx,OFFSET dialog_dir
 mov ax,0x4202
 call ui_call
 ENGINE_AX
 mov es,ax
 mov word ptr es:[dialog_disk],bp
 pop es
 pop bp
 pop dx
 pop cx
 pop ax
 ret

sync_editor:
 push ax
 push si
 push bp
 push es
 ENGINE_AX
 mov es,ax
 cmp word ptr es:[native_sync],0
 je sync_done
 mov si,0x3a
 mov bp,OFFSET editor_text
 call write_text
 mov si,0x2c
 mov bp,OFFSET selected_name
 call write_text
 cmp word ptr es:[native_focus],0
 je sync_done
 cmp word ptr es:[native_focus],2
 je focus_worksheet
 mov si,0x3a
 call focus_text
 jmp sync_done
focus_worksheet:
 mov si,0x3e
 mov ax,0x418c
 call ui_call
sync_done:
 pop es
 pop bp
 pop si
 pop ax
 ret

/* Apply UI requests only after the calculation core has returned to GEOS's
 * normal stack. Browsing does not change the worksheet's saved directory. */
finish_action:
 call sync_editor
 push ax
 push bx
 push cx
 push dx
 push si
 push di
 push bp
 push es
 ENGINE_AX
 mov es,ax
 mov ax,word ptr es:[native_request]
 or ax,ax
 jz dialog_status
 cmp ax,6
 je show_help
 cmp ax,5
 je dismiss_current
 push ax
 call dismiss_dialog
 pop ax
 cmp ax,1
 je show_open
 cmp ax,2
 je show_save
 cmp ax,3
 je show_fill
 mov si,0x90
 jmp show_dialog
show_help:
 mov si,0xa0
 mov ax,0x4197
 call ui_call
 jmp finish_ui
show_open:
 mov si,0x62
 call init_selector
 mov si,0x60
 jmp show_dialog
show_save:
 mov si,0x72
 call init_selector
 mov si,0x74
 mov bp,OFFSET default_filename
 cmp byte ptr es:[document_path],0
 je set_save_name
 mov bp,OFFSET document_path
set_save_name:
 call write_text
 mov si,0x70
 jmp show_dialog
show_fill:
 mov si,0x80
show_dialog:
 mov word ptr [D_DIALOG],si
 mov ax,0x4197
 call ui_call
 cmp word ptr [D_DIALOG],0x70
 jne fill_focus_check
 mov si,0x74
 call focus_text
 jmp dialog_status
fill_focus_check:
 cmp word ptr [D_DIALOG],0x80
 jne dialog_status
 mov si,0x82
 call focus_text
 jmp dialog_status
dismiss_current:
 call dismiss_dialog
 jmp finish_ui
dialog_status:
 mov si,word ptr [D_DIALOG]
 cmp si,0x60
 jne save_status
 mov si,0x64
 jmp write_status
save_status:
 cmp si,0x70
 jne fill_status
 mov si,0x76
 jmp write_status
fill_status:
 cmp si,0x80
 jne finish_ui
 mov si,0x84
write_status:
 mov bp,OFFSET message
 call write_text
finish_ui:
 pop es
 pop bp
 pop di
 pop si
 pop dx
 pop cx
 pop bx
 pop ax
 call repaint
 ret

dismiss_dialog:
 push ax
 push si
 mov si,word ptr [D_DIALOG]
 or si,si
 jz dismiss_done
 mov word ptr [D_DIALOG],0
 mov ax,0x419b
 call ui_call
dismiss_done:
 pop si
 pop ax
 ret

init_selector:
 push ax
 push cx
 push dx
 push bp
 /* A zero native_path_ok leaves the selector free to use its own initial
    directory. It can still browse another disk and recover from failure. */
 cmp word ptr es:[native_path_ok],0
 je init_selector_done
 mov cx,es
 mov dx,OFFSET sheet_dir
 mov bp,word ptr es:[sheet_disk]
 mov ax,0x4203
 call ui_call
init_selector_done:
 pop bp
 pop dx
 pop cx
 pop ax
 ret

/* Runs one C action. Private SS is NEVER visible to enabled interrupts. */
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
 mov word ptr [E_ACTION],si
 mov ss,ax
 mov esp,STACK_TOP
 xor ebp,ebp
 cld
 movzx eax,si
 push eax
 .code16gcc
 call native_action
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

/* Inserted by the build tool at every C basic-block label and at most eight
 * ordinary instructions apart. This yields a valid GEOS interrupt/scheduler
 * context without trusting 1.x to preserve the upper halves of 386 registers. */
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
 .globl poll_interrupt_window
poll_interrupt_window:
 sti
 nop
 nop
 cli
 /* Do not rely on upper halves of ANY register across this window. */
 mov ax,ds
 mov ss,ax
 mov esp,dword ptr [E_ESP]
 pop es
 pop ds
 popad
 popfd
 .byte 0x66,0xc3

/* int native_file(op, p, count, q). Called with the C stack and IF clear.
 * All file services execute on the original native GEOS stack with IF set.
 * The C register state is saved BEFORE enabling interrupts. */
.globl native_file
native_file:
 pushfd
 pushad
 push ds
 push es
 mov dword ptr [E_ESP],esp
 mov ebp,esp
 /* 4 return + 4 flags + 32 regs + 4 segments = args at ESP+44. */
 mov ax,word ptr ss:[ebp+44]
 mov dx,word ptr ss:[ebp+48]
 mov cx,word ptr ss:[ebp+52]
 mov bx,word ptr ss:[ebp+56]
 mov di,bx
 mov si,ax
 mov ax,word ptr [E_SS]
 mov bp,word ptr [E_SP]
 mov ss,ax
 mov sp,bp
 sti
 cmp si,0
 je f_open
 cmp si,1
 je f_create
 cmp si,2
 je f_read
 cmp si,3
 je f_write
 cmp si,4
 je f_close
 cmp si,5
 je f_rename
 cmp si,6
 je f_delete
 cmp si,7
 je f_push_directory
 cmp si,8
 je f_pop_directory
 mov ax,1
 stc
 jmp f_result
f_open:
 mov ax,0x00c0
 K 0x34
 jmp f_result
f_create:
 mov ax,0x02c1
 xor cx,cx
 K 0x35
 jmp f_result
f_read:
 xor ax,ax
 K 0x3a
 jnc f_count
 cmp ax,128
 je f_count
 stc
 jmp f_result
f_write:
 xor ax,ax
 K 0x3b
 jnc f_count
 cmp ax,128
 je f_count
 stc
 jmp f_result
f_count:
 mov ax,cx
 clc
 jmp f_result
f_close:
 xor ax,ax
 K 0x36
 jc f_result
 xor ax,ax
 jmp f_result
f_rename:
 K 0x39
 jc f_result
 xor ax,ax
 jmp f_result
f_delete:
 K 0x38
 jc f_result
 xor ax,ax
 jmp f_result
f_push_directory:
 push dx
 push cx
 K 0x49
 pop bx
 pop dx
 K 0x33
 jnc f_directory_ok
 push ax
 K 0x4a
 pop ax
 stc
 jmp f_result
f_pop_directory:
 K 0x4a
f_directory_ok:
 xor ax,ax
 clc
f_result:
 cli
 /* Store carry and AX using only 16-bit operations before restoring C regs. */
 pushf
 pop dx
 mov cx,ax
 mov ax,ds
 mov ss,ax
 mov esp,dword ptr [E_ESP]
 movzx eax,cx
 test dx,1
 jz f_restore
 cmp ax,130
 jne f_neg
 mov eax,80
f_neg:
 neg eax
f_restore:
 /* Saved EAX is at ESP+32: 4 bytes segment slots + 28 into pushad. */
 mov dword ptr ss:[esp+32],eax
 pop es
 pop ds
 popad
 popfd
 .byte 0x66,0xc3

repaint:
 mov di,word ptr [D_WINDOW]
 or di,di
 jz repaint_done
 K 211
 call draw_native
 K 212
repaint_done:
 ret

/* Render the C-generated display list through the actual GEOS graphics API. */
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
 je draw_cpu_error
 ENGINE_AX
 mov ds,ax
 mov cx,0x1a00
 mov dx,10
 xor ah,ah
 K 366
 mov ax,0xff00
 K 362
 mov si,OFFSET drawing
 mov bp,word ptr [drawing_count]
 cmp bp,112
 jbe draw_loop
 mov bp,112
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
 draw_cpu_error:
 mov cx,0x1a00
 mov dx,10
 xor ah,ah
 K 366
 xor ax,ax
 K 359
 mov si,0x200
 mov ax,5
 mov bx,10
 xor cx,cx
 K 330
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
