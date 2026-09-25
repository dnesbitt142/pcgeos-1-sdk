# Linux Host Setup

## GNU path

Required commands:

```text
gcc
ld
nm
objcopy
python3
```

The GCC build uses `-m16`, assembles the generated source as 32-bit ELF objects, links with `ld -m elf_i386`, then extracts raw `.text` and `.data` sections.

Check:

```sh
./bin/pcgeos1 doctor
```

Build with an explicit GNU toolchain:

```sh
./bin/pcgeos1 build project.json --gwp /path/GWP2.zip --toolchain gnu
```

## LLVM path

LLVM is also supported on Linux and is useful for matching the Windows build path:

```text
clang
ld.lld
llvm-nm (GNU nm is accepted on Linux as a fallback)
llvm-objcopy
```

```sh
./bin/pcgeos1 build project.json --gwp /path/GWP2.zip --toolchain llvm
```

GNU and LLVM outputs are not expected to be byte-identical because code generation differs. Their geode interfaces and resource invariants should match.
