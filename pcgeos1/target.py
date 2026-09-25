from __future__ import annotations
import hashlib, zipfile
from pathlib import Path
from .geode import parse

KNOWN={
 'SPINTEXT.GEO':'848f5afb43a2184b01d2a4ad3231957b6ab9936006b23b4b2a260d1224d44370',
 'NOTEPAD.GEO':'edc48848ff4b9d2880e715bbb29532f14b3b54293c45159c467e33e2af841d1b',
 'VIEWER.GEO':'3d433a39c455a9cea242763dad0e3f681b4196fb7b1a75a08ca47e1aa8aa4a30',
 'TERM.GEO':'2d66ac2ff9fd24c4591303b2cba7cec6f40f0d52b4f3d75d9e0cdaa5fc1be542',
}
PATHS={
 'SPINTEXT.GEO':'/WORLD/EXTRAS/SPINTEXT.GEO',
 'NOTEPAD.GEO':'/WORLD/NOTEPAD.GEO',
 'VIEWER.GEO':'/WORLD/VIEWER.GEO',
 'TERM.GEO':'/WORLD/TERM.GEO',
}

def sha(b):return hashlib.sha256(b).hexdigest()

def member(z,end):
    names=[n for n in z.namelist() if n.replace('\\','/').upper().endswith(end)]
    if len(names)!=1:raise ValueError(f'Expected exactly one archive member ending {end}, got {len(names)}')
    return z.read(names[0])

def load_templates(gwp,strict=True):
    out={}
    with zipfile.ZipFile(gwp) as z:
        for name,end in PATHS.items():
            data=member(z,end); digest=sha(data)
            if strict and digest!=KNOWN[name]:
                raise ValueError(f'Unsupported {name}: SHA-256 {digest}; SDK 0.1 knows {KNOWN[name]}')
            out[name]=(data,parse(data,name),digest)
    return out

def scan(gwp):
    rows=[]
    with zipfile.ZipFile(gwp) as z:
        for zi in z.infolist():
            if zi.is_dir() or not zi.filename.lower().endswith('.geo'):continue
            data=z.read(zi)
            try:q=parse(data,zi.filename)
            except Exception:continue
            rows.append({'path':zi.filename,'sha256':sha(data),'format':q['format_version'],'name':q['permanent_name'],
                         'ext':q['permanent_extension'],'release':q['release'],'protocol':q['protocol'],
                         'kernel_protocol':q['kernel_protocol'],'imports':q['imports'],'resources':len(q['resources']),
                         'exports':len(q['exports'])})
    return rows
