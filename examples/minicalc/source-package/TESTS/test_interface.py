"""Hosted C selection, formula-bar, dialog-request and display tests.

The field synchronization below models the native text-control adapter.
It is not an execution of the GEOS UI library; native adapters are tested
separately against the controlled instruction harness.
"""
import ctypes as C, os, tempfile, unittest
from pathlib import Path
from test_core import LIB,BOOK,val,source,msg
ENTRY=(C.c_char*128).in_dll(LIB,'entry')
ADDRESS=(C.c_char*16).in_dll(LIB,'address_entry')
AUX=(C.c_char*128).in_dll(LIB,'aux_entry')
EDITOR=(C.c_char*64).in_dll(LIB,'editor_text')
SELECTED=(C.c_char*8).in_dll(LIB,'selected_name')
FILE=(C.c_char*128).in_dll(LIB,'dialog_file')
DIR=(C.c_char*104).in_dll(LIB,'dialog_dir')
def word(name):return C.c_ushort.in_dll(LIB,name)
def integer(name):return C.c_int.in_dll(LIB,name).value
class Primitive(C.Structure):
    _pack_=1
    _fields_=[(n,C.c_ushort) for n in ('kind','x','y','x2','y2','color')]+[('text',C.c_char*64)]
def action(n,text=None):
    if text is not None:
        dest=ADDRESS if n==15 else AUX if n==18 else FILE if n in (26,27) else ENTRY
        dest.value=text.encode('ascii')
    LIB.native_action(n)
    if word('native_sync').value:
        ENTRY.value=EDITOR.value;ADDRESS.value=SELECTED.value
    return word('native_request').value
def click(x,y,double=False):
    word('pointer_x').value=x;word('pointer_y').value=y;word('pointer_info').value=0x40 if double else 0;return action(14)
def key(k,flags=4):
    word('key_char').value=k;word('key_flags').value=flags;return action(30)
def keys(s):
    for ch in s:key(ord(ch))
