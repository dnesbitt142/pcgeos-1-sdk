"""Test the same C calculation/persistence sources used by the native geode.
Set MINICALC_BUILD to the build directory, or run TOOLS/build.py first.
These are hosted C tests, NOT a GEOS boot.
"""
from __future__ import annotations
import ctypes as C
import hashlib,json,os,random,struct,sys,tempfile,unittest
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BUILD=Path(os.environ.get('MINICALC_BUILD',ROOT/'BUILD'))
sys.path.insert(0,str(ROOT/'TOOLS/legacy'))
from legacy_records import parse_records,read_cell

class Cell(C.Structure):
    _fields_=[('row',C.c_ushort),('col',C.c_ubyte),('state',C.c_ubyte),
              ('value',C.c_int),('error',C.c_ubyte),('kind',C.c_ubyte),('input',C.c_char*64)]
class Sheet(C.Structure):
    _fields_=[('cells',Cell*256),('count',C.c_int)]
LIB=C.CDLL(str(BUILD/'libminicalc.so'))
LIB.edit_cell.argtypes=[C.c_int,C.c_int,C.c_char_p]
LIB.find_cell.argtypes=[C.POINTER(Sheet),C.c_int,C.c_int]
LIB.copy_range.argtypes=[C.c_int,C.c_int,C.c_char_p]
LIB.cell_display.argtypes=[C.c_int,C.c_int,C.c_void_p,C.c_uint]
LIB.save_document.argtypes=LIB.read_document.argtypes=[C.c_char_p]
LIB.ieee64.argtypes=[C.c_int,C.c_void_p]
BOOK=Sheet.in_dll(LIB,'book')
def rc(s):return int(s[1:])-1,ord(s[0].upper())-65
def put(s,text):return LIB.edit_cell(*rc(s),text.encode('ascii'))
def val(s):
    b=C.create_string_buffer(80);LIB.cell_display(*rc(s),b,len(b));return b.value.decode()
def source(s):
    i=LIB.find_cell(C.byref(BOOK),*rc(s));return bytes(BOOK.cells[i].input).decode() if i>=0 else ''
def snap():return {f'{chr(c.col+65)}{c.row+1}':bytes(c.input).decode() for c in BOOK.cells[:BOOK.count]}
def msg():return bytes((C.c_char*160).in_dll(LIB,'message')).split(b'\0')[0].decode()
def save(p):return LIB.save_document(os.fsencode(p))
def load(p):return LIB.read_document(os.fsencode(p))
def manifest(cells):
    lines=['MINICALC 1']+[f'{a}\t{s}' for a,s in cells]
    h=2166136261
    for b in ('\n'.join(lines)+'\n').encode('ascii'):h=((h^b)*16777619)&0xffffffff
    lines.append(f'END\t{len(cells)}\t{h:08X}')
    return ('\r\n'.join(lines)+'\r\n').encode('ascii')

