#!/usr/bin/env python3
"""Check native geode/UI class references against the exact target archive.

Static checks only: this does not execute the loader or specific UI.
"""
from __future__ import annotations
import argparse, hashlib, json, zipfile
from pathlib import Path
from geode import parse, resource_bytes, u16
from ui_builder import chunk
from build import read_member
ROOT=Path(__file__).resolve().parents[1]
def audit(gwp: Path) -> dict:
    data=(ROOT/'MINICALC.GEO').read_bytes();q=parse(data,'MINICALC.GEO')
    report=json.loads((ROOT/'EVIDENCE/BUILD.json').read_text())
    with zipfile.ZipFile(gwp) as archive:
        target=parse(read_member(archive,'/SYSTEM/UI.GEO'),'target UI.GEO')
        sample=parse(read_member(archive,'/WORLD/EXTRAS/SPINTEXT.GEO'),'native skeleton')
        mono=read_member(archive,'/FONT/MONO.FNT')
    refs=[]
    for rid,handles in ((3,report['ui']['objects']),(4,[0x22])):
        res=resource_bytes(data,q,rid)
        for h in handles:
            obj=chunk(res,h)
            if u16(obj,0)!=0x3000:raise ValueError('Unexpected encoded native UI class')
            ordinal=u16(obj,2)
            if ordinal>=len(target['exports']):raise ValueError('Out-of-range native UI class reference')
            refs.append({'resource':rid,'chunk':h,'class_ordinal':ordinal})
    # Exact target's native URW Mono plain 10-point bitmap. The font remains
    # installed with GEOS; it is NOT included in the output package.
    if mono[:4]!=b'BSWF' or u16(mono,8)!=0x1a00:raise ValueError('Unexpected native mono font')
    face=0x50fe;table=face+71
    widths=[u16(mono,table+(c-32)*8+3)+mono[table+(c-32)*8+2]/256 for c in range(32,127)]
    if set(widths)!={6.0}:raise ValueError('Native font does not match the caret advance')
    font_metrics={'font_id':0x1a00,'point_size':10,'file_sha256':hashlib.sha256(mono).hexdigest(),'bitmap_face_file_offset':face,'printable_ascii_characters_checked':len(widths),'minimum_advance':min(widths),'maximum_advance':max(widths),'font_file_included_in_package':False}
    required=next(x['protocol'] for x in q['imports'] if x['name']=='ui')
    if required!=target['protocol']:raise ValueError('Target UI protocol mismatch')
    if q['kernel_protocol']!=sample['kernel_protocol']:raise ValueError('Kernel requirement differs from native template')
    result={
        'geode_sha256':hashlib.sha256(data).hexdigest(),
        'target_archive_sha256':hashlib.sha256(gwp.read_bytes()).hexdigest(),
        'native_ui_available_protocol':target['protocol'],
        'native_ui_requested_protocol':required,'ui_protocol_matches':True,
        'kernel_requested_protocol':q['kernel_protocol'],
        'kernel_protocol_matches_source_native_template':True,
        'native_ui_export_count':len(target['exports']),
        'encoded_ui_class_references':refs,
        'imported_ui_function_relocations':[r for r in q['relocations'] if r['source']==1],
        'runtime_loader_executed':False,'worksheet_font':font_metrics,
        'scope':'Static protocol, resource and class-ordinal audit; no claim of UI behavior or loader success.'}
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--gwp',required=True,type=Path);a=p.parse_args()
    r=audit(a.gwp)
    (ROOT/'EVIDENCE/TARGET_AUDIT.json').write_text(json.dumps(r,indent=2)+'\n')
    print('Target interface and class-ordinal checks passed (static only).')
