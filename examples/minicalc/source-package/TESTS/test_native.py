"""Execute the compiled .GEO methods through a modeled GEOS interface.

Linux x86-64, GCC, and modify_ldt are required. This is not a GEOS boot.
The CPU probe is replaced with a chosen result; all other native/C instruction
bytes come from MINICALC.GEO, with its recorded kernel relocations resolved.
"""
from __future__ import annotations
import json,os,shutil,struct,subprocess,tempfile,unittest
from pathlib import Path
from run_native import ROOT,prepare

class NativeExecutionTests(unittest.TestCase):
    runs=[]
    @classmethod
    def setUpClass(cls):
        cls.build=tempfile.TemporaryDirectory(prefix='mc-native-build-')
        cls.command=prepare(Path(cls.build.name))
        cls.info=json.loads((ROOT/'EVIDENCE/BUILD.json').read_text())
        cls.symbols=cls.info['symbol_offsets']
    @classmethod
    def tearDownClass(cls):
        cls.build.cleanup()
        (ROOT/'EVIDENCE/NATIVE_RUNS.json').write_text(json.dumps({'scope':'Actual geode instruction execution; modeled GEOS API and interrupt windows; not a DOS/GEOS boot','runs':cls.runs},indent=2)+'\n')
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='mc-native-')
        self.work=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def sample(self,name='FIRST'):
        for suffix in ('MCS','WK1'):
            src=ROOT/'TESTS/FIXTURES'/f'{name}.{suffix}' if name=='DOSFIRST' else ROOT/'DOCUMENT'/f'{name}.{suffix}'
            shutil.copyfile(src,self.work/f'{name}.{suffix}')
    def execute(self,lines,**env):
        script=self.work/'SCRIPT.TXT';trace=self.work/'TRACE.TXT'
        script.write_text('\n'.join(lines)+'\n')
        environ={k:v for k,v in os.environ.items() if k not in ('BAD_CPU','FAIL_DOCUMENT_PATH','FAIL_WRITE','FAIL_RENAME','CORRUPT_STATE','FAIL_ALLOC','HIGH_READ_ERROR','HIGH_WRITE_ERROR','FAIL_SET_DIRECTORY')}
        environ.update({k:str(v) for k,v in env.items()})
        result=subprocess.run(self.command+[str(self.work),str(script),str(trace)],capture_output=True,text=True,env=environ,timeout=40)
        self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)
        self.trace=trace.read_text();self.engine=(self.work/'ENGINE.BIN').read_bytes()
        metrics={k:int(v) for item in result.stdout.split() if '=' in item for k,v in [item.split('=',1)]}
        self.assertEqual(metrics['driver_steps'],len(lines))
        self.assertGreaterEqual(metrics['native_methods'],len(lines))
        self.assertEqual(metrics['polling_windows'],metrics['upper_register_scrambles'])
        if not env.get('BAD_CPU'):
            self.assertGreater(metrics['polling_windows'],0)
            self.assertGreater(metrics['min_private_sp'],metrics['engine_used']+64)
        self.runs.append({'test':self._testMethodName,'environment':env,'metrics':metrics})
        return metrics
    def cells(self):
        at=self.symbols['book'];count=struct.unpack_from('<i',self.engine,at+76*256)[0]
        self.assertTrue(0<=count<=256)
        out={}
        for i in range(count):
            off=at+76*i;r,c=struct.unpack_from('<HB',self.engine,off)
            out[f'{chr(65+c)}{r+1}']={'value':struct.unpack_from('<i',self.engine,off+4)[0],
                                     'error':self.engine[off+8],
                                     'input':self.engine[off+10:off+74].split(b'\0')[0].decode('ascii')}
        return out
    def message(self):
        at=self.symbols['message'];return self.engine[at:at+160].split(b'\0')[0].decode('ascii')
    def test_01_click_type_enter_acceptance_save_restore(self):
        metrics=self.execute(['START','EXPOSE','CLICK 40 30','DO 1 10','DO 1 20','DO 1 =SUM(A1:A2)','CLICK 40 30','DO 1 100','DO 4','DO 20 NATIVE.MCS','CLOSE','RESTORE','EXPOSE','DO 15 A3'])
        self.assertEqual(self.cells()['A3'],{'value':1200000,'error':0,'input':'=SUM(A1:A2)'})
        self.assertIn('CELL A3 value=300000',self.trace)
        self.assertIn(b'A3\t=SUM(A1:A2)',(self.work/'NATIVE.MCS').read_bytes())
        self.assertTrue((self.work/'NATIVE.WK1').is_file());self.assertIn('CLOSED handle=8193',self.trace)
        self.assertIn('FIELD 3a =SUM(A1:A2)',self.trace);self.assertIn('FOCUS 3e',self.trace)
        self.assertGreater(metrics['draw_calls'],0)
        (ROOT/'EVIDENCE/NATIVE_ACCEPTANCE_TRACE.txt').write_text(self.trace)
        for suffix in ('MCS','WK1'):shutil.copyfile(self.work/f'NATIVE.{suffix}',ROOT/'EVIDENCE'/f'NATIVE.{suffix}')
    def test_02_open_button_activates_native_selector(self):
        self.sample('DOSFIRST');m=self.execute(['START','DO 2','SEL DOSFIRST.MCS','DO 19','DO 1 100','DO 3','DO 11','DO 2','FILE DOSFIRST.MCS'])
        self.assertEqual(self.cells()['A3']['value'],1200000)
        self.assertEqual(self.cells()['A3']['input'],'=SUM(A1:A2)')
        self.assertTrue((self.work/'DOSFIRST.C00').exists());self.assertTrue((self.work/'DOSFIRST.W00').exists())
        self.assertGreater(m['native_methods'],m['driver_steps'])
        self.assertIn('DIALOG_OPEN 60',self.trace);self.assertIn('DIALOG_CLOSE 60',self.trace)
    def test_03_all_functions_in_native_code(self):
        self.sample('FUNCTION');self.execute(['START','DO 2','FILE FUNCTION.MCS','EXPOSE'])
        for cell,value in {'D1':120000,'D2':40000,'D3':20000,'D4':60000,'D5':30000,'D6':25000,'D7':12400,'D8':100000,'D9':3333}.items():
            self.assertEqual(self.cells()[cell]['value'],value,cell);self.assertEqual(self.cells()[cell]['error'],0,cell)
    def test_04_fill_dialog_relative_reference_copy_and_undo_redo(self):
        self.execute(['START','DO 15 B1','DO 1 5','DO 1 7','DO 15 A1','DO 1 =B1+$B$1','DO 15 A1','DO 17','DO 18 A2:A3','DO 5','DO 5'])
        self.assertEqual(self.cells()['A2']['input'],'=B2+$B$1');self.assertEqual(self.cells()['A2']['value'],120000)
        self.assertEqual(self.cells()['A3']['input'],'=B3+$B$1');self.assertEqual(self.cells()['A3']['value'],50000)
        self.assertIn('DIALOG_OPEN 80',self.trace);self.assertIn('DIALOG_CLOSE 80',self.trace)
    def test_05_errors_and_cycle_recovery(self):
        self.execute(['START','DO 1 =1/0','DO 1 =A3','DO 1 =A2','DO 15 A3','DO 1 10','DO 15 B1','DO 1 =IF(1,2,3)'])
        cells=self.cells();self.assertNotEqual(cells['A1']['error'],0)
        self.assertEqual(cells['A2']['value'],100000);self.assertEqual(cells['A2']['error'],0)
        self.assertNotEqual(cells['B1']['error'],0)
    def test_06_dirty_new_and_open_cancel_preserve_sheet(self):
        self.sample();self.execute(['START','DO 15 Z999','DO 1 retained','DO 11','DO 23','DO 2','DO 23'])
        self.assertEqual(set(self.cells()),{'Z999'})
        self.assertEqual(self.trace.count('DIALOG_OPEN 90'),2);self.assertNotIn('DIALOG_OPEN 60',self.trace)
    def test_07_discard_confirmation_then_open(self):
        self.sample();self.execute(['START','DO 15 Z999','DO 1 temporary','DO 2','DO 22','FILE FIRST.MCS'])
        self.assertNotIn('Z999',self.cells());self.assertEqual(self.cells()['A3']['value'],300000)
        self.assertIn('DIALOG_CLOSE 90',self.trace);self.assertIn('DIALOG_OPEN 60',self.trace)
    def test_08_existing_foreign_destination_is_not_overwritten(self):
        (self.work/'OTHER.MCS').write_bytes(b'keep this unrelated file')
        self.execute(['START','DO 1 11','DO 4','DO 20 OTHER.MCS','DO 23'])
        self.assertEqual((self.work/'OTHER.MCS').read_bytes(),b'keep this unrelated file')
        self.assertFalse((self.work/'OTHER.WK1').exists());self.assertNotEqual(self.message(),'')
    def test_09_native_write_failure_preserves_old_pair(self):
        self.sample();before={s:(self.work/f'FIRST.{s}').read_bytes() for s in ('MCS','WK1')}
        self.execute(['START','DO 2','FILE FIRST.MCS','DO 1 100','DO 3'],FAIL_WRITE=0)
        for s in before:self.assertEqual((self.work/f'FIRST.{s}').read_bytes(),before[s])
        self.assertEqual(self.cells()['A3']['value'],1200000);self.assertIn('failed',self.message().lower())
    def test_10_native_rename_failure_rolls_back(self):
        self.sample();before={s:(self.work/f'FIRST.{s}').read_bytes() for s in ('MCS','WK1')}
        self.execute(['START','DO 2','FILE FIRST.MCS','DO 1 100','DO 3'],FAIL_RENAME=2)
        for s in before:self.assertEqual((self.work/f'FIRST.{s}').read_bytes(),before[s])
        self.assertEqual(self.cells()['A3']['value'],1200000)
    def test_11_pending_formula_is_committed_in_close_snapshot(self):
        self.execute(['START','DO 1 123','TYPE =A1*2','CLOSE','RESTORE'])
        self.assertEqual(self.cells()['A2']['input'],'=A1*2');self.assertEqual(self.cells()['A2']['value'],2460000)
        self.assertFalse(list(self.work.glob('*.MCS')));self.assertIn('Session restored',self.message())
    def test_12_wrong_build_state_tag_is_rejected(self):
        self.execute(['START','DO 1 123','CLOSE','RESTORE'],CORRUPT_STATE=1)
        self.assertEqual(self.cells(),{});self.assertNotIn('Session restored',self.message())
    def test_13_unsupported_cpu_path_does_not_enter_engine(self):
        metrics=self.execute(['START','EXPOSE','DO 1 123','CLOSE'],BAD_CPU=1)
        self.assertEqual(self.cells(),{});self.assertEqual(metrics['polling_windows'],0)
        self.assertIn('386 or newer',self.trace);self.assertIn('CLOSED handle=0',self.trace)
    def test_14_picker_recovers_missing_standard_document_path(self):
        self.execute(['START','DO 1 123','DO 4','DO 20 FIRST.MCS'],FAIL_DOCUMENT_PATH=1)
        self.assertIn(b'A1\t123',(self.work/'FIRST.MCS').read_bytes());self.assertIn('DIALOG_CLOSE 70',self.trace)
    def test_15_failed_close_allocation_returns_no_state(self):
        self.execute(['START','DO 1 123','CLOSE'],FAIL_ALLOC=1)
        self.assertIn('CLOSED handle=0',self.trace);self.assertEqual(self.cells()['A1']['value'],1230000)
    def test_16_file_highlight_without_activation_does_not_open(self):
        self.sample();self.execute(['START','DO 2','SEL FIRST.MCS','DO 23'])
        self.assertEqual(self.cells(),{});self.assertIn('DIALOG_CLOSE 60',self.trace)
    def test_17_far_cell_go_clear_and_back_to_grid(self):
        self.execute(['START','EXPOSE','DO 15 Z999','DO 1 42','DO 15 A1','DO 1 =Z999+1','DO 15 Z999','DO 16'])
        self.assertEqual(set(self.cells()),{'A1'});self.assertEqual(self.cells()['A1']['value'],10000)
        self.assertIn('FIELD 2c Z999',self.trace)
    def test_18_help_navigation_and_return(self):
        self.execute(['START','EXPOSE','DO 10','HELP_CLOSED','DO 7','DO 9','DO 6','DO 8'])
        self.assertEqual(self.cells(),{});self.assertIn('HELP_OPEN a0',self.trace)
        self.assertIn('FIELD 2c F11',self.trace)
    def test_19_high_numbered_read_error_is_not_success(self):
        self.sample();self.execute(['START','DO 2','FILE FIRST.MCS'],HIGH_READ_ERROR=1)
        self.assertEqual(self.cells(),{});self.assertIn('No readable MiniCalc',self.message())
        self.assertNotIn('DIALOG_CLOSE 60',self.trace)
    def test_20_high_numbered_write_error_is_not_success(self):
        self.execute(['START','DO 1 123','DO 4','DO 20 NEW.MCS'],HIGH_WRITE_ERROR=1)
        self.assertFalse((self.work/'NEW.MCS').exists());self.assertFalse((self.work/'NEW.WK1').exists())
        self.assertIn('Save failed',self.message());self.assertNotIn('DIALOG_CLOSE 70',self.trace)
    def test_21_click_commits_pending_editor_then_focuses_new_cell(self):
        self.execute(['START','TYPE pending edit','CLICK 140 50','DO 1 42'])
        self.assertEqual(self.cells()['A1']['input'],'pending edit');self.assertEqual(self.cells()['B2']['value'],420000)
        self.assertIn('FIELD 2c B2',self.trace);self.assertIn('FOCUS 3e',self.trace)
    def test_22_revert_and_non_cell_click_preserve_original(self):
        self.execute(['START','DO 1 keep','DO 15 A1','TYPE discard this','DO 24','CLICK 0 0','CLICK 536 30','CLICK 40 244','CLICK 65535 65535'])
        self.assertEqual(set(self.cells()),{'A1'});self.assertEqual(self.cells()['A1']['input'],'keep')
        self.assertIn('Uncommitted edit cancelled',self.message())
    def test_23_browse_subfolder_save_reopen_preserves_formula(self):
        (self.work/'SUB').mkdir()
        self.execute(['START','DO 1 7','DO 1 =A1*2','DO 4',r'BROWSE \SUB','DO 20 BOOK.MCS','DO 11','DO 2','FILE BOOK.MCS'])
        self.assertFalse((self.work/'BOOK.MCS').exists());self.assertIn(b'A2\t=A1*2',(self.work/'SUB/BOOK.MCS').read_bytes())
        self.assertEqual(self.cells()['A2']['value'],140000)
    def test_24_cancel_browsing_cannot_redirect_save(self):
        self.sample();(self.work/'OTHER').mkdir()
        self.execute(['START','DO 2','FILE FIRST.MCS','DO 4',r'BROWSE \OTHER','DO 23','DO 1 100','DO 3'])
        self.assertIn(b'A1\t100',(self.work/'FIRST.MCS').read_bytes());self.assertFalse((self.work/'OTHER/FIRST.MCS').exists())
    def test_25_same_leaf_different_directory_not_current_document(self):
        self.sample();(self.work/'OTHER').mkdir()
        for ext in ('MCS','WK1'):shutil.copyfile(self.work/f'FIRST.{ext}',self.work/f'OTHER/FIRST.{ext}')
        before=(self.work/'OTHER/FIRST.MCS').read_bytes()
        self.execute(['START','DO 2','FILE FIRST.MCS','DO 1 100','DO 4',r'BROWSE \OTHER','DO 20 FIRST.MCS','DO 23','DO 3'])
        self.assertEqual((self.work/'OTHER/FIRST.MCS').read_bytes(),before)
        self.assertIn(b'A1\t100',(self.work/'FIRST.MCS').read_bytes())
    def test_26_new_same_leaf_in_another_directory_can_save(self):
        self.sample();(self.work/'OTHER').mkdir()
        before=(self.work/'FIRST.MCS').read_bytes()
        self.execute(['START','DO 2','FILE FIRST.MCS','DO 1 100','DO 4',r'BROWSE \OTHER','DO 20 FIRST.MCS','DO 15 A1','DO 1 200','DO 3'])
        self.assertEqual((self.work/'FIRST.MCS').read_bytes(),before)
        self.assertIn(b'A1\t200',(self.work/'OTHER/FIRST.MCS').read_bytes())
    def test_27_directory_failure_preserves_sheet_and_unwinds_context(self):
        self.sample();before=(self.work/'FIRST.MCS').read_bytes()
        self.execute(['START','DO 2','FILE FIRST.MCS'],FAIL_SET_DIRECTORY=1)
        self.assertEqual(self.cells(),{});self.assertEqual((self.work/'FIRST.MCS').read_bytes(),before)
        self.assertIn('Cannot enter',self.message())
    def test_28_folder_notification_never_interpreted_as_workbook(self):
        self.execute(['START','DO 2','SEL SUB\\','FILE SUB\\','DO 23'])
        self.assertEqual(self.cells(),{});self.assertEqual(self.trace.count('DIALOG_CLOSE 60'),1)
    def test_29_failed_open_retains_previous_saved_sheet(self):
        self.sample();(self.work/'BAD.MCS').write_bytes(b'not a working file')
        self.execute(['START','DO 2','FILE FIRST.MCS','DO 2','FILE BAD.MCS','DO 23'])
        self.assertEqual(self.cells()['A3']['value'],300000)
    def test_30_fill_cancel_leaves_destination_unchanged(self):
        self.execute(['START','DO 1 11','DO 15 A1','DO 17','DO 23'])
        self.assertEqual(set(self.cells()),{'A1'});self.assertEqual(self.cells()['A1']['value'],110000)
    def test_31_directory_filename_rejected_by_save_dialog(self):
        self.execute(['START','DO 1 11','DO 4','DO 20 X/Y.MCS','DO 23'])
        self.assertFalse(list(self.work.glob('*.MCS')));self.assertIn('filename only',self.message())
    def test_32_pending_input_is_saved_without_extra_enter(self):
        self.execute(['START','TYPE =2+3','DO 3','DO 20 PENDING.MCS'])
        self.assertEqual(self.cells()['A1']['value'],50000)
        self.assertIn(b'A1\t=2+3',(self.work/'PENDING.MCS').read_bytes())
    def test_33_longest_input_is_retained_by_native_field_adapter(self):
        raw='x'*63
        self.execute(['START','DO 15 Z999','DO 1 '+raw,'DO 15 A1','DO 15 Z999'])
        self.assertEqual(self.cells()['Z999']['input'],raw);self.assertIn('FIELD 3a '+raw,self.trace)
    def test_34_invalid_fill_stays_open_and_can_be_corrected(self):
        self.execute(['START','DO 1 11','DO 15 A1','DO 17','DO 18 bad','DO 18 B1:B3'])
        self.assertEqual(set(self.cells()),{'A1','B1','B2','B3'})
        self.assertEqual(self.trace.count('DIALOG_OPEN 80'),1);self.assertEqual(self.trace.count('DIALOG_CLOSE 80'),1)

    def test_35_save_selector_highlight_updates_name_without_saving(self):
        self.sample();before=(self.work/'FIRST.MCS').read_bytes()
        self.execute(['START','DO 1 99','DO 4','SEL FIRST.MCS','DO 23'])
        self.assertIn('FIELD 74 FIRST.MCS',self.trace)
        self.assertEqual((self.work/'FIRST.MCS').read_bytes(),before)
        self.assertEqual(self.cells()['A1']['value'],990000)
    def test_36_restored_disk_handle_is_not_reused_without_picker(self):
        self.sample();before=(self.work/'FIRST.MCS').read_bytes()
        self.execute(['START','DO 2','FILE FIRST.MCS','DO 1 100','CLOSE','RESTORE','DO 3','DO 23'])
        self.assertEqual(self.cells()['A3']['value'],1200000)
        self.assertEqual((self.work/'FIRST.MCS').read_bytes(),before)
        self.assertIn('DIALOG_OPEN 70',self.trace)
    def test_37_actual_key_events_type_calculate_and_save(self):
        def typing(s):return [f'KEY {ord(c):x} 4' for c in s]
        script=['START','EXPOSE','CLICK 40 30']+typing('10')+['KEY ff0d 4']+typing('20')+['KEY ff0d 4']+typing('=SUM(A1:A2)')+['KEY ff0d 4','CLICK 40 30']+typing('100')+['KEY ff0d 4','DO 4','DO 20 KEYBOARD.MCS']
        self.execute(script)
        self.assertEqual(self.cells()['A3']['value'],1200000)
        self.assertEqual(self.cells()['A3']['input'],'=SUM(A1:A2)')
        self.assertIn('CELL A3 value=300000',self.trace);self.assertIn('FOCUS 3e',self.trace)
        self.assertNotIn('FOCUS 3a',self.trace)
        (ROOT/'EVIDENCE/IN_CELL_KEYBOARD_TRACE.txt').write_text(self.trace)
    def test_38_f2_native_partial_formula_edit(self):
        self.execute(['START','DO 1 =2+3','CLICK 40 30','KEY ff81 4','KEY ff08 4','KEY 34 4','KEY ff0d 4'])
        self.assertEqual(self.cells()['A1']['input'],'=2+4');self.assertEqual(self.cells()['A1']['value'],60000)
    def test_39_double_click_and_escape_cancel(self):
        self.execute(['START','DO 1 original','DBLCLICK 40 30','KEY ff08 4','KEY 58 4','KEY ff1b 4'])
        self.assertEqual(self.cells()['A1']['input'],'original');self.assertIn('FIELD 3a original',self.trace)
        self.assertIn('Edit cancelled',self.message())
    def test_40_native_edit_selection_and_navigation(self):
        self.execute(['START','DO 1 abcdef','CLICK 40 30','KEY ff81 4','KEY ff93 804','KEY ff93 804','KEY 58 4','KEY ff0d 4','KEY ff92 4','KEY ff09 804'])
        self.assertEqual(self.cells()['A1']['input'],'abcdX');self.assertIn('FIELD 2c B2',self.trace)
    def test_41_unhandled_keys_delegate_to_native_superclass(self):
        self.execute(['START','CLICK 40 30','KEY 78 1','KEY 78 8004','KEY ff82 4'])
        self.assertEqual(self.cells(),{});self.assertIn('SUPER msg=7b cx=ff82 dx=4',self.trace)
        self.assertIn('SUPER msg=7b cx=78 dx=8004',self.trace)
    def test_42_f1_native_help_preserves_pending_entry(self):
        self.execute(['START','EXPOSE','CLICK 40 30','KEY 31 4','KEY ff80 4','HELP_CLOSED','KEY ff1b 4'])
        self.assertEqual(self.cells(),{});self.assertIn('HELP_OPEN a0',self.trace)
        self.assertIn('FIELD 3a 1',self.trace)
    def test_43_long_edit_has_caret_and_draws_within_vga_view(self):
        script=['START','EXPOSE','CLICK 40 30']+[f'KEY {ord(c):x} 4' for c in 'x'*63]+['KEY ff94 4','KEY ff9a 4','KEY ff0d 4']
        self.execute(script);self.assertEqual(self.cells()['A1']['input'],'x'*62)
        for line in self.trace.splitlines():
            if line.startswith('RECT '):
                x,y,x2,y2=map(int,line.split()[1:]);self.assertTrue(0<=x<=x2<512);self.assertTrue(0<=y<=y2<280)
            if line.startswith('TEXT '):
                x,y=map(int,line.split()[1:3]);self.assertLess(x,512);self.assertLess(y,280)
    def test_44_edit_menu_directs_keyboard_to_cell(self):
        self.execute(['START','DO 1 12','CLICK 40 30','DO 29','KEY 33 4','KEY ff0d 4'])
        self.assertEqual(self.cells()['A1']['value'],1230000)
    def test_45_typing_pending_input_click_another_cell(self):
        self.execute(['START','CLICK 40 30','KEY 31 4','KEY 32 4','CLICK 140 50','KEY 35 4','KEY ff0d 4'])
        self.assertEqual(self.cells()['A1']['value'],120000);self.assertEqual(self.cells()['B2']['value'],50000)
    def test_46_numeric_keypad_input(self):
        self.execute(['START','CLICK 40 30','KEY ff31 4','KEY ff32 4','KEY ff2e 4','KEY ff35 4','KEY ff0d 4'])
        self.assertEqual(self.cells()['A1']['value'],125000)
    def test_47_control_a_replaces_entire_existing_formula(self):
        self.execute(['START','DO 1 =2+3','CLICK 40 30','DO 29','KEY 61 2004','KEY 39 4','KEY ff0d 4'])
        self.assertEqual(self.cells()['A1']['input'],'9');self.assertEqual(self.cells()['A1']['value'],90000)
if __name__=='__main__':unittest.main(verbosity=2)
