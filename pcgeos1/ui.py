from __future__ import annotations
import struct
from .geode import u16

def word(b,o,n):struct.pack_into('<H',b,o,n)
def chunk(b,h):
    a=u16(b,h);return b[a:a+u16(b,a-2)-2]
def lmem(rid,chunks,object_handles,ignore_dirty=()):
    n=(max(chunks)-0x20)//2+1
    data=bytearray(32+2*n)
    for off,val in [(0,rid),(2,32),(4,0xe000),(6,2),(10,n)]:word(data,off,val)
    flags=bytes(0 if h==0x20 else 7 if h in ignore_dirty else 3 if h in object_handles else 2 for h in range(0x20,0x20+2*n,2))
    chunks=dict(chunks);chunks[0x20]=flags
    for h in range(0x20,0x20+2*n,2):
        value=chunks.get(h)
        if value is None:word(data,h,0xffff);continue
        data+=b'\xcc'*((-len(data))%4);word(data,h,len(data)+2)
        data+=struct.pack('<H',len(value)+2)+value
        data+=b'\xcc'*((-len(data))%4)
    word(data,8,len(data));data+=b'\0'*((-len(data))%16);word(data,20,len(data))
    return bytes(data)
def moniker(s):return bytes.fromhex('0100000000ff')+s.encode('ascii')+b'\0'
def obj(template,next_handle=None,parent=None,child=None,mon=0,hints=0):
    b=bytearray(template)
    word(b,12,next_handle if next_handle is not None else (parent|1));word(b,14,0x4000)
    word(b,16,child or 0);word(b,18,0x4000 if child else 0)
    word(b,20,mon);word(b,22,0);word(b,24,hints)
    return b

def build_basic_ui(spin_r3,spin_r4,viewer_help,viewer_primary,app_name,help_text,width=500,height=300):
    """Build a small native 1.x Primary+GenView+title Help shell.

    The class-specific bytes come from exact target templates; only generic
    tree links, monikers, hints, and view dimensions are altered.
    """
    d={0x22:None};objects=set();next_data=0x80
    def data(v):
        nonlocal next_data
        h=next_data;next_data+=2;d[h]=bytes(v);return h
    def label(s,mnemonic=0xff):
        b=bytearray(moniker(s));b[5]=mnemonic;return data(b)
    def add(h,template,parent,nxt=None,child=None,mon=0,hints=0):
        b=obj(template,next_handle=nxt,parent=parent,child=child,mon=mon,hints=hints);d[h]=b;objects.add(h);return b
    primary_hint=data(chunk(spin_r3,0x26))
    primary=add(0x24,chunk(spin_r3,0x24),0x22,child=0x3e,hints=primary_hint);word(primary,14,0x1004)
    view=add(0x3e,chunk(spin_r3,0x3e),0x24,0x58)
    word(view,46,u16(view,46)|0x40)
    for at,value in [(50,width),(52,height),(54,width),(56,height)]:word(view,at,value)
    # Actual Viewer title-bar Help trigger/hint.
    ht=add(0x58,chunk(viewer_primary,0x56),0x24,None,mon=label('Help',0),hints=data(chunk(viewer_primary,0x5a)))
    word(ht,22,0x0f80);word(ht,28,0);word(ht,30,0x1000);word(ht,32,0x0c0a)
    # Native Viewer scrollable help dialog.
    reply_hint=data(bytes.fromhex('42400400'))
    add(0xa0,chunk(viewer_help,0x22),0x24,child=0xa2,mon=label('Help for '+app_name))
    hd=add(0xa2,chunk(viewer_help,0x32),0xa0,0xa4,hints=data(chunk(viewer_help,0x36)))
    text=help_text.replace('\r\n','\n').replace('\n','\r').encode('ascii','replace')+b'\0'
    word(hd,28,data(text));word(hd,30,0);word(hd,38,0x011a);word(hd,44,400);word(hd,46,12)
    add(0xa4,chunk(viewer_help,0x3c),0xa0,child=0xa6,hints=reply_hint)
    for h,source,title,nxt,message in [(0xa6,0x44,'Page Up',0xa8,0x226b),(0xa8,0x48,'Page Down',0xaa,0x226c),(0xaa,0x40,'Close',None,0)]:
        b=add(h,chunk(viewer_help,source),0xa4,nxt,mon=label(title,0))
        word(b,28,0xa2 if message else 0);word(b,30,0x4000 if message else 0);word(b,32,message)
    r3=lmem(3,{h:(bytes(v) if v is not None else None) for h,v in d.items()},objects,{0x3e,0xa6,0xa8,0xaa})
    ac={h:chunk(spin_r4,h) for h in (0x22,0x24,0x26,0x28)}
    ac[0x28]=moniker(app_name)
    return r3,lmem(4,ac,{0x22}),{'primary':0x24,'view':0x3e,'help_trigger':0x58,'help_dialog':0xa0,'viewport':[width,height]}
