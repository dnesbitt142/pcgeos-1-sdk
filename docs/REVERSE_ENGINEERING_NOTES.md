# Reverse Engineering Notes

The SDK was derived from several concrete PC/GEOS 1.x/2.x investigations.

## Findings that shaped the SDK

- 1.x and 2.x geode containers are structurally different; changing a signature or protocol field is not a valid backport.
- Specific UI and generic UI protocols are meaningful ABI boundaries.
- Imported function ordinals must be validated against the exact target export table; an in-range number still does not prove semantic compatibility.
- Native UI object instance layouts are safer to recover from matching target applications than to guess from later source revisions.
- Native Help in the target can be built from the Viewer's title-bar trigger/hint plus its scrollable help dialog; it is not necessary to imitate Help in application drawing.
- Native GenFileSelector controls provide correct drive/directory behavior and should be preferred to custom browser widgets.
- Modern `-m16` compilation is practical for 386+ systems but needs a carefully isolated native ABI bridge.
- File services should execute on the original GEOS stack, not a compiler-private stack.
- Reproducible builds, input hashes and relocation audits are essential when the historical SDK is not used.

## Later public source trees

Public PC/GEOS source code is valuable for understanding structures and semantics, but it may represent later releases. SDK 0.1 therefore treats the exact target binaries as authoritative for private UI layouts and recovered message/interface details.
