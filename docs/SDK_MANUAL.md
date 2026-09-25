# PC/GEOS 1.x SDK 0.1 Manual

## Purpose

SDK 0.1 makes it possible to create experimental native PC/GEOS 1.x applications from modern Linux and Windows development machines without requiring the original historical compiler suite. It does this by combining modern freestanding x86 compilation with exact native object templates recovered from a known target installation.

This is deliberately a small, auditable SDK rather than a claim to recreate the complete GeoWorks development environment.

## Architecture

The build has five stages:

1. **Target verification** - hashes and parses native applications from the user-supplied archive.
2. **C compilation** - compiles application code in a freestanding 16-bit execution mode for a 386+ CPU.
3. **Native ABI bridge** - handwritten assembly enters/exits GEOS correctly and periodically restores a scheduler-safe native context.
4. **UI reconstruction** - builds local-memory object resources from exact 1.x templates.
5. **Geode packaging** - writes resources, imports, protocols, and relocation records in GEOS 1.x format.

## Why a target archive is required

The original generic UI object compiler and matching 1.x headers are not part of this SDK. Class instance layouts and private hints are therefore taken from exact native applications. SDK 0.1 uses:

- SPINTEXT.GEO for the process/application/primary/view skeleton
- VIEWER.GEO for title-bar Help and scrollable Help
- NOTEPAD.GEO and TERM.GEO in the advanced MiniCalc reference

This makes the basic shell look and behave like a native application, but it is version-specific.

## Modern compiler model

`-m16` does not turn GCC or Clang into an 8086 small-model compiler. The compiler still assumes 32-bit C arithmetic/register conventions, while the assembler emits instructions for a 16-bit code segment. Therefore:

- SDK-generated C applications require a 386 or newer CPU.
- C pointers are not general GEOS far pointers.
- GEOS services should be accessed through assembly adapters rather than called directly from C.
- Application state lives in a private appended resource with a private stack.

## Scheduler bridge

Instrumented C calls `native_poll` at basic blocks and after at most eight straight-line instructions. `native_poll` saves full 32-bit state, restores the real GEOS stack, enables interrupts briefly, then returns to the private application stack.

This was developed to avoid assuming that a 1.x scheduler preserves upper halves of 386 registers used by a modern compiler.

## Project file

`project.json` fields:

- `long_name`: user-visible application name, up to the geode long-name field limit.
- `permanent_name`: 1-8 ASCII characters; permanent geode identity.
- `token`: exactly four ASCII characters.
- `output`: output filename, normally uppercase `.GEO`.
- `release`: four 16-bit release numbers.
- `protocol`: two 16-bit application protocol numbers.
- `viewport`: `[width,height]` for the basic GenView shell.
- `sources`: C source files relative to the project.
- `help`: ASCII help text file.
- `native_stack_bytes`: native process stack requested in the geode header.
- `cflags`: optional additional compiler flags.
- `allow_unknown_target`: defaults false. Do not enable casually.

## Application callback API

The basic template implements four callbacks:

```c
void app_init(void);
void app_draw(void);
void app_key(void);
void app_click(void);
```

`app_draw` emits a list of simple draw commands. Pointer and keyboard callbacks inspect globals declared in `pcgeos1.h`.

## Native drawing subset

SDK 0.1 exposes rectangles and text:

```c
pcg_begin_frame();
pcg_rect(x1,y1,x2,y2,color);
pcg_text(x,y,color,"Hello");
```

The assembly renderer maps these to recovered kernel graphics entry points. This is intentionally a small surface that can be audited against the known target.

## Redraws

Call `pcg_invalidate()` after state changes. When a pointer or handled keyboard callback returns, the native adapter redraws the view if requested.

## Keyboard input

The basic GenView has the native 1.x send-control-characters bit enabled. `pcg_key_char` and `pcg_key_flags` receive the native message fields. Set `pcg_key_handled=1` if the application consumes the key; otherwise the message is forwarded to the superclass.

## Pointer input

`pcg_pointer_x`, `pcg_pointer_y`, and `pcg_pointer_info` receive the selector message values. The basic SDK does not yet normalize button/modifier bits into a higher-level portable event structure.

## Help

The project shell uses:

- the Viewer's native title-bar Help trigger and hint
- the Viewer's scrollable GenTextDisplay help dialog
- native Page Up, Page Down, and Close controls

The help text is embedded in the UI resource at build time.

## File I/O and complex dialogs

The basic runtime does not expose file I/O yet. The advanced MiniCalc reference contains a tested design for:

- native `FileOpen`, `FileCreate`, `FileRead`, `FileWrite`, `FileClose`, rename and delete wrappers
- directory push/pop behavior
- GenFileSelector-based native Open and Save As dialogs
- filename fields and reply bars
- transactional save/rollback logic

See `FILE_IO_AND_DIALOGS.md` and `examples/minicalc/`.

## Relocations

Assembly labels beginning `krel_` identify kernel far-call locations. Labels beginning `rrel_` identify resource references. The packer converts these symbol locations into GEOS relocation records.

The generic runtime currently uses only recovered kernel ordinals required for object dispatch, graphics, and the application superclass path.

## UI development strategy

There are three safe levels:

1. **Basic shell** - supported by SDK 0.1; use the generated native view and Help.
2. **Template composition** - copy exact controls from known target applications and modify generic tree links, monikers, actions, hints, dimensions and text.
3. **New class layouts** - not supported. Do not invent private instance structures without evidence.

## Debugging

Host-side debugging consists of:

- `pcgeos1 inspect` for geode headers/imports/resources
- `scan-target` for target inventory
- `build-report.json` for symbols, hashes and instrumentation
- `app.map` and `symbols.txt` for code offsets
- disassembly of `text.bin` with `objdump` or LLVM tools

Runtime debugging requires a DOS/GEOS test environment. Record loader messages, exact screen state, and whether failure occurs before or after the primary window appears.

## ABI stability policy for SDK 0.1

There is no stable binary ABI across SDK versions yet. Source compatibility is the goal, but the runtime, project schema, object templates and C API may change in 0.x releases. Pin SDK 0.1 for reproducible work.
