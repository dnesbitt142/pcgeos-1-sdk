# Build System Internals

## `pcgeos1 build`

The generic builder is implemented by `pcgeos1/buildsys.py`.

### Inputs

- `project.json`
- project C sources
- SDK runtime sources
- user-supplied target archive

### Target stage

`pcgeos1/target.py` opens the archive without extracting arbitrary paths and loads exactly identified members. Known template hashes are checked by default.

### Compilation stage

Each C source is compiled to assembly rather than directly to an object. This deliberate intermediate step lets the SDK instrument control flow with `native_poll` calls.

The transformed assembly is then assembled into 32-bit ELF relocatable objects. The handwritten native adapter is assembled separately.

### Link stage

`runtime/native.ld` creates an ELF intermediate with:

- `.text` beginning at offset 0;
- `.data` beginning at private-engine offset 0x100;
- `.bss` following `.data` but not stored in the ELF binary extraction;
- `__engine_used` marking the end of initialized plus uninitialized engine state.

The linker asserts that code and engine state leave suitable 64 KiB headroom.

### Extraction stage

The builder extracts raw `.text` and `.data`. It allocates a 65,520-byte private engine resource, writes a small SDK tag at the start, and places initialized C data at offset 0x100. BSS starts zero because the resource is created zero-filled.

### Symbol stage

`nm`/`llvm-nm` output is parsed to find:

- process entry points;
- `__engine_used`;
- `krel_*` kernel relocation sites;
- `rrel_*` resource relocation sites.

### Packaging stage

`pcgeos1/packer.py` starts from the known 1.x skeleton. It preserves the native import table and unchanged resources, replaces dgroup/code/UI resources, appends the engine resource, recalculates file positions, and writes relocation records.

The finished file is reparsed immediately and checked for:

- GEOS 1.x format;
- unchanged import table;
- unchanged kernel protocol;
- valid resource/relocation bounds.

### Build evidence

The builder writes:

```text
build/build-report.json
build/app.map
build/symbols.txt
build/*.s
build/*.o
build/app.elf
build/text.bin
build/data.bin
```

Keep these files when reporting a runtime failure.