def goto(addr):return action(15,addr)
def putat(addr,raw):goto(addr);action(1,raw)
class InterfaceTests(unittest.TestCase):
    def setUp(self):
        LIB.test_faults(0,0,0);word('native_path_ok').value=1
        word('sheet_disk').value=word('dialog_disk').value=0x1001
        (C.c_char*104).in_dll(LIB,'sheet_dir').value=DIR.value=b'\\'
        action(0)
    def test_click_and_enter_acceptance(self):
        click(40,30);action(1,'10');action(1,'20');action(1,'=SUM(A1:A2)')
        self.assertEqual(val('A3'),'30');click(40,30);action(1,'100')
        self.assertEqual(val('A3'),'120');self.assertEqual(source('A3'),'=SUM(A1:A2)')
    def test_selected_formula_bar_retains_formula_not_result(self):
        putat('B5','=2+3');goto('B5');self.assertEqual(ENTRY.value,b'=2+3')
        self.assertEqual(SELECTED.value,b'B5');self.assertEqual(word('native_focus').value,2)
    def test_enter_moves_down_and_syncs_new_cell(self):
        action(1,'hello');self.assertEqual(SELECTED.value,b'A2');self.assertEqual(ENTRY.value,b'')
        self.assertEqual(source('A1'),'hello')
    def test_click_commits_old_pending_edit(self):
        ENTRY.value=b'pending';click(145,52)
        self.assertEqual(source('A1'),'pending');self.assertEqual(SELECTED.value,b'B2')
        self.assertEqual(ENTRY.value,b'')
    def test_revert_does_not_mutate_sheet(self):
        putat('A1','old');goto('A1');ENTRY.value=b'pending';action(24)
        self.assertEqual(source('A1'),'old');self.assertEqual(ENTRY.value,b'old')
    def test_click_headers_and_outside_does_not_commit(self):
        ENTRY.value=b'pending'
        for p in ((0,0),(31,24),(32,23),(492,25),(32,224),(65535,65535)):
            click(*p);self.assertEqual(BOOK.count,0);self.assertEqual(SELECTED.value,b'A1')
    def test_far_cell_and_edge_selection(self):
        goto('Z999');action(1,'edge')
        self.assertEqual(source('Z999'),'edge');self.assertEqual(SELECTED.value,b'Z999')
        self.assertEqual((integer('first_row'),integer('first_col')),(990,25))
        click(136,24);click(36,223)
        self.assertEqual(SELECTED.value,b'Z999')
    def test_invalid_address_keeps_selected_and_pending_input(self):
        ENTRY.value=b'pending'
        for s in ('AA1','A1000','0','Z0'):
            goto(s);self.assertEqual(BOOK.count,0);self.assertEqual(SELECTED.value,b'A1')
        self.assertEqual(ENTRY.value,b'pending')
    def test_native_clear_and_fill_with_relative_references(self):
        putat('B1','5');putat('B2','7');putat('A1','=B1+$B$1');goto('A1')
        self.assertEqual(action(17),3);self.assertEqual(action(18,'A2:A3'),5)
        self.assertEqual(source('A2'),'=B2+$B$1');self.assertEqual(val('A2'),'12')
        goto('A3');action(16);self.assertEqual(source('A3'),'');action(5)
        self.assertEqual(source('A3'),'=B3+$B$1')
    def test_invalid_fill_keeps_sheet_and_dialog_open(self):
        putat('A1','keep');goto('A1');action(17)
        self.assertEqual(action(18,'XX1:YY2'),0);self.assertEqual(BOOK.count,1)
    def test_dirty_new_cancel_and_discard(self):
        action(1,'keep');self.assertEqual(action(11),4);self.assertEqual(source('A1'),'keep')
        self.assertEqual(action(23),5);self.assertEqual(source('A1'),'keep')
        action(11);self.assertEqual(action(22),5);self.assertEqual(BOOK.count,0)
    def test_dirty_open_confirmation_precedes_browser(self):
        ENTRY.value=b'pending';self.assertEqual(action(2),4)
        self.assertEqual(source('A1'),'pending');self.assertEqual(action(22),1)
        self.assertEqual(BOOK.count,0)
    def test_save_without_path_requests_native_save_as(self):
        action(1,'123');self.assertEqual(action(3),2)
        word('native_path_ok').value=0;self.assertEqual(action(4),2)
    def test_native_save_open_reopen_and_copies(self):
        old=os.getcwd()
        try:
            with tempfile.TemporaryDirectory(prefix='mc-') as t:
                os.chdir(t);action(1,'7');action(4);self.assertEqual(action(27,'A.MCS'),5)
                goto('A1');action(1,'8');action(3)
                self.assertIn(b'A1\t8',Path('A.MCS').read_bytes());self.assertTrue(Path('A.C00').is_file())
                action(11);action(2);self.assertEqual(action(26,'A.MCS'),5);self.assertEqual(val('A1'),'8')
        finally:os.chdir(old)
    def test_dialog_filename_not_a_path(self):
        action(4)
        for text in ('','C:\\X.MCS','SUB/X.MCS','LONGFILENAME.MCS'):
            self.assertEqual(action(27,text),0);self.assertEqual(word('native_success').value,0)
    def test_help_uses_native_request_without_replacing_grid(self):
        before=[bytes(p) for p in (Primitive*112).in_dll(LIB,'drawing')[:word('drawing_count').value]]
        self.assertEqual(action(10),6)
        draw=(Primitive*112).in_dll(LIB,'drawing');count=word('drawing_count').value
        self.assertEqual([bytes(p) for p in draw[:count]],before)
        self.assertTrue(1<count<=112)
        for p in draw[:count]:
            self.assertLess(p.x,512);self.assertLess(p.y,280);self.assertIn(p.color,(0,7,15))
            if p.kind==0:self.assertLess(p.x2,512);self.assertLess(p.y2,280)
    def test_paging_stops_at_edges_and_selects_visible_cell(self):
        for _ in range(110):action(7);action(9)
        self.assertEqual((integer('first_row'),integer('first_col')),(990,25))
        for _ in range(110):action(6);action(8)
        self.assertEqual((integer('first_row'),integer('first_col')),(0,0))
        self.assertEqual(SELECTED.value,b'A1')
    def test_button_undo_redo(self):
        putat('A1','1');putat('A1','2');action(5);self.assertEqual(val('A1'),'1')
        action(5);self.assertEqual(val('A1'),'2')
    def test_full_input_length_and_reject_overflow_before_click(self):
        goto('Z999');action(1,'x'*63);self.assertEqual(source('Z999'),'x'*63)
        ENTRY.value=b'y'*64;click(36,24)
        self.assertEqual(SELECTED.value,b'Z999');self.assertEqual(source('Z999'),'x'*63)
    def test_close_action_commits_pending_edit(self):
        ENTRY.value=b'=2+3';action(28);self.assertEqual(val('A1'),'5')
    def test_direct_typing_and_recalculation(self):
        click(40,30);keys('10');key(0xff0d);keys('20');key(0xff0d)
        keys('=SUM(A1:A2)');key(0xff0d)
        self.assertEqual(val('A3'),'30');click(40,30);keys('100');key(0xff0d)
        self.assertEqual(val('A3'),'120');self.assertEqual(source('A3'),'=SUM(A1:A2)')
    def test_f2_edit_and_escape_restore(self):
        putat('A1','=2+3');click(40,30);key(0xff81)
        self.assertEqual(ENTRY.value,b'=2+3');key(0xff93);keys('0');key(0xff0d)
        self.assertEqual(source('A1'),'=2+03');click(40,30);keys('wrong');key(0xff1b)
        self.assertEqual(ENTRY.value,b'=2+03');self.assertEqual(source('A1'),'=2+03')
    def test_double_click_preserves_and_backspace_edits(self):
        putat('B2','abc');click(140,50,True);self.assertEqual(integer('edit_active'),1)
        self.assertEqual(ENTRY.value,b'abc');key(0xff08);keys('Z');key(0xff0d)
        self.assertEqual(source('B2'),'abZ')
    def test_shift_selection_and_control_a(self):
        putat('A1','abcdef');click(40,30);key(0xff81)
        key(0xff93,0x804);key(0xff93,0x804);keys('XY');key(0xff0d)
        self.assertEqual(source('A1'),'abcdXY');click(40,30);key(0xff81)
        key(ord('a'),0x2004);keys('new');key(0xff0d)
        self.assertEqual(source('A1'),'new')
    def test_arrows_tab_and_home_navigation(self):
        click(40,30);key(0xff92);self.assertEqual(SELECTED.value,b'B1')
        key(0xff91);self.assertEqual(SELECTED.value,b'B2')
        key(0xff09,0x804);self.assertEqual(SELECTED.value,b'A2')
        key(0xff0d,0x804);self.assertEqual(SELECTED.value,b'A1')
        goto('Z999');key(0xff92);key(0xff91);self.assertEqual(SELECTED.value,b'Z999')
        key(0xff94,0x2004);self.assertEqual(SELECTED.value,b'A1')
    def test_keyboard_release_alt_and_unknown_leave_input(self):
        for code,flags in [(ord('x'),1),(ord('x'),0x8004),(0xff82,4),(ord('x'),0x84)]:
            key(code,flags);self.assertEqual(word('key_handled').value,0);self.assertEqual(ENTRY.value,b'')
        keys('a');key(ord('b'),2);self.assertEqual(ENTRY.value,b'ab')
    def test_long_incell_edit_scroll_and_caret_bounds(self):
        keys('x'*63);keys('y');self.assertEqual(len(ENTRY.value),63)
        self.assertGreater(integer('edit_scroll'),0)
        count=word('drawing_count').value
        self.assertLessEqual(count,112)
        for p in (Primitive*112).in_dll(LIB,'drawing')[:count]:
            self.assertLess(p.x,512);self.assertLess(p.y,280)
            if p.kind==0:self.assertLess(p.x2,512);self.assertLess(p.y2,280)
        key(0xff94);self.assertEqual(integer('edit_cursor'),0);self.assertEqual(integer('edit_scroll'),0)
        key(0xff9a);key(0xff0d);self.assertEqual(source('A1'),'x'*62)
    def test_click_in_edited_cell_positions_caret(self):
        keys('abc');click(42,30);self.assertEqual(integer('edit_cursor'),1)
        keys('Z');key(0xff0d);self.assertEqual(source('A1'),'aZbc')
    def test_help_does_not_commit_pending_cell(self):
        keys('pending');self.assertEqual(key(0xff80),6)
        self.assertEqual(BOOK.count,0);self.assertEqual(ENTRY.value,b'pending')
    def test_edit_menu_action_keeps_original_input(self):
        putat('A1','123');goto('A1');action(29)
        self.assertEqual(integer('edit_active'),1);self.assertEqual(ENTRY.value,b'123')
    def test_pending_keyboard_input_is_saved(self):
        old=os.getcwd()
        try:
            with tempfile.TemporaryDirectory(prefix='mc-') as t:
                os.chdir(t);keys('=2+3');action(4);action(27,'KEYS.MCS')
                self.assertEqual(val('A1'),'5');self.assertIn(b'A1\t=2+3',Path('KEYS.MCS').read_bytes())
        finally:os.chdir(old)
    def test_native_numeric_keypad_characters(self):
        for k in (0xff31,0xff32,0xff2e,0xff35):key(k)
        key(0xff0d);self.assertEqual(val('A1'),'12.5')
if __name__=='__main__':unittest.main(verbosity=2)
