# SDK Command-Line Reference

## `pcgeos1 doctor`

Reports Python/platform information and available GNU/LLVM toolchains.

## `pcgeos1 new DIRECTORY [options]`

Creates a new basic native-view project.

Options:

```text
--name "Long Name"
--permanent-name name8
--token ABC1
```

The permanent name is truncated to eight characters; choose a unique value yourself. The token must represent four characters.

## `pcgeos1 build [project.json] --gwp ARCHIVE`

Builds the project.

Options:

```text
--toolchain auto|gnu|llvm
--build-dir PATH
```

`auto` prefers GNU on non-Windows hosts when available, otherwise LLVM.

## `pcgeos1 inspect FILE.GEO`

Prints a compact JSON summary including format, names, release/protocol, imports, resource count, export count and relocation count.

## `pcgeos1 scan-target --gwp ARCHIVE [--output target.json]`

Parses every recognized `.GEO` in the archive and reports protocols/imports/resources. This is useful when developing a new target profile.

# Python modules

## `pcgeos1.geode`

Bounds-checked GEOS parser plus resource/relocation access helpers.

## `pcgeos1.target`

Known target hashes, safe archive-member lookup and target inventory.

## `pcgeos1.ui`

LMEM and basic native UI composition helpers.

## `pcgeos1.toolchain`

GNU/LLVM toolchain abstraction.

## `pcgeos1.instrument`

Compiler-generated assembly instrumentation for scheduler-safe polling.

## `pcgeos1.packer`

GEOS 1.x resource/header/relocation packer based on a known native skeleton.

## `pcgeos1.buildsys`

Generic project build orchestration.
