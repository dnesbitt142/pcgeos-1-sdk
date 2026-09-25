#!/usr/bin/env python3
"""Build a genuine Ensemble 1.x geode with native UI/graphics/file adapters.
Requires GCC -m16, GNU binutils, Python 3.10+, and the exact supplied GWP2.zip.
No installed GEOS files or input archives are modified.
"""
import argparse,hashlib,json,re,struct,subprocess,zipfile
from pathlib import Path
from geode import parse,resource_bytes,relocation_bytes,u16,align16
from ui_builder import build_ui,chunk
ROOT=Path(__file__).resolve().parents[1]
SPIN_SHA='848f5afb43a2184b01d2a4ad3231957b6ab9936006b23b4b2a260d1224d44370'
FLAGS=['-m16','-march=i386','-Os','-std=c99','-ffreestanding','-fno-builtin','-fno-pic','-fno-pie','-fno-stack-protector','-fno-asynchronous-unwind-tables','-fno-unwind-tables','-fno-ident','-mno-sse','-mno-mmx','-msoft-float','-mpreferred-stack-boundary=2','-mincoming-stack-boundary=2','-ffunction-sections','-fdata-sections','-fno-tree-loop-distribute-patterns','-Wall','-Wextra','-Wno-misleading-indentation']
def run(*args):subprocess.run([str(x) for x in args],check=True,cwd=ROOT)
def sha(b):return hashlib.sha256(b).hexdigest()
def w(b,o,v):struct.pack_into('<H',b,o,v)
def instrument(s):
 out=[];intext=False;need=True;count=0;polls=0;instructions=0;repeats=0
 for line in s.splitlines():
  st=line.strip()
  if st.startswith('.section'):intext='.text' in st
  elif st=='.text':intext=True
  elif st in ('.data','.bss'):intext=False
  if intext and st.endswith(':'):need=True
  if intext and st and not st.startswith(('.', '#')) and not st.endswith(':'):
   op=st.split()[0]
   if op.startswith('rep'):
    suffix=st.split()[1]
    if op!='rep' or suffix not in ('movsl','movsb','stosb','stosl'):raise ValueError('Unsupported repeat: '+st)
    tag=f'.Lmc_repeat_{repeats}';repeats+=1
    out.extend(['\tpushfl',f'\tjecxz {tag}_done',tag+':','\tcall native_poll','\t'+suffix,'\tdecl %ecx',f'\tjnz {tag}',tag+'_done:','\tpopfl'])
    polls+=1;instructions+=1;need=True;count=0;continue
   if need or count>=8:out.append('\tcall\tnative_poll');polls+=1;need=False;count=0
   out.append(line);count+=1;instructions+=1
   if op.startswith('j') or op.startswith('call') or op.startswith('ret'):need=True
  else:out.append(line)
 return '\n'.join(out)+'\n',{'poll_sites':polls,'original_instructions':instructions,'bounded_repeat_expansions':repeats,'maximum_straight_line_instructions_between_polls':8}
def read_member(z,end):
 names=[x for x in z.namelist() if x.replace('\\','/').upper().endswith(end)]
 if len(names)!=1:raise ValueError('Expected exactly one '+end)
 return z.read(names[0])
