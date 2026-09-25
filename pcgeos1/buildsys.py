from __future__ import annotations
import hashlib,json,struct,tempfile
from pathlib import Path
from .toolchain import detect,flags_for
from .instrument import instrument
from .target import load_templates
from .geode import resource_bytes
from .ui import build_basic_ui
from .packer import package_from_skeleton

def sha(b):return hashlib.sha256(b).hexdigest()
def w(b,o,v):struct.pack_into('<H',b,o,v)

def load_project(path):
    p=Path(path); cfg=json.loads(p.read_text(encoding='utf-8')); root=p.parent.resolve()
    required=['long_name','permanent_name','token','output']
    for k in required:
        if k not in cfg:raise ValueError(f'project.json missing {k}')
    if not (1<=len(cfg['permanent_name'])<=8):raise ValueError('permanent_name must be 1..8 ASCII characters')
    if len(cfg['token'])!=4:raise ValueError('token must be exactly 4 ASCII characters')
    cfg['_root']=root
    return cfg

def _symbols(text):
    result={}
    for line in text.splitlines():
        p=line.split()
        if len(p)==3 and p[0] != 'U':
            try:result[p[2]]=int(p[0],16)
            except ValueError:pass
    return result

def build(project_path,gwp,build_dir=None,toolchain='auto'):
    cfg=load_project(project_path);root=cfg['_root'];sdk=Path(__file__).resolve().parents[1]
    out=(Path(build_dir) if build_dir else root/'build').resolve();out.mkdir(parents=True,exist_ok=True)
    tc=detect(toolchain);flags=flags_for(tc)+cfg.get('cflags',[])
    templates=load_templates(gwp,strict=not cfg.get('allow_unknown_target',False))
    spin,spinq,_=templates['SPINTEXT.GEO']; viewer,viewerq,_=templates['VIEWER.GEO']
    help_path=root/cfg.get('help','src/help.txt');help_text=help_path.read_text(encoding='ascii') if help_path.exists() else cfg['long_name']
    ui3,ui4,uimap=build_basic_ui(resource_bytes(spin,spinq,3),resource_bytes(spin,spinq,4),
                                  resource_bytes(viewer,viewerq,12),resource_bytes(viewer,viewerq,28),
                                  cfg['long_name'],help_text,*cfg.get('viewport',[500,300]))
    sources=[root/p for p in cfg.get('sources',['src/app.c'])]
    sources.append(sdk/'runtime/sdk_runtime.c')
    objects=[];instrumentation={}
    for src in sources:
        name=src.stem+('_sdk' if src.name=='sdk_runtime.c' else '')
        raw=out/(name+'.raw.s');asm=out/(name+'.s');obj=out/(name+'.o')
        tc.compile_c_to_asm(src,raw,flags+['-I'+str(sdk/'include')])
        txt,rep=instrument(raw.read_text(encoding='utf-8',errors='replace'));asm.write_text(txt,encoding='utf-8')
        instrumentation[name]=rep;tc.assemble(asm,obj);objects.append(obj)
    # Skeleton has 11 resources; our appended engine is resource 11.
    native_obj=out/'native.o';tc.assemble(sdk/'runtime/native.S',native_obj,defines=['ENGINE_RESOURCE_ID=11']);objects.insert(0,native_obj)
    elf=out/'app.elf';tc.link(sdk/'runtime/native.ld',elf,out/'app.map',objects)
    nm=tc.symbols(elf);syms=_symbols(nm)
    for sec in ('text','data'):tc.extract(elf,sec,out/(sec+'.bin'))
    code=(out/'text.bin').read_bytes();edata=(out/'data.bin').read_bytes()
    used=syms.get('__engine_used');
    if used is None:raise ValueError('Linker did not produce __engine_used')
    if used>=54000:raise ValueError('Engine data/BSS exceeds SDK private-stack safety limit')
    engine=bytearray(65520);engine[:4]=b'PGS1';w(engine,4,0x0001);w(engine,20,used);engine[0x100:0x100+len(edata)]=edata
    result,info,pack=package_from_skeleton(spin,code,bytes(engine),ui3,ui4,syms,cfg)
    output=root/cfg['output'];output.write_bytes(result)
    report={'sdk_version':'0.1','status':'experimental; exact target template build required','project':cfg['long_name'],
            'output':str(output),'sha256':sha(result),'bytes':len(result),'toolchain':{'family':tc.family,'version':tc.version},
            'kernel_protocol':info['kernel_protocol'],'imports':info['imports'],'resources':len(info['resources']),
            'code_bytes':len(code),'engine_used':used,'instrumentation':instrumentation,'ui':uimap,'pack':pack,
            'target_templates':{k:v[2] for k,v in templates.items()}}
    (out/'build-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    (out/'symbols.txt').write_text(nm,encoding='utf-8')
    return report
