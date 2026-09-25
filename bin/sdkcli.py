#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,shutil,sys
from pathlib import Path
SDK=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SDK))
from pcgeos1.toolchain import doctor
from pcgeos1.buildsys import build
from pcgeos1.target import scan
from pcgeos1.geode import parse

def main():
    p=argparse.ArgumentParser(prog='pcgeos1',description='PC/GEOS 1.x SDK 0.1 experimental build tools')
    sp=p.add_subparsers(dest='cmd',required=True)
    sp.add_parser('doctor')
    b=sp.add_parser('build');b.add_argument('project',nargs='?',default='project.json');b.add_argument('--gwp',required=True);b.add_argument('--toolchain',choices=['auto','gnu','llvm'],default='auto');b.add_argument('--build-dir')
    n=sp.add_parser('new');n.add_argument('directory');n.add_argument('--name',default='Hello GEOS');n.add_argument('--permanent-name',default='hello');n.add_argument('--token',default='HLO1')
    i=sp.add_parser('inspect');i.add_argument('geo')
    t=sp.add_parser('scan-target');t.add_argument('--gwp',required=True);t.add_argument('--output')
    a=p.parse_args()
    if a.cmd=='doctor': print(json.dumps(doctor(),indent=2));return 0
    if a.cmd=='build': print(json.dumps(build(a.project,a.gwp,a.build_dir,a.toolchain),indent=2));return 0
    if a.cmd=='new':
        dst=Path(a.directory)
        if dst.exists():raise SystemExit('Destination already exists: '+str(dst))
        shutil.copytree(SDK/'templates/basic_view',dst)
        cfg=json.loads((dst/'project.json').read_text())
        cfg.update(long_name=a.name,permanent_name=a.permanent_name[:8],token=a.token[:4].ljust(4,' '),output=a.permanent_name.upper()+'.GEO')
        (dst/'project.json').write_text(json.dumps(cfg,indent=2)+'\n')
        print('Created',dst);return 0
    if a.cmd=='inspect':
        q=parse(Path(a.geo).read_bytes(),Path(a.geo).name)
        short={k:q[k] for k in ('size','sha256','format_version','long_name','release','protocol','permanent_name','permanent_extension','kernel_protocol','imports')};short['resources']=len(q['resources']);short['exports']=len(q['exports']);short['relocations']=len(q['relocations']);print(json.dumps(short,indent=2));return 0
    if a.cmd=='scan-target':
        rows=scan(a.gwp);text=json.dumps(rows,indent=2)+'\n'
        if a.output:Path(a.output).write_text(text)
        else:print(text,end='')
        return 0
if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as e:
        print('pcgeos1: error:',e,file=sys.stderr);raise SystemExit(1)
