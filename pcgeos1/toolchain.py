from __future__ import annotations
import os, platform, shutil, subprocess
from dataclasses import dataclass

@dataclass
class Toolchain:
    family: str
    cc: str
    ld: str
    nm: str
    objcopy: str
    version: str

    def compile_c_to_asm(self, src, out, flags):
        if self.family == 'gnu':
            cmd=[self.cc,*flags,'-S',str(src),'-o',str(out)]
        else:
            cmd=[self.cc,'--target=i386-unknown-none-elf','-m16',*flags,'-S',str(src),'-o',str(out)]
        subprocess.run(cmd,check=True)

    def assemble(self, src, out, defines=()):
        if self.family == 'gnu':
            cmd=[self.cc,'-m32',*(f'-D{x}' for x in defines),'-c',str(src),'-o',str(out)]
        else:
            cmd=[self.cc,'--target=i386-unknown-none-elf','-m16',*(f'-D{x}' for x in defines),'-c',str(src),'-o',str(out)]
        subprocess.run(cmd,check=True)

    def link(self, script, out, mapfile, objects):
        cmd=[self.ld,'-m','elf_i386','--no-check-sections','--gc-sections','-T',str(script),'-Map',str(mapfile),'-o',str(out),*map(str,objects)]
        subprocess.run(cmd,check=True)

    def symbols(self, elf):
        return subprocess.check_output([self.nm,'-n',str(elf)],text=True)

    def extract(self, elf, section, out):
        subprocess.run([self.objcopy,'-O','binary','-j','.'+section,str(elf),str(out)],check=True)

COMMON_FLAGS=['-Os','-std=c99','-ffreestanding','-fno-builtin','-fno-pic','-fno-stack-protector',
              '-fno-asynchronous-unwind-tables','-fno-unwind-tables','-fno-ident','-mno-sse','-mno-mmx',
              '-msoft-float','-ffunction-sections','-fdata-sections','-Wall','-Wextra']
GNU_FLAGS=['-m16','-march=i386','-fno-pie','-mpreferred-stack-boundary=2','-mincoming-stack-boundary=2',
           '-fno-tree-loop-distribute-patterns'] + COMMON_FLAGS
LLVM_FLAGS=['-march=i386','-fno-pie'] + COMMON_FLAGS

def _which_many(names):
    for n in names:
        p=shutil.which(n)
        if p:return p
    return None

def detect(preference='auto'):
    preference=preference.lower()
    candidates=[]
    if preference in ('auto','gnu') and os.name!='nt':
        cc=_which_many(['gcc']); ld=_which_many(['ld']); nm=_which_many(['nm']); oc=_which_many(['objcopy'])
        if all((cc,ld,nm,oc)):
            ver=subprocess.check_output([cc,'--version'],text=True,errors='replace').splitlines()[0]
            candidates.append(Toolchain('gnu',cc,ld,nm,oc,ver))
    if preference in ('auto','llvm'):
        cc=_which_many(['clang','clang.exe']); ld=_which_many(['ld.lld','ld.lld.exe'])
        nm=_which_many(['llvm-nm','llvm-nm.exe','nm' if os.name!='nt' else '__missing__'])
        oc=_which_many(['llvm-objcopy','llvm-objcopy.exe'])
        if all((cc,ld,nm,oc)):
            ver=subprocess.check_output([cc,'--version'],text=True,errors='replace').splitlines()[0]
            candidates.append(Toolchain('llvm',cc,ld,nm,oc,ver))
    if not candidates:
        hint = ('Install GCC + GNU binutils on Linux, or LLVM (clang, lld, llvm-nm, llvm-objcopy) on Windows. '
                'Windows users may alternatively run the Linux toolchain under WSL2.')
        raise RuntimeError('No supported toolchain found. '+hint)
    return candidates[0]

def flags_for(tc):
    return GNU_FLAGS if tc.family=='gnu' else LLVM_FLAGS

def doctor():
    result={'platform':platform.platform(),'python':platform.python_version(),'toolchains':[]}
    for pref in ('gnu','llvm'):
        try:
            t=detect(pref);result['toolchains'].append({'family':t.family,'cc':t.cc,'ld':t.ld,'nm':t.nm,'objcopy':t.objcopy,'version':t.version})
        except Exception as e:
            result['toolchains'].append({'family':pref,'available':False,'error':str(e)})
    return result
