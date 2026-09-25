# Target Compatibility

SDK 0.1 is validated against one GeoWorks Pro 1.2 target set.

## Required native interface

- GEOS 1.x executable format
- kernel protocol: `622.3`
- UI library protocol: `693.0`
- basic application skeleton: `SPINTEXT.GEO`

## Exact template hashes

| File | SHA-256 |
|---|---|
| SPINTEXT.GEO | `848f5afb43a2184b01d2a4ad3231957b6ab9936006b23b4b2a260d1224d44370` |
| NOTEPAD.GEO | `edc48848ff4b9d2880e715bbb29532f14b3b54293c45159c467e33e2af841d1b` |
| VIEWER.GEO | `3d433a39c455a9cea242763dad0e3f681b4196fb7b1a75a08ca47e1aa8aa4a30` |
| TERM.GEO | `2d66ac2ff9fd24c4591303b2cba7cec6f40f0d52b4f3d75d9e0cdaa5fc1be542` |

The generic basic-view build currently requires all four hashes even though it directly consumes only SPINTEXT and VIEWER. This is intentional: the target set is treated as a coherent known distribution.

## Unknown targets

`allow_unknown_target` exists for research, not routine application development. Disabling hash checks does not make private object layouts compatible.

To add a target properly:

1. scan every geode and record kernel/UI protocols;
2. identify native applications that contain the required object types;
3. recover exact object chunks and hints;
4. verify superclass/message behavior;
5. add target-specific hashes and tests;
6. keep target profiles separate if layouts differ.
