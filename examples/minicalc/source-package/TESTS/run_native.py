#!/usr/bin/env python3
import argparse,json,struct,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'TOOLS'))
from geode import parse,resource_bytes

def prepare(build):
 b=(ROOT/'MINICALC.GEO').read_bytes();q=parse(b)
 code=bytearray(resource_bytes(b,q,2));engine=resource_bytes(b,q,11);dg=resource_bytes(b,q,1)
 for r in q['relocations']:
  if r['resource']!=2:continue
  at=r['offset']
  if r['source']==0:
   ordinal=struct.unpack_from('<H',code,at)[0];struct.pack_into('<HH',code,at,4*ordinal,47)
  elif r['info']==0x22:struct.pack_into('<H',code,at,31)
  else:raise ValueError(r)
 build.mkdir(parents=True,exist_ok=True)
 (build/'relocated.bin').write_bytes(code);(build/'engine.bin').write_bytes(engine);(build/'dgroup.bin').write_bytes(dg)
 subprocess.run(['gcc','-O2','-Wall','-Wextra',str(ROOT/'TESTS/native_runner.c'),'-o',str(build/'native_runner')],check=True)
 return [str(build/'native_runner'),str(build/'relocated.bin'),str(build/'engine.bin'),str(build/'dgroup.bin'),str(ROOT/'EVIDENCE/SYMBOLS.txt')]
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('workdir',type=Path);p.add_argument('script',type=Path);p.add_argument('trace',type=Path);a=p.parse_args();command=prepare(ROOT/'TESTS/BUILD');subprocess.run(command+[str(a.workdir),str(a.script),str(a.trace)],check=True)
