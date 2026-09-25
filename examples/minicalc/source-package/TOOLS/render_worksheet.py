#!/usr/bin/env python3
"""Reconstruct one worksheet frame from the actual native-method test trace.

NOT a GEOS screenshot. It omits native window chrome, controls and dialogs.
Requires Pillow only for this optional evidence renderer. No font file is
copied into the output; it reads the user's hash-checked installed-font input.
"""
import argparse, hashlib, json, struct, zipfile
from pathlib import Path
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[1]
def render(gwp, output):
    info=json.loads((ROOT/'EVIDENCE/TARGET_AUDIT.json').read_text())['worksheet_font']
    with zipfile.ZipFile(gwp) as z:
        names=[n for n in z.namelist() if n.upper().endswith('/FONT/MONO.FNT')]
        if len(names)!=1:raise ValueError('Expected the target native mono font')
        font=z.read(names[0])
    if hashlib.sha256(font).hexdigest()!=info['file_sha256']:raise ValueError('Unsupported font build')
    start=info['bitmap_face_file_offset'];size=struct.unpack_from('<H',font,start)[0];font=font[start:start+size]
    text=(ROOT/'EVIDENCE/IN_CELL_KEYBOARD_TRACE.txt').read_text()
    # The closing parenthesis typed into A3, before committing =SUM(A1:A2).
    marker='KEY 29 4\n';a=text.index(marker)+len(marker);b=text.index('\nACTION ',a)
    events=text[a:b].splitlines()
    im=Image.new('RGB',(512,280),'white');draw=ImageDraw.Draw(im)
    palette={0:(0,0,0),7:(170,170,170),15:(255,255,255)};area=ink=palette[0];seen=False
    for line in events:
        p=line.split(' ',3)
        if line.startswith('COLOR '):
            _,which,value=line.split();value=int(value)
            if int(which)==355:area=palette[value]
            else:ink=palette[value]
        elif line.startswith('RECT '):
            x,y,x2,y2=map(int,line.split()[1:]);draw.rectangle((x,y,x2,y2),fill=area);seen=True
        elif line.startswith('TEXT '):
            x,y=int(p[1]),int(p[2]);string=p[3] if len(p)>3 else ''
            for c in string:
                if not 32<=ord(c)<=126:raise ValueError('Non-ASCII frame')
                off=71+(ord(c)-32)*8;bitmap=struct.unpack_from('<H',font,off)[0]
                width=struct.unpack_from('<H',font,off+3)[0]
                if bitmap>3:
                    w,h,dy,dx=struct.unpack_from('<BBbb',font,bitmap)
                    stride=(w+7)//8
                    if bitmap+4+h*stride>len(font):raise ValueError('Invalid bitmap bounds')
                    for yy in range(h):
                        for xx in range(w):
                            if font[bitmap+4+yy*stride+xx//8]&(0x80>>(xx%8)):
                                px,py=x+dx+xx,y+dy+yy
                                if 0<=px<512 and 0<=py<280:im.putpixel((px,py),ink)
                x+=width
    if not seen:raise ValueError('Trace contains no frame')
    im.save(output)
    return {'scope':'Worksheet draw-call reconstruction, NOT a GEOS screenshot','source':'IN_CELL_KEYBOARD_TRACE.txt, closing parenthesis key event','frame_size':[512,280],'native_font_id':info['font_id'],'native_font_point_size':info['point_size'],'native_chrome_or_dialogs_rendered':False,'font_file_distributed':False,'output_sha256':hashlib.sha256(Path(output).read_bytes()).hexdigest()}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--gwp',type=Path,required=True);p.add_argument('--output',type=Path,default=ROOT/'EVIDENCE/WORKSHEET_RENDER.png');a=p.parse_args()
    report=render(a.gwp,a.output);(ROOT/'EVIDENCE/WORKSHEET_RENDER.json').write_text(json.dumps(report,indent=2)+'\n');print(report['scope'])
