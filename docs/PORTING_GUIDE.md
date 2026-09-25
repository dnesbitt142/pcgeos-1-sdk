# Porting Existing Code to SDK 0.1

## Good candidates

Applications with:

- self-contained calculations/data processing;
- simple native view drawing;
- keyboard and pointer interaction;
- modest memory requirements;
- 386+ target hardware.

## Harder candidates

Applications heavily dependent on undocumented class instance data, multiple imported libraries, object inheritance, dynamic object creation, text-engine internals, or later GEOS APIs.

## Recommended migration

1. Isolate platform-independent logic in ordinary C.
2. Replace libc dependencies with bounded local helpers or SDK functions.
3. Use `app_init`, `app_draw`, `app_key`, and `app_click` first.
4. Keep state in the private engine resource.
5. Add native services one at a time through assembly wrappers.
6. Recover UI controls from exact target applications before introducing them.
7. Add host tests for each state transition and file format.
8. Boot-test each milestone in a recoverable GEOS environment.

## Memory model cautions

Avoid assuming that arbitrary GEOS segments can be represented by C pointers. Use explicit copied buffers or native adapters. Keep individual geode resources under 64 KiB.
