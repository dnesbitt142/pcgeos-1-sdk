# Getting Started

## 1. Install the host toolchain

### Linux

Install Python 3.10+ plus either:

- GCC with `-m16`, GNU `ld`, `nm`, and `objcopy`, or
- LLVM/Clang, LLD, `llvm-nm`, and `llvm-objcopy`.

Run:

```sh
./bin/pcgeos1 doctor
```

### Windows

The native Windows path uses LLVM because MinGW binutils do not reliably provide the ELF link/extract workflow used by this SDK.

Install:

- Python 3.10 or newer
- LLVM for Windows, including `clang.exe`, `ld.lld.exe`, `llvm-nm.exe`, and `llvm-objcopy.exe`

Ensure both Python and LLVM are on `PATH`, then run:

```powershell
.\bin\pcgeos1.ps1 doctor
```

WSL2 is also supported as a practical alternative: use the Linux instructions inside WSL.

## 2. Supply a compatible target archive

SDK 0.1 does not redistribute GeoWorks binaries. Point builds at your own `GWP2.zip` containing the exact target applications and libraries.

Verify it:

```sh
./bin/pcgeos1 scan-target --gwp /path/to/GWP2.zip --output target.json
```

The basic UI builder validates four template files by SHA-256. See `TARGET_COMPATIBILITY.md`.

## 3. Create a project

```sh
./bin/pcgeos1 new hello2 --name "Hello Two" --permanent-name hello2 --token HL02
cd hello2
```

The generated project contains:

```text
project.json
src/app.c
src/help.txt
```

## 4. Build

Linux auto-detection:

```sh
/path/to/pcgeos1-sdk-0.1/bin/pcgeos1 build project.json --gwp /path/to/GWP2.zip
```

Windows LLVM:

```powershell
C:\path\pcgeos1-sdk-0.1\bin\pcgeos1.ps1 build project.json --gwp C:\path\GWP2.zip --toolchain llvm
```

The output `.GEO` appears in the project directory. Detailed intermediate files and `build-report.json` appear under `build/`.

## 5. Inspect the result

```sh
./bin/pcgeos1 inspect hello2/HELLO2.GEO
```

Confirm:

- file format 1
- kernel protocol 622.3
- `ui` protocol 693.0
- expected permanent name and application token

## 6. Test in GEOS

Use a disposable or snapshotted installation.

1. Exit GEOS.
2. Copy the generated `.GEO` into a test `WORLD` directory.
3. Restart GEOS.
4. Launch it from GeoManager.
5. Test mouse, keyboard, redraw, title-bar Help, application close, and repeated launch.
6. If anything fails, record the exact error and restore the snapshot.

The SDK's host tests cannot certify loader/UI behavior in a real Ensemble session.
