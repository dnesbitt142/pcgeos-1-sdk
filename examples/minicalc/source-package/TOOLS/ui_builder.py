"""Build old (1.x) generic UI object resources from the supplied native sample.
Unknown class-specific fields stay from their exact native templates. These are
not 2.x object instances. Object tree links and LMEM chunk sizes are validated.
"""
import struct
from geode import u16,align16

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
 word(b,12,next_handle if next_handle is not None else parent|1);word(b,14,0x4000)
 word(b,16,child or 0);word(b,18,0x4000 if child else 0)
 word(b,20,mon);word(b,22,0);word(b,24,hints)
 return b

def build_ui(r3,r4,trigger_template,note_ui,viewer_dialogs,display_template,viewer_help,viewer_primary,help_text):
 """Native 1.x menus, formula bar and actual GenFileSelector dialogs.
 Object-specific layouts originate from the exact supplied native programs.
 No 2.x document-control objects or invented binary instances are used.
 """
 d={0x22:None};objects=set();buttons=[];next_data=0x100
 def data(value):
  nonlocal next_data
  h=next_data;next_data+=2;d[h]=bytes(value);return h
 def label(s,mnemonic=0xff):
  b=bytearray(moniker(s));b[5]=mnemonic;return data(b)
 def add(h,template,parent,nxt=None,child=None,mon=0,hints=0):
  b=obj(template,next_handle=nxt,parent=parent,child=child,mon=mon,hints=hints);d[h]=b;objects.add(h);return b
 def button(h,title,action,parent,nxt=None,default=False,cancel=False):
  b=add(h,trigger_template,parent,nxt,mon=label(title,0xfe if cancel else 0),hints=default_hint if default else 0)
  word(b,26,0xc080 if cancel else 0xc000);word(b,28,0);word(b,30,0x1000);word(b,32,0xc00+action)
  buttons.append(dict(chunk=h,label=title,action=action))
 def edit(h,title,parent,nxt,action,limit=63,initial='',filename=False):
  b=add(h,chunk(viewer_dialogs,0x2e) if filename else chunk(r3,0x3a),parent,nxt,mon=label(title) if title else 0,hints=filename_hint if filename else 0)
  word(b,28,data(initial.encode()+b'\0'));word(b,40,limit);word(b,51,0);word(b,53,0x1000);word(b,55,0xc00+action)
  return b
 def display(h,parent,nxt,initial):
  b=add(h,display_template,parent,nxt);word(b,28,data(initial.encode()+b'\0'));word(b,40,159);return b
 def selector(h,parent,nxt,notify):
  b=add(h,chunk(viewer_dialogs,0x54),parent,nxt,hints=selector_hint)
  word(b,201,0);word(b,203,0x1000 if notify else 0);word(b,205,0xc00+notify if notify else 0)
  b[207:219]=b'*.MCS\0'.ljust(12,b'\0');return b
 menu_hint=data(chunk(note_ui,0x36));row_hint=data(chunk(r3,0x2a));primary_hint=data(chunk(r3,0x26))
 dialog_hint=data(chunk(viewer_dialogs,0x4c));selector_hint=data(chunk(viewer_dialogs,0x56));reply_hint=data(bytes.fromhex('42400400'))
 default_hint=data(bytes.fromhex('03400400'));filename_hint=data(chunk(viewer_dialogs,0x34))
 primary=add(0x24,chunk(r3,0x24),0x22,child=0x30,hints=primary_hint);word(primary,14,0x1004)
 # The native specific UI chooses placement/appearance of these menu objects.
 menu_template=chunk(note_ui,0x32)
 for h,title,nxt,first in [(0x30,'File',0x32,0x44),(0x32,'Edit',0x34,0x4c),(0x34,'View',0x28,0x50)]:
  add(h,menu_template,0x24,nxt,first,label(title,0),menu_hint)
 add(0x28,chunk(r3,0x28),0x24,0x3e,0x2c,hints=row_hint)
 address_field=edit(0x2c,'Cell:',0x28,0x2e,15,7,'A1');word(address_field,44,42)
 button(0x2e,'Go',15,0x28,0x3a)
 formula_field=edit(0x3a,'Formula:',0x28,None,1,63);word(formula_field,44,294)
 v=add(0x3e,chunk(r3,0x3e),0x24,0x58)
 word(v,46,u16(v,46)|0x40) # native 1.x send-control-characters bit
 for at,value in [(50,512),(52,280),(54,512),(56,280)]:word(v,at,value)
 for h,title,a,par,nxt in [(0x44,'New',11,0x30,0x46),(0x46,'Open...',2,0x30,0x48),(0x48,'Save',3,0x30,0x4a),(0x4a,'Save As...',4,0x30,None),(0x4c,'Undo / Redo',5,0x32,0x4e),(0x4e,'Clear Cell',16,0x32,0x5a),(0x5a,'Fill Range...',17,0x32,0x40),(0x40,'Edit Cell',29,0x32,0x42),(0x42,'Revert Edit',24,0x32,None),(0x50,'Previous Rows',6,0x34,0x52),(0x52,'Next Rows',7,0x34,0x54),(0x54,'Previous Columns',8,0x34,0x56),(0x56,'Next Columns',9,0x34,None)]:button(h,title,a,par,nxt)
 # This is the Viewer's actual native title-bar Help trigger and hints.
 # HINT 0x4044 is present in the 1.x specific UI; no later SDK number is used.
 ht=add(0x58,chunk(viewer_primary,0x56),0x24,0x60,mon=label('Help',0),hints=data(chunk(viewer_primary,0x5a)))
 word(ht,22,0x0f80);word(ht,28,0);word(ht,30,0x1000);word(ht,32,0x0c0a)
 word(d[0x40],22,0x0f81) # F2, same control-shortcut encoding as native Write F5
 buttons.append(dict(chunk=0x58,label='Help',action=10))
 # These GenList/GenFileSelector/reply-bar templates are the Viewer's own
 # native Open and Create-New dialogs, with only tree links and actions changed.
 dt=chunk(viewer_dialogs,0x4a);rt=chunk(viewer_dialogs,0x6a)
 add(0x60,dt,0x24,0x70,0x62,label('Open Spreadsheet'),dialog_hint)
 selector(0x62,0x60,0x64,21);display(0x64,0x60,0x66,'Select an MCS working file, then choose Open.')
 add(0x66,rt,0x60,child=0x68,hints=reply_hint);button(0x68,'Open',19,0x66,0x6a,default=True);button(0x6a,'Cancel',23,0x66,cancel=True)
 add(0x70,dt,0x24,0x80,0x72,label('Save Spreadsheet As'),dialog_hint)
 selector(0x72,0x70,0x74,25);edit(0x74,'File name:',0x70,0x76,20,12,'SHEET.MCS',filename=True)
 display(0x76,0x70,0x78,'MCS keeps formulas; a WK1 viewing copy is also saved.')
 add(0x78,rt,0x70,child=0x7a,hints=reply_hint);button(0x7a,'Save',20,0x78,0x7c,default=True);button(0x7c,'Cancel',23,0x78,cancel=True)
 add(0x80,dt,0x24,0x90,0x82,label('Fill from Selected Cell'),dialog_hint)
 edit(0x82,'Destination:',0x80,0x84,18,15,'B1:B10');display(0x84,0x80,0x86,'Relative references adjust. Existing target cells are replaced.')
 add(0x86,rt,0x80,child=0x88,hints=reply_hint);button(0x88,'Fill',18,0x86,0x8a,default=True);button(0x8a,'Cancel',23,0x86,cancel=True)
 add(0x90,dt,0x24,0xa0,child=0x92,mon=label('Unsaved Changes'),hints=dialog_hint)
 display(0x92,0x90,0x94,'Discard the unsaved changes to this sheet? Cancel to keep them.')
 add(0x94,rt,0x90,child=0x96,hints=reply_hint);button(0x96,'Discard',22,0x94,0x98);button(0x98,'Cancel',23,0x94,default=True,cancel=True)
 # Ensemble 1.x uses this scrollable GenTextDisplay help dialog. Retain
 # its native page messages, interaction flags and automatically closing
 # dismiss trigger. It is NOT GEOHELP.EXE (the DOS troubleshooting tool).
 add(0xa0,chunk(viewer_help,0x22),0x24,child=0xa2,mon=label('Help for MiniCalc'))
 help_display=add(0xa2,chunk(viewer_help,0x32),0xa0,0xa4,hints=data(chunk(viewer_help,0x36)))
 word(help_display,28,data(help_text.replace('\r\n','\n').replace('\n','\r').encode('ascii')+b'\0'))
 # Use the native plain-text attributes rather than stale runs referring to
 # byte offsets in the Viewer's original help text.
 word(help_display,30,0);word(help_display,38,0x011a)
 word(help_display,44,400);word(help_display,46,12)
 add(0xa4,chunk(viewer_help,0x3c),0xa0,child=0xa6,hints=reply_hint)
 for h,source,title,nxt,message in [(0xa6,0x44,'Page Up',0xa8,0x226b),(0xa8,0x48,'Page Down',0xaa,0x226c),(0xaa,0x40,'Close',None,0)]:
  b=add(h,chunk(viewer_help,source),0xa4,nxt,mon=label(title,0))
  word(b,28,0xa2 if message else 0);word(b,30,0x4000 if message else 0);word(b,32,message)
 d={h:bytes(b) if b is not None else None for h,b in d.items()}
 nr3=lmem(3,d,objects,{0x3e,0xa6,0xa8,0xaa}|{b['chunk'] for b in buttons})
 ac={h:chunk(r4,h) for h in (0x22,0x24,0x26,0x28)};app=bytearray(ac[0x22]);app[30:34]=b'MC1N';ac[0x22]=bytes(app);ac[0x28]=moniker('MiniCalc Native')
 return nr3,lmem(4,ac,{0x22}),dict(input_chunk=0x3a,address_chunk=0x2c,view_chunk=0x3e,primary_chunk=0x24,buttons=buttons,objects=sorted(objects),menus=[0x30,0x32,0x34],dialogs={'open':0x60,'save_as':0x70,'fill':0x80,'discard':0x90,'help':0xa0},file_selectors=[0x62,0x72],dialog_status=[0x64,0x76,0x84],grid={'x':32,'y':24,'cell_width':92,'cell_height':20,'rows':10,'columns':5},viewport={'width':512,'height':280},field_widths={'address':42,'formula':294},help={'title_trigger':0x58,'title_hint_hex':chunk(viewer_primary,0x5a).hex(),'dialog':0xa0,'display':0xa2,'page_up':0xa6,'page_down':0xa8,'close':0xaa,'native_messages':[0x226b,0x226c],'text_characters':len(help_text)},keyboard={'message':0x007b,'focus':'GenView 0x003e','edit_action':29,'help_shortcut':0x0f80,'edit_shortcut':0x0f81,'view_control_key_bit':0x40},templates=['SPINTEXT.GEO: native primary/row/editor/view','NOTEPAD.GEO: native menu and trigger','VIEWER.GEO: native file selectors, dialogs, filename field and reply bar','TERM.GEO: native read-only GenText display','VIEWER.GEO R12: native scrollable help dialog and paging controls','VIEWER.GEO R28: native title-bar Help trigger/hint'])
