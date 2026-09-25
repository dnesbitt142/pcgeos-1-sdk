#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,shutil,subprocess,sys,tempfile
from pathlib import Path
SDK=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SDK))
from pcgeos1.geode import parse
from pcgeos1.target import load_templates
from pcgeos1.toolchain import detect
from pcgeos1.buildsys import build

def run(gwp,all_toolchains=False):
    results={'target_templates':{},'builds':[]}
    t=load_templates(gwp)
    results['target_templates']={k:v[2] for k,v in t.items()}
    families=['gnu','llvm'] if all_toolchains else ['auto']
    for fam in families:
        if fam!='auto':
            try:detect(fam)
            except Exception as e:
                results['builds'].append({'toolchain':fam,'skipped':str(e)});continue
        with tempfile.TemporaryDirectory() as td:
            proj=Path(td)/'hello';shutil.copytree(SDK/'examples/hello',proj,ignore=shutil.ignore_patterns('build-*','HELLO.GEO','build'))
            report=build(proj/'project.json',gwp,proj/'build',fam)
            data=(proj/'HELLO.GEO').read_bytes();q=parse(data,'HELLO.GEO')
            assert q['format_version']==1
            assert q['kernel_protocol']==[622,3]
            assert [(x['name'],x['protocol']) for x in q['imports']]==[('ui',[693,0])]
            assert q['permanent_name'].strip()=='hello'
            assert len(q['resources'])==12
            results['builds'].append({'toolchain':report['toolchain'],'sha256':report['sha256'],'bytes':len(data),'resources':len(q['resources']),'relocations':len(q['relocations'])})
    return results

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--gwp',required=True,type=Path);p.add_argument('--all-toolchains',action='store_true');a=p.parse_args()
    result=run(a.gwp,a.all_toolchains);print(json.dumps(result,indent=2));
