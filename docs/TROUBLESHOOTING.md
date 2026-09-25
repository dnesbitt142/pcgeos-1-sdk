# Troubleshooting

## `No supported toolchain found`

Run `pcgeos1 doctor`.

Linux: install GCC/binutils or LLVM.

Windows: install LLVM with Clang, LLD, llvm-nm and llvm-objcopy, or use WSL2.

## `Unsupported native ... template build`

Your target archive does not match the SDK 0.1 profile. Do not simply disable the check for production. See `TARGET_COMPATIBILITY.md`.

## Application does not appear in GeoManager

Check:

- `.GEO` is in the expected `WORLD` directory;
- only one copy with that identity is active;
- permanent name and token are unique;
- the target installation matches the expected kernel/UI protocols.

## GEOS error during launch

Use `pcgeos1 inspect APP.GEO` and save `build/build-report.json`, `build/app.map`, and `build/symbols.txt`. Record the exact error before modifying the build.

## Window appears but drawing is blank

Confirm `app_draw()` emits commands and that the view receives expose events. Compare with `examples/hello`.

## Keyboard does not reach the application

The generic view must retain the send-control-characters flag. Do not replace the GenView template without checking that field.

## Crashes only after some interaction

Suspect ABI crossings first. Do not call arbitrary kernel/UI ordinals directly from C. Keep native services behind an assembly adapter that restores the expected GEOS stack/context.

## LLVM build works but differs from GCC

Different machine code is normal. Compare structural output with `pcgeos1 inspect`; do not require identical hashes across compilers.