class CoreTests(unittest.TestCase):
    def setUp(self):LIB.test_faults(0,0,0);LIB.new_book()
    def test_acceptance_30_to_120(self):
        put('A1','10');put('A2','20');put('A3','=SUM(A1:A2)');self.assertEqual(val('A3'),'30');put('A1','100');self.assertEqual(val('A3'),'120')
    def test_all_documented_functions(self):
        for a,s in [('A1','2'),('A2','4'),('A3','6'),('A4','text')]:put(a,s)
        expressions={'SUM(A1:A4)':'12','AVERAGE(A1:A4)':'4','MIN(A1:A4)':'2','MAX(A1:A4)':'6','COUNT(A1:A4)':'3','ABS(-2.5)':'2.5','ROUND(1.235,2)':'1.24'}
        for expr,expected in expressions.items():
            with self.subTest(expr=expr):put('B1','='+expr);self.assertEqual(val('B1'),expected)
    def test_operator_precedence(self):
        expressions={'1+2*3':'7','(1+2)*3':'9','-(-2+3)':'-1','+--3':'3','1/3':'0.3333','2/3':'0.6667','-2/3':'-0.6667','5%':'0.05','200*5%':'10','1.0001*1.0001':'1.0002'}
        for expr,expected in expressions.items():
            with self.subTest(expr=expr):put('A1','='+expr);self.assertEqual(val('A1'),expected)
    def test_range_forms_and_spaces(self):
        put('A1','2');put('A2','3');put('B1','= SUM( A1 : A2 , 4 )');self.assertEqual(val('B1'),'9');put('B1','=SUM(A2:A1)');self.assertEqual(val('B1'),'5')
    def test_aggregate_numeric_text_blank_rules(self):
        put('A1',"'123");put('A2','word');put('A3','0');put('B1','=COUNT(A1:A4)');self.assertEqual(val('B1'),'1');put('B1','=SUM(A1:A4)');self.assertEqual(val('B1'),'0');put('B1','=A1+1');self.assertEqual(val('B1'),'#VALUE!');put('B1','=A4+1');self.assertEqual(val('B1'),'1')
    def test_round_negative_places_and_ties(self):
        for expr,expected in [('ROUND(-1.235,2)','-1.24'),('ROUND(12345,-2)','12300'),('ROUND(12350,-2)','12400'),('ROUND(0.0001,4)','0.0001')]:
            put('A1','='+expr);self.assertEqual(val('A1'),expected)
    def test_division_by_zero_and_propagation(self):
        put('A1','=1/0');put('A2','=A1+2');put('A3','=SUM(A1:A2)');self.assertEqual([val(a) for a in ['A1','A2','A3']],['#DIV/0!']*3)
    def test_cycle_detection_and_recovery(self):
        put('A1','=A2');put('A2','=A1');self.assertEqual(val('A1'),'#CYCLE!');self.assertEqual(val('A2'),'#CYCLE!');put('A2','10');self.assertEqual(val('A1'),'10')
    def test_direct_and_range_self_cycles(self):
        put('A1','=A1');self.assertEqual(val('A1'),'#CYCLE!');put('A1','=SUM(A1:A2)');self.assertEqual(val('A1'),'#CYCLE!')
    def test_overflow_and_precision_errors(self):
        for expr,err in [('214748.3648','#NUM!'),('1.00001','#PREC!'),('=214748.3647+0.0001','#NUM!'),('=1000*1000','#NUM!'),('=ROUND(1,5)','#VALUE!')]:
            put('A1',expr);self.assertEqual(val('A1'),err)
        put('A1','-214748.3647');self.assertEqual(val('A1'),'-214748.3647');put('A1','1.000000');self.assertEqual(val('A1'),'1')
    def test_unsupported_and_malformed_formulas(self):
        for expr in ['=SUM(A1', '=1+', '=ROUND(1)', '=ABS(1,2)', '=1 2', '=(1+2))']:
            put('B1',expr);self.assertTrue(val('B1').startswith('#'),expr)
        put('B1','=IF(1,2,3)');self.assertEqual(val('B1'),'#NAME?')
    def test_deep_expression_is_bounded(self):
        put('A1','='+'('*28+'1'+')'*28);self.assertEqual(val('A1'),'#DEPTH!')
    def test_forward_references_and_recalculation(self):
        put('A1','=C1+B1');put('B1','=D1*2');put('C1','7');put('D1','4');self.assertEqual(val('A1'),'15');put('D1','10');self.assertEqual(val('A1'),'27')
    def test_delete_clears_cell_and_dependencies(self):
        put('A1','9');put('A2','=A1+1');put('A1','');self.assertEqual(val('A1'),'');self.assertEqual(val('A2'),'1')
    def test_relative_absolute_copy(self):
        put('A1','=$B$1+B$2+$C3+D4');self.assertEqual(LIB.copy_range(0,0,b'B2'),1);self.assertEqual(source('B2'),'=$B$1+C$2+$C4+E5')
    def test_fill_from_one_source(self):
        put('A1','=B1+1');self.assertEqual(LIB.copy_range(0,0,b'A2:A5'),1);self.assertEqual(source('A5'),'=B5+1')
    def test_copy_reference_outside_grid(self):
        put('B1','=A1');LIB.copy_range(0,1,b'A1');self.assertEqual(source('A1'),'=#REF!');self.assertEqual(val('A1'),'#REF!')
    def test_copy_text_is_literal(self):
        put('A1','Cell A1 is a label');LIB.copy_range(0,0,b'B2');self.assertEqual(source('B2'),'Cell A1 is a label')
    def test_undo_redo(self):
        put('A1','1');put('A1','2');LIB.undo_book();self.assertEqual(val('A1'),'1');LIB.undo_book();self.assertEqual(val('A1'),'2')
    def test_multi_cell_copy_undo(self):
        put('A1','4');before=snap();LIB.copy_range(0,0,b'B1:D2');LIB.undo_book();self.assertEqual(snap(),before)
    def test_capacity_and_atomic_failed_copy(self):
        for n in range(256):self.assertEqual(put(f'{chr(65+n%26)}{n//26+1}',str(n)),1)
        before=snap();self.assertEqual(put('Z999','1'),0);self.assertEqual(snap(),before);self.assertEqual(LIB.copy_range(0,0,b'A999:Z999'),0);self.assertEqual(snap(),before)
    def test_input_limits_and_ascii(self):
        put('A1','kept');self.assertEqual(put('A1','x'*64),0);self.assertEqual(source('A1'),'kept');self.assertEqual(put('A1','x'*63),1);self.assertEqual(LIB.edit_cell(0,0,b'bad\x01'),0)
    def test_random_fixed_point_arithmetic(self):
        rng=random.Random(1086)
        for _ in range(700):
            a=rng.randint(-1000000,1000000);b=rng.randint(-1000000,1000000) or 1
            da=Decimal(a)/10000;db=Decimal(b)/10000
            op=rng.choice(['+','-','*','/']);exact={'+':lambda:da+db,'-':lambda:da-db,'*':lambda:da*db,'/':lambda:da/db}[op]()
            expected=exact.quantize(Decimal('.0001'),rounding=ROUND_HALF_UP)
            if abs(expected)>Decimal('214748.3647'):want='#NUM!'
            else:want=format(expected,'f').rstrip('0').rstrip('.') if '.' in format(expected,'f') else str(expected);want='0' if want=='-0' else want
            put('A1',f'=({da}){op}({db})');self.assertEqual(val('A1'),want,(da,op,db))
    def test_ieee_export_rounding_10009_cases(self):
        rng=random.Random(8401);values=[0,1,-1,9999,10000,10001,2147483647,-2147483647,327680000]+[rng.randint(-2147483647,2147483647) for _ in range(10000)]
        for value in values:
            b=C.create_string_buffer(8);LIB.ieee64(value,b);self.assertEqual(b.raw,struct.pack('<d',value/10000),value)

