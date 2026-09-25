# Windows Host Setup

## Native Windows build with LLVM

Install Python 3.10+ and a current LLVM distribution containing:

```text
clang.exe
ld.lld.exe
llvm-nm.exe
llvm-objcopy.exe
```

Add both Python and LLVM `bin` directories to `PATH`.

From PowerShell:

```powershell
.\bin\pcgeos1.ps1 doctor
.\bin\pcgeos1.ps1 build project.json --gwp C:\GEOSDEV\GWP2.zip --toolchain llvm
```

The SDK tells Clang to target `i386-unknown-none-elf`, so it produces ELF objects rather than Windows PE/COFF application objects. LLD links those objects as `elf_i386`; the SDK then extracts the raw code/data and creates the GEOS file itself.

## Why not ordinary MinGW linking?

The SDK requires an ELF intermediate and explicit raw-section extraction. A normal MinGW link produces Windows-format output and does not match this pipeline. LLVM provides a consistent cross-platform path.

## WSL2 alternative

If native LLVM setup is inconvenient, install a Linux distribution under WSL2 and use the Linux GNU instructions. The resulting `.GEO` is independent of the host OS.

## Path notes

- Quote paths containing spaces.
- Keep project sources and the SDK on a normal local filesystem where possible.
- `project.json` uses forward or backward slash paths accepted by Python.

## Validation status in SDK 0.1

The LLVM build path was exercised end-to-end with Clang/LLD/LLVM objcopy producing the same GEOS structure as the GNU build, but that validation host was Linux. The PowerShell launcher and Windows executable-name detection are included for native Windows use; native Windows execution of the build driver should still be treated as release-candidate support until a Windows machine reproduces the Hello self-test.