def build(gwp,out):
 out.mkdir(parents=True,exist_ok=True);(ROOT/'EVIDENCE').mkdir(exist_ok=True)
 with zipfile.ZipFile(gwp) as z:
  original=read_member(z,'/WORLD/EXTRAS/SPINTEXT.GEO');note=read_member(z,'/WORLD/NOTEPAD.GEO');viewer=read_member(z,'/WORLD/VIEWER.GEO');term=read_member(z,'/WORLD/TERM.GEO')
 if sha(original)!=SPIN_SHA:raise ValueError('Unsupported native UI skeleton build')
 for name,data,wanted in [('NOTEPAD',note,'edc48848ff4b9d2880e715bbb29532f14b3b54293c45159c467e33e2af841d1b'),('VIEWER',viewer,'3d433a39c455a9cea242763dad0e3f681b4196fb7b1a75a08ca47e1aa8aa4a30'),('TERM',term,'2d66ac2ff9fd24c4591303b2cba7cec6f40f0d52b4f3d75d9e0cdaa5fc1be542')]:
  if sha(data)!=wanted:raise ValueError('Unsupported native '+name+' template build')
 q=parse(original,'SPINTEXT.GEO');nq=parse(note,'NOTEPAD.GEO')
 r3=resource_bytes(original,q,3);r4=resource_bytes(original,q,4)
 nt=chunk(resource_bytes(note,nq,7),0x3c)
 if nt[:4]!=bytes.fromhex('00304400') or len(nt)!=34:raise ValueError('Unsupported GenTrigger template')
 r3,r4,uimap=build_ui(r3,r4,nt,resource_bytes(note,nq,7),resource_bytes(viewer,parse(viewer),26),chunk(resource_bytes(term,parse(term),15),0x28),resource_bytes(viewer,parse(viewer),12),resource_bytes(viewer,parse(viewer),28),(ROOT/'SRC/HELP.TXT').read_text(encoding='ascii'))
 sourcehash=sha(b''.join(p.name.encode()+p.read_bytes() for p in sorted((ROOT/'SRC').glob('*'))))
 tag=int(sourcehash[:8],16)
 objects=[];instrumentation={}
 for name in ('core','document','runtime','native_ui'):
  raw=out/(name+'.raw.s');asm=out/(name+'.s');obj=out/(name+'.o')
  run('gcc',*FLAGS,'-S',ROOT/'SRC'/(name+'.c'),'-o',raw)
  text,report=instrument(raw.read_text());asm.write_text(text);instrumentation[name]=report
  run('gcc','-m32','-c',asm,'-o',obj);objects.append(obj)
 obj=out/'native.o';run('gcc','-m32','-DSTATE_TAG='+hex(tag),'-c',ROOT/'SRC/native.S','-o',obj);objects.insert(0,obj)
 elf=out/'MINICALC.elf';run('ld','-m','elf_i386','--no-check-sections','--gc-sections','-T',ROOT/'SRC/native.ld','-Map',out/'MINICALC.map','-o',elf,*objects)
 nm=subprocess.check_output(['nm','-n',str(elf)],text=True)
 syms={p[2]:int(p[0],16) for l in nm.splitlines() if len(p:=l.split())==3 and p[0]!='U'}
 for sec in ('text','data'):run('objcopy','-O','binary','-j','.'+sec,elf,out/(sec+'.bin'))
 code=(out/'text.bin').read_bytes();edata=(out/'data.bin').read_bytes()
 engine=bytearray(65520);engine[0:4]=b'MCN2';w(engine,4,0x0201);w(engine,20,syms['__engine_used']);struct.pack_into('<I',engine,28,tag);engine[0x100:0x100+len(edata)]=edata
 methods=[(0xa01,'native_open'),(0xa03,'native_close'),(4,'native_attach'),(0x57,'native_view_closed'),(0x49,'native_expose')]+[(0xc3,'native_select'),(0x7b,'native_key')]+[(0xc00+i,'native_command') for i in list(range(1,12))+list(range(15,26))+[29]]
 dg=bytearray(1024);odg=resource_bytes(original,q,1);dg[:0x40]=odg[:0x40];w(dg,0x14,1024);dg[0x40:0x52]=odg[0x40:0x52];w(dg,0x46,len(methods))
 drels=[(0x11,0,0x40),(0x12,0,0x42)]
 for i,(msg,name) in enumerate(methods):
  w(dg,0x52+2*i,msg);a=0x52+2*len(methods)+4*i;w(dg,a,syms[name]);w(dg,a+2,2);drels.append((0x22,0,a+2))
 err=b'MiniCalc Native requires a 386 or newer CPU. No files were changed.\0';dg[0x200:0x200+len(err)]=err
 crels=[]
 for name,addr in syms.items():
  if name.startswith('krel_'):crels.append((0,0,addr))
  if name.startswith('rrel_'):crels.append((0x22,0,addr))
 crels.sort(key=lambda r:r[2])
 def enc(rs):return b''.join(struct.pack('<BBH',*r) for r in rs)
 resources=[]
 for r in q['resources']:
  i=r['id'];resources.append([resource_bytes(original,q,i),relocation_bytes(original,q,i),r['flags']])
 resources[1]=[bytes(dg),enc(drels),0x80];resources[2]=[code,enc(crels),q['resources'][2]['flags']]
 resources[3][0]=r3;resources[4][0]=r4
 resources.append([bytes(engine),b'',0x80])
 header=bytearray(original[:q['resource_table_at']]);N=len(resources)
 header[32:68]=b'MiniCalc Native'.ljust(36,b'\0');struct.pack_into('<4H',header,8,0,4,0,1);struct.pack_into('<2H',header,16,1,0);header[20:24]=b'MC1N'
 header[244:252]=b'mcalc1  ';header[252:256]=b'app ';header[256:260]=b'MC1N'
 struct.pack_into('<4H',header,230,0,4,0,1);struct.pack_into('<2H',header,238,1,0)
 # One live worksheet instance: absolute engine-resource fixups must not be
 # shared across independent launches of this prototype.
 attrs=u16(header,200)&~0x0400;w(header,200,attrs);w(header,226,attrs)
 w(header,208,N);w(header,280,N);w(header,214,8192)
 table=bytearray(10*N);payload=bytearray();pos=len(header)+len(table)
 for i,(data,relocs,flags) in enumerate(resources):
  w(table,2*i,len(data));struct.pack_into('<I',table,2*N+4*i,pos);w(table,6*N+2*i,len(relocs));w(table,8*N+2*i,flags)
  block=data+b'\0'*(align16(len(data))-len(data))+relocs;payload+=block;pos+=len(block)
 result=bytes(header+table+payload);info=parse(result,'MINICALC.GEO')
 assert info['format_version']==1 and info['imports']==q['imports'] and info['kernel_protocol']==[622,3]
 (ROOT/'MINICALC.GEO').write_bytes(result)
 report={'status':'native Ensemble 1.x prototype; not boot-tested','input_skeleton_sha256':sha(original),'input_notepad_sha256':sha(note),'input_viewer_sha256':sha(viewer),'input_terminal_sha256':sha(term),'source_sha256':sourcehash,'state_tag':tag,'sha256':sha(result),'geode_bytes':len(result),'code_bytes':len(code),'engine_resource_bytes':len(engine),'engine_data_end':syms['__engine_used'],'private_stack_headroom':65504-syms['__engine_used'],'native_uninitialized_and_stack_bytes':8192,'cpu':'80386 or newer','kernel_protocol':info['kernel_protocol'],'imports':info['imports'],'methods':[dict(message=m,handler=h,offset=syms[h]) for m,h in methods],'ui':uimap,'instrumentation':instrumentation,'symbol_offsets':syms,'kernel_ordinals':sorted({u16(code,r[2]) for r in crels if r[0]==0}),'kernel_relocation_count':sum(r[0]==0 for r in crels),'resource_count':N,'dos_or_bios_interrupt_instructions':0,'note':'No 2.x libraries; no MINICALC.EXE is loaded. The source uses native GEOS calls only.'}
 (ROOT/'EVIDENCE/BUILD.json').write_text(json.dumps(report,indent=2)+'\n');(ROOT/'EVIDENCE/STRUCTURE.json').write_text(json.dumps(info,indent=2)+'\n');(ROOT/'EVIDENCE/SYMBOLS.txt').write_text(nm)
 (out/'engine.bin').write_bytes(engine);(out/'dgroup.bin').write_bytes(dg)
 print(json.dumps({k:v for k,v in report.items() if k not in ('symbol_offsets','methods','imports','ui')},indent=2))
 return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--gwp',required=True,type=Path);p.add_argument('--out',type=Path,default=ROOT/'BUILD');a=p.parse_args();build(a.gwp,a.out.resolve())
