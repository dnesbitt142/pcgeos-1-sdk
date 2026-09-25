#!/usr/bin/env python3
"""Build the hosted test adapter and run native/core tests. Not a GEOS boot.

GCC and Python 3.10+ required. Native instruction tests additionally need
Linux x86-64 and the modify_ldt system call. --host-only skips those tests.
"""
import argparse,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--host-only',action='store_true');a=p.parse_args()
    (ROOT/'BUILD').mkdir(exist_ok=True)
    subprocess.run(['gcc','-O2','-std=c99','-DCALC_SHARED','-DMINICALC_HOST_UI','-fPIC','-shared','-I',str(ROOT/'SRC'),*[str(ROOT/'SRC'/x) for x in ('core.c','document.c','native_ui.c')],str(ROOT/'TESTS/host_adapter.c'),'-o',str(ROOT/'BUILD/libminicalc.so')],check=True)
    patterns=['test_core.py','test_interface.py','test_structure.py']+([] if a.host_only else ['test_native.py'])
    for pattern in patterns:
        subprocess.run([sys.executable,'-m','unittest','discover','-s','TESTS','-p',pattern,'-v'],cwd=ROOT,check=True)
if __name__=='__main__':main()
