"""Native geode, object-tree, resource, and adapter invariants (static only)."""
import hashlib,json,re,struct,sys,tempfile,subprocess,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'TOOLS'))
from geode import parse,resource_bytes,u16,GeodeError
from ui_builder import chunk
from build import instrument
class NativeStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b=(ROOT/'MINICALC.GEO').read_bytes();cls.q=parse(cls.b)
        cls.report=json.loads((ROOT/'EVIDENCE/BUILD.json').read_text())
        cls.code=resource_bytes(cls.b,cls.q,2);cls.dg=resource_bytes(cls.b,cls.q,1)
        cls.ui=resource_bytes(cls.b,cls.q,3);cls.app=resource_bytes(cls.b,cls.q,4)
    def test_01_native_identity_and_hash(self):
        self.assertEqual(self.q['format_version'],1);self.assertEqual(self.b[:4],bytes.fromhex('c745cf53'))
        self.assertEqual(self.q['permanent_name'],'mcalc1');self.assertEqual(self.q['permanent_extension'],'app')
        self.assertEqual(self.b[20:24],b'MC1N');self.assertEqual(self.q['sha256'],self.report['sha256'])
    def test_02_single_live_instance(self):
        self.assertTrue(u16(self.b,200)&0x8000);self.assertTrue(u16(self.b,200)&0x0200)
        self.assertEqual(u16(self.b,200)&0x0400,0)
        self.assertEqual(u16(self.b,200),u16(self.b,226))
    def test_03_only_native_ui_import_and_kernel_protocol(self):
        self.assertEqual(self.q['kernel_protocol'],[622,3]);self.assertEqual(self.q['imports'],[{'index':0,'name':'ui','attributes':0x4000,'protocol':[693,0]}])
        self.assertEqual(self.q['exports'],[])
    def test_04_class_method_table_uses_actual_native_handlers(self):
        self.assertEqual(u16(self.b,216),0x40);self.assertEqual(u16(self.b,218),1)
        self.assertEqual(self.dg[0x50:0x52],b'\x08\x01')
        n=len(self.report['methods']);self.assertEqual(n,30);self.assertEqual(u16(self.dg,0x46),n)
        self.assertIn(0xc3,[m['message'] for m in self.report['methods']])
        for i,m in enumerate(self.report['methods']):
            self.assertEqual(u16(self.dg,0x52+2*i),m['message'])
            self.assertEqual(u16(self.dg,0x52+2*n+4*i),m['offset'])
            self.assertEqual(u16(self.dg,0x52+2*n+4*i+2),2)
            self.assertLess(m['offset'],len(self.code))
    def test_05_fixed_private_engine_and_stack_room(self):
        eng=resource_bytes(self.b,self.q,11);self.assertEqual(len(eng),65520)
        self.assertEqual(eng[:4],b'MCN2');self.assertEqual(u16(eng,4),0x0201)
        self.assertEqual(u16(eng,20),self.report['engine_data_end'])
        self.assertEqual(struct.unpack_from('<I',eng,28)[0],self.report['state_tag'])
        self.assertEqual(self.q['resources'][11]['flags'],0x80)
        self.assertGreater(self.report['private_stack_headroom'],12000)
        self.assertEqual(u16(self.b,214),8192)
    def test_06_all_recorded_code_relocations_match_call_sites(self):
        rels=[r for r in self.q['relocations'] if r['resource']==2]
        self.assertGreater(len(rels),41)
        for r in rels:
            a=r['offset']
            if r['source']==0:
                self.assertEqual(self.code[a-1],0x9a);self.assertEqual(u16(self.code,a+2),0)
                self.assertIn(r['value'],self.report['kernel_ordinals'])
            else:
                self.assertEqual(r['info'],0x22);self.assertEqual(r['value'],11)
                self.assertEqual(self.code[a-1],0xb8)
    def test_07_chunk_bounds_and_object_flag_table(self):
        for rid,d in ((3,self.ui),(4,self.app)):
            n=u16(d,10);flags=chunk(d,0x20);self.assertEqual(len(flags),n)
            self.assertEqual(u16(d,0),rid);self.assertEqual(u16(d,2),0x20)
            self.assertEqual(u16(d,20),len(d));used=[]
            for h in range(0x20,0x20+2*n,2):
                a=u16(d,h)
                if a==0xffff:continue
                length=u16(d,a-2);self.assertGreaterEqual(length,2)
                self.assertGreaterEqual(a-2,0x20+2*n);self.assertLessEqual(a-2+length,u16(d,8))
                used.append((a-2,a-2+length))
            used.sort();self.assertTrue(all(a[1]<=b[0] for a,b in zip(used,used[1:])))
    def test_08_object_tree_is_complete_and_acyclic(self):
        expected=set(self.report['ui']['objects']);self.assertEqual(len(expected),53)
        seen=set()
        def children(parent):
            p=chunk(self.ui,parent);h=u16(p,16)
            if not h:return
            self.assertEqual(u16(p,18),0x4000)
            while True:
                self.assertNotIn(h,seen);self.assertIn(h,expected);seen.add(h)
                obj=chunk(self.ui,h);self.assertEqual(u16(obj,0),0x3000);self.assertLess(u16(obj,2),262)
                children(h);link=u16(obj,12);self.assertEqual(u16(obj,14),0x4000)
                if link&1:self.assertEqual(link,parent|1);break
                h=link
        seen.add(0x24);children(0x24);self.assertEqual(seen,expected)
    def test_09_every_button_targets_a_native_method(self):
        flags=chunk(self.ui,0x20)
        for b in self.report['ui']['buttons']:
            h=b['chunk'];d=chunk(self.ui,h)
            self.assertEqual(u16(d,2),0x44);self.assertEqual(d[28:32],b'\0\0\0\x10')
            self.assertEqual(u16(d,32),0xc00+b['action'])
            self.assertIn(b['label'].encode(),chunk(self.ui,u16(d,20)))
            self.assertEqual(flags[(h-0x20)//2],7)
    def test_10_native_entry_and_view(self):
        field=chunk(self.ui,0x3a);self.assertEqual(u16(field,2),0x56)
        self.assertEqual(u16(field,40),63);self.assertEqual(u16(field,55),0xc01)
        view=chunk(self.ui,0x3e);self.assertEqual(u16(view,2),0x4b)
        self.assertEqual([u16(view,x) for x in (50,52,54,56)],[512,280,512,280])
        self.assertEqual(chunk(self.app,0x22)[30:34],b'MC1N')
    def test_11_no_dos_or_bios_interrupt_instructions(self):
        with tempfile.TemporaryDirectory() as t:
            f=Path(t)/'code.bin';f.write_bytes(self.code)
            text=subprocess.check_output(['objdump','-D','-b','binary','-m','i8086','-M','intel',str(f)],text=True)
        self.assertIsNone(re.search(r'\bint\s+0x(?:10|16|20|21)\b',text))
        self.assertNotIn(b'MINICALC.EXE',self.code)
    def test_12_instrumentation_bounds_and_repeat_expansion(self):
        raw='.text\nf:\n'+''.join('\tnop\n' for _ in range(20))+'\trep movsl\n\tret\n'
        result,report=instrument(raw)
        self.assertNotIn('rep movsl',result);self.assertIn('call native_poll',result)
        self.assertEqual(report['bounded_repeat_expansions'],1)
        self.assertGreaterEqual(report['poll_sites'],4)
        with self.assertRaises(ValueError):instrument('.text\nf:\n\trepne scasb\n')
    def test_13_source_fingerprint_matches_build(self):
        data=b''.join(p.name.encode()+p.read_bytes() for p in sorted((ROOT/'SRC').glob('*')))
        self.assertEqual(hashlib.sha256(data).hexdigest(),self.report['source_sha256'])
    def test_14_truncated_or_corrupt_container_rejected(self):
        for b in (self.b[:200],self.b[:-1],b'MZ'+self.b[2:]):
            with self.assertRaises(GeodeError):parse(b)
        bad=bytearray(self.b);bad[208]^=1
        with self.assertRaises(GeodeError):parse(bytes(bad))
    def test_15_native_menus_and_file_selector_instances(self):
        for h in (0x30,0x32,0x34):
            d=chunk(self.ui,h);self.assertEqual(u16(d,2),0x50);self.assertEqual(d[28],2)
        for h in (0x60,0x70,0x80,0x90):
            d=chunk(self.ui,h);self.assertEqual(u16(d,2),0x54);self.assertEqual(len(d),40)
        for h in (0x62,0x72):
            d=chunk(self.ui,h);self.assertEqual(u16(d,2),0x63);self.assertEqual(len(d),225)
            self.assertEqual(d[207:219],b'*.MCS\0'.ljust(12,b'\0'))
        self.assertEqual(u16(chunk(self.ui,0x62),205),0xc15)
        self.assertEqual(u16(chunk(self.ui,0x72),205),0xc19)
        self.assertEqual(u16(chunk(self.ui,0x74),40),12)
        self.assertEqual(u16(chunk(self.ui,0x82),40),15)
    def test_16_directory_context_uses_native_kernel_services(self):
        for ordinal in (51,73,74,75,76):self.assertIn(ordinal,self.report['kernel_ordinals'])
        self.assertGreater(len(self.report['ui']['file_selectors']),0)
    def test_17_controls_target_existing_methods(self):
        methods={m['message'] for m in self.report['methods']}
        for h in (0x2c,0x3a,0x74,0x82):
            d=chunk(self.ui,h);self.assertEqual(u16(d,2),0x56)
            self.assertEqual(u16(d,51),0);self.assertEqual(u16(d,53),0x1000)
            self.assertIn(u16(d,55),methods)
        for h in (0x64,0x76,0x84,0x92):self.assertEqual(u16(chunk(self.ui,h),2),0x55)
    def test_18_vga_toolbar_fields_and_grid_geometry(self):
        self.assertEqual(u16(chunk(self.ui,0x2c),44),42)
        self.assertEqual(u16(chunk(self.ui,0x3a),44),294)
        self.assertEqual(u16(chunk(self.ui,0x3a),12),0x29)
        self.assertEqual(self.report['ui']['grid'],dict(x=32,y=24,cell_width=92,cell_height=20,rows=10,columns=5))
        self.assertEqual(self.report['ui']['menus'],[0x30,0x32,0x34])
    def test_19_title_bar_help_uses_exact_native_hint(self):
        d=chunk(self.ui,0x58)
        self.assertEqual(chunk(self.ui,u16(d,24)),bytes.fromhex('0142040044400400'))
        self.assertEqual(u16(d,22),0x0f80);self.assertEqual(u16(d,32),0xc0a);self.assertEqual(u16(d,12),0x60)
    def test_20_native_help_control_and_paging(self):
        d=chunk(self.ui,0xa0);self.assertEqual(len(d),29);self.assertEqual(u16(d,2),0x50);self.assertEqual(d[28],0x4a)
        t=chunk(self.ui,0xa2);self.assertEqual(len(t),50);self.assertEqual(u16(t,2),0x55)
        self.assertEqual(u16(t,30),0);self.assertEqual(u16(t,38),0x11a)
        self.assertEqual(u16(t,44),400);self.assertEqual(u16(t,46),12)
        text=chunk(self.ui,u16(t,28));self.assertIn(b'Press F2 or double-click',text)
        self.assertEqual(text,(ROOT/'SRC/HELP.TXT').read_text().replace('\n','\r').encode()+b'\0')
        for h,m in [(0xa6,0x226b),(0xa8,0x226c)]:
            t=chunk(self.ui,h);self.assertEqual(u16(t,28),0xa2);self.assertEqual(u16(t,30),0x4000);self.assertEqual(u16(t,32),m)
        close=chunk(self.ui,0xaa);self.assertEqual(u16(close,26),0xc080);self.assertEqual(u16(close,32),0)
    def test_21_keyboard_method_and_view_output(self):
        self.assertIn({'message':0x7b,'handler':'native_key','offset':self.report['symbol_offsets']['native_key']},self.report['methods'])
        v=chunk(self.ui,0x3e);self.assertEqual(u16(v,46)&0x8040,0x8040);self.assertEqual(u16(chunk(self.ui,0x40),22),0x0f81)
        self.assertEqual(u16(v,66),0);self.assertEqual(u16(v,68),0x1000)
        self.assertLess(0x52+6*len(self.report['methods']),0x180)
if __name__=='__main__':unittest.main(verbosity=2)
