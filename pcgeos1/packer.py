from __future__ import annotations
import struct
from .geode import parse,resource_bytes,relocation_bytes,u16,align16

def w(b,o,v):struct.pack_into('<H',b,o,v)

def encode_relocs(rs):return b''.join(struct.pack('<BBH',*r) for r in rs)

def package_from_skeleton(original,code,engine,ui3,ui4,symbols,project):
    q=parse(original,'SPINTEXT.GEO')
    methods=[(0xa01,'native_open'),(0xa03,'native_close'),(4,'native_attach'),(0x57,'native_view_closed'),
             (0x49,'native_expose'),(0xc3,'native_select'),(0x7b,'native_key'),(0xc0a,'native_command')]
    missing=[n for _,n in methods if n not in symbols]
    if missing:raise ValueError('Runtime is missing method symbols: '+', '.join(missing))
    dg=bytearray(project.get('dgroup_bytes',512));odg=resource_bytes(original,q,1);dg[:min(0x40,len(dg))]=odg[:min(0x40,len(dg))]
    w(dg,0x14,len(dg));dg[0x40:0x52]=odg[0x40:0x52];w(dg,0x46,len(methods))
    drels=[(0x11,0,0x40),(0x12,0,0x42)]
    for i,(msg,name) in enumerate(methods):
        w(dg,0x52+2*i,msg);a=0x52+2*len(methods)+4*i;w(dg,a,symbols[name]);w(dg,a+2,2);drels.append((0x22,0,a+2))
    crels=[]
    for name,addr in symbols.items():
        if name.startswith('krel_'):crels.append((0,0,addr))
        elif name.startswith('rrel_'):crels.append((0x22,0,addr))
    crels.sort(key=lambda r:r[2])
    resources=[[resource_bytes(original,q,r['id']),relocation_bytes(original,q,r['id']),r['flags']] for r in q['resources']]
    resources[1]=[bytes(dg),encode_relocs(drels),0x80];resources[2]=[code,encode_relocs(crels),q['resources'][2]['flags']]
    resources[3][0]=ui3;resources[4][0]=ui4;resources.append([engine,b'',0x80])
    header=bytearray(original[:q['resource_table_at']]);N=len(resources)
    long=project['long_name'].encode('ascii','replace')[:35];header[32:68]=long.ljust(36,b'\0')
    rel=project.get('release',[0,1,0,0]);proto=project.get('protocol',[1,0]);token=project.get('token','SDK1').encode('ascii')[:4].ljust(4,b' ')
    perm=project['permanent_name'].encode('ascii')[:8].ljust(8,b' ')
    struct.pack_into('<4H',header,8,*rel);struct.pack_into('<2H',header,16,*proto);header[20:24]=token
    header[244:252]=perm;header[252:256]=b'app ';header[256:260]=token
    struct.pack_into('<4H',header,230,*rel);struct.pack_into('<2H',header,238,*proto)
    attrs=u16(header,200)&~0x0400;w(header,200,attrs);w(header,226,attrs)
    w(header,208,N);w(header,280,N);w(header,214,project.get('native_stack_bytes',8192))
    table=bytearray(10*N);payload=bytearray();pos=len(header)+len(table)
    for i,(data,relocs,flags) in enumerate(resources):
        if len(data)>65535:raise ValueError(f'Resource {i} exceeds 64K')
        w(table,2*i,len(data));struct.pack_into('<I',table,2*N+4*i,pos);w(table,6*N+2*i,len(relocs));w(table,8*N+2*i,flags)
        block=data+b'\0'*(align16(len(data))-len(data))+relocs;payload+=block;pos+=len(block)
    result=bytes(header+table+payload);info=parse(result,project['output'])
    if info['format_version']!=1 or info['imports']!=q['imports'] or info['kernel_protocol']!=q['kernel_protocol']:
        raise ValueError('Packaged geode failed native interface invariants')
    return result,info,{'methods':methods,'kernel_relocations':len([r for r in crels if r[0]==0]),'resource_relocations':len([r for r in crels if r[0]==0x22])}
