# Adding Another PC/GEOS 1.x Target Profile

SDK 0.1 intentionally locks native object templates to a known GeoWorks Pro 1.2 build. Supporting another Ensemble/GeoWorks 1.x release should be done as a new profile, not by weakening validation.

## Procedure

1. Run `pcgeos1 scan-target` and save the full inventory.
2. Identify the kernel protocol and generic UI library protocol.
3. Locate a small native application with a primary window and GenView.
4. Locate native examples of every additional control you need: menu, trigger, text field, file selector, interaction, Help, and so on.
5. Hash those donor binaries and preserve an unmodified archive.
6. Compare resource layouts and object chunks against the existing profile.
7. Disassemble message handlers to confirm message numbers and calling conventions where they cross into custom code.
8. Add profile-specific hashes and chunk metadata instead of changing the existing profile in place.
9. Build a minimal Hello application and validate structure.
10. Boot-test open, redraw, keyboard, pointer, Help, close, repeated launch, and low-memory behavior.

## Evidence expected for a contributed profile

- target release identity and archive hash;
- kernel/UI protocols;
- hashes of every donor binary;
- object chunk provenance;
- build self-test output;
- real GEOS runtime test notes;
- any differences from the 622.3 / UI 693.0 profile.