class DocumentTests(unittest.TestCase):
    def setUp(self):
        LIB.test_faults(0,0,0);LIB.new_book();self.temp=tempfile.TemporaryDirectory(prefix='mc-');self.root=Path(self.temp.name);self.path=self.root/'BOOK.MCS'
    def tearDown(self):LIB.test_faults(0,0,0);self.temp.cleanup()
    def start(self):put('A1','10');put('A2','20');put('A3','=SUM(A1:A2)')
    def test_save_reopen_edit_save(self):
        self.start();self.assertEqual(save(self.path),1,msg());LIB.new_book();self.assertEqual(load(self.path),1,msg());self.assertEqual(source('A3'),'=SUM(A1:A2)');put('A1','100');self.assertEqual(val('A3'),'120');self.assertEqual(save(self.path),1,msg());self.assertTrue((self.root/'BOOK.C00').exists());self.assertTrue((self.root/'BOOK.W00').exists());LIB.new_book();load(self.path);self.assertEqual(val('A3'),'120')
    def test_matching_view_opens_working_formulas(self):
        self.start();save(self.path);LIB.new_book();self.assertEqual(load(self.root/'BOOK.WK1'),1,msg());self.assertEqual(source('A3'),'=SUM(A1:A2)')
    def test_values_wk1_record_layout(self):
        self.start();put('B1',"'007");put('B2','=1/0');save(self.path)
        records=parse_records((self.root/'BOOK.WK1').read_bytes());self.assertEqual(records.version,0x0406);cells={c['address']:c for r in records.records if (c:=read_cell(r,records.version))}
        self.assertEqual(cells['A3']['kind'],'integer');self.assertEqual(cells['A3']['value'],30);self.assertEqual(cells['B1']['label_bytes_hex'],b'007'.hex());self.assertEqual(cells['B2']['label_bytes_hex'],b'#DIV/0!'.hex());self.assertFalse(any(c['kind']=='formula' for c in cells.values()))
    def test_unknown_foreign_workbook_not_overwritten(self):
        f=self.root/'FOREIGN.WK1';f.write_bytes(b'original foreign bytes');before=f.read_bytes();self.start();self.assertEqual(load(f),0);self.assertEqual(save(f),0);self.assertEqual(f.read_bytes(),before)
    def test_existing_destination_is_not_overwritten(self):
        self.path.write_bytes(b'do not overwrite');self.start();self.assertEqual(save(self.path),0);self.assertEqual(self.path.read_bytes(),b'do not overwrite')
    def test_external_edit_detection(self):
        self.start();save(self.path);original=self.path.read_bytes();self.path.write_bytes(original+b'outside change');put('A1','12');self.assertEqual(save(self.path),0);self.assertEqual(self.path.read_bytes(),original+b'outside change')
    def test_mismatched_view_load_is_transactional(self):
        self.start();save(self.path);view=self.root/'BOOK.WK1';view.write_bytes(view.read_bytes()+b'changed');LIB.new_book();put('Z1','keep');before=snap();self.assertEqual(load(view),0);self.assertEqual(snap(),before)
    def test_missing_or_changed_view_allows_master_read_not_overwrite(self):
        self.start();save(self.path);view=self.root/'BOOK.WK1';view.write_bytes(b'foreign');LIB.new_book();self.assertEqual(load(self.path),1);put('A1','11');self.assertEqual(save(self.path),0);self.assertEqual(view.read_bytes(),b'foreign');self.assertEqual(save(self.root/'NEW.MCS'),1)
    def test_invalid_inputs_preserve_current_sheet(self):
        self.start();before=snap();valid=manifest([('B1','42')]);inputs=[b'',valid[:-1],valid.replace(b'42',b'43'),valid+b'extra',b'MINICALC 2\r\n',manifest([('B1','1'),('B1','2')]),manifest([('AA1','1')]),manifest([('A1','x'*64)])]
        for raw in inputs:
            self.path.write_bytes(raw);self.assertEqual(load(self.path),0);self.assertEqual(snap(),before)
    def test_reserved_device_and_bad_filenames(self):
        for name in ['CON.MCS','NUL.WK1','AUX','COM1.MCS','LPT9.MCS','TOOLONG99.MCS','BOOK.WQ1','*.MCS']:
            self.assertEqual(save(self.root/name),0,name)
    def test_crlf_and_lf_working_files(self):
        raw=manifest([('A1','1.25'),('A2','=A1*2')]);self.path.write_bytes(raw.replace(b'\r\n',b'\n'));self.assertEqual(load(self.path),1);self.assertEqual(val('A2'),'2.5')
    def test_full_capacity_roundtrip(self):
        for n in range(256):put(f'{chr(65+n%26)}{n//26+1}',"'"+('x'*62 if n%2 else str(n)))
        original=snap();self.assertEqual(save(self.path),1);LIB.new_book();self.assertEqual(load(self.path),1);self.assertEqual(snap(),original)
    def test_random_roundtrip(self):
        rng=random.Random(1192)
        for n in range(100):put(f'{chr(65+n%20)}{n//20+1}',str(rng.randint(-9999,9999)))
        for n in range(8):put(f'Z{n+1}',f'=SUM(A{n+1}:T{n+1})')
        original=snap();values={a:val(a) for a in original};save(self.path);LIB.new_book();load(self.path);self.assertEqual(snap(),original);self.assertEqual({a:val(a) for a in original},values)
    def test_short_write_preserves_both_previous_files(self):
        for fail_at in (1,2):
            with self.subTest(fail_at=fail_at):
                LIB.test_faults(0,0,0);self.start();self.assertEqual(save(self.path),1);before={p.name:p.read_bytes() for p in self.root.iterdir()};put('A1','111');LIB.test_faults(fail_at,0,0);self.assertEqual(save(self.path),0);self.assertEqual(self.path.read_bytes(),before['BOOK.MCS']);self.assertEqual((self.root/'BOOK.WK1').read_bytes(),before['BOOK.WK1']);self.assertEqual(val('A3'),'131');LIB.test_faults(0,0,0)
                for p in self.root.iterdir():p.unlink()
                LIB.new_book()
    def test_rename_failure_rolls_back_pair(self):
        for fail_at in (1,2,3,4):
            with self.subTest(fail_at=fail_at):
                LIB.test_faults(0,0,0);self.start();self.assertEqual(save(self.path),1);m=self.path.read_bytes();v=(self.root/'BOOK.WK1').read_bytes();put('A1','200');LIB.test_faults(0,fail_at,0);self.assertEqual(save(self.path),0);self.assertEqual(self.path.read_bytes(),m);self.assertEqual((self.root/'BOOK.WK1').read_bytes(),v);LIB.test_faults(0,0,0)
                for p in self.root.iterdir():p.unlink()
                LIB.new_book()
    def test_existing_temp_files_never_deleted(self):
        for n in range(100):(self.root/f'BOOK.T{n:02}').write_bytes(b'unrelated temporary')
        self.start();self.assertEqual(save(self.path),0);self.assertEqual(len(list(self.root.iterdir())),100);self.assertTrue(all(p.read_bytes()==b'unrelated temporary' for p in self.root.iterdir()))
    def test_backup_exhaustion_preserves_documents(self):
        self.start();save(self.path);before=self.path.read_bytes()
        for n in range(100):(self.root/f'BOOK.C{n:02}').write_bytes(b'keep backup')
        put('A1','4');self.assertEqual(save(self.path),0);self.assertEqual(self.path.read_bytes(),before);self.assertTrue(all((self.root/f'BOOK.C{n:02}').read_bytes()==b'keep backup' for n in range(100)))
    def test_error_cells_persist_as_formulas(self):
        put('A1','=1/0');put('A2','=A2');save(self.path);LIB.new_book();load(self.path);self.assertEqual(source('A1'),'=1/0');self.assertEqual(val('A1'),'#DIV/0!');self.assertEqual(val('A2'),'#CYCLE!')

if __name__=='__main__':unittest.main(verbosity=2)
