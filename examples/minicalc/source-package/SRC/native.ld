OUTPUT_FORMAT("elf32-i386")
ENTRY(native_open)
SECTIONS {
  . = 0;
  .text : { KEEP(*(.native)) *(.text*) }
  __code_size = SIZEOF(.text);
  .data 0x0100 : AT((__code_size + 15) & ~15) { *(.data*) *(.rodata*) }
  .bss (NOLOAD) : { __bss_start = .; *(.bss*) *(COMMON) __bss_end = .; }
  __engine_used = __bss_end;
  /DISCARD/ : { *(.eh_frame*) *(.comment*) *(.note*) }
  ASSERT(__code_size < 60000, "Native code resource exceeds limit")
  ASSERT(__bss_end < 54000, "Engine leaves insufficient private stack")
}
