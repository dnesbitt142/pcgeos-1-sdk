# GEOS Executable Format Notes

`pcgeos1/geode.py` is a bounds-checked reader for the GEOS 1.x and 2.x executable layouts encountered during this work. It is not a loader.

## GEOS 1.x

The known 1.x geodes use signature bytes:

```text
C7 45 CF 53
```

The executable header starts at byte 200. Resource file positions are absolute.

## GEOS 2.x

The observed 2.x files use:

```text
C7 45 C1 53
```

The executable header starts at byte 256, and stored resource positions require the 256-byte header origin adjustment.

## Tables

The parser reads:

- imported libraries
- exported entry table
- resource size table
- resource file-position table
- relocation-size table
- resource flags
- relocation records

It verifies duplicate count fields, resource bounds, overlap, import indices and relocation target bounds.

## Relocation records

Each observed relocation record is four bytes:

```text
info, extra, target_offset
```

The upper nibble of `info` identifies the source class; the lower nibble identifies the relocation type. SDK 0.1 emits kernel far-call and resource relocations needed by its runtime.

## Packer strategy

The SDK starts from a known native 1.x application skeleton, preserves its import table and compatible resources, replaces dgroup/code/UI resources, appends a private engine resource, and rewrites the resource descriptor table and payload positions.

This is safer than manufacturing every undocumented header field from zero in the first SDK release.
