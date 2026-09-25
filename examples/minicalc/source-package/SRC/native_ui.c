#include "calc.h"
/* Native selection/editor model. No DOS calls. All geometry is in unscaled
 * document coordinates; the native GenView delivers those same coordinates. */
#include "ui_layout.h"
#define TEXT_CAP 64
typedef struct __attribute__((packed)){u16 type,x,y,x2,y2,color;char text[TEXT_CAP];} Primitive;
Primitive drawing[DRAW_LIMIT];u16 drawing_count;
char entry[128],address_entry[16],aux_entry[128];
char editor_text[64],selected_name[8];
const char default_filename[]="SHEET.MCS";
char sheet_dir[104],dialog_dir[104],dialog_file[128];
u16 sheet_disk,dialog_disk,native_path_ok,native_request,native_sync,native_focus,native_success;
u16 pointer_x,pointer_y,pointer_info,key_char,key_flags,key_handled;
int edit_active,edit_cursor,edit_anchor,edit_scroll;
int chosen_row,chosen_col,first_row,first_col,native_dirty;
static int pending_action;
#ifndef MINICALC_HOST_UI
extern int native_file(int operation,const char*p,unsigned arg,const char*q);
static int enter_dir(const char*p,u16 disk){return native_file(7,p,disk,0)>=0;}
static void leave_dir(void){native_file(8,0,0,0);}
#else
/* Hosted model does not emulate GEOS disk handles. Instruction tests do. */
static int enter_dir(const char*p,u16 disk){(void)p;(void)disk;return 1;}
static void leave_dir(void){}
#endif
static void text(int x,int y,const char*s,int color){Primitive*p;if(drawing_count>=DRAW_LIMIT)return;p=&drawing[drawing_count++];m_zero(p,sizeof(*p));p->type=1;p->x=x;p->y=y;p->color=color;s_copy(p->text,s,TEXT_CAP);}
static void rect(int x,int y,int x2,int y2,int color){Primitive*p;if(drawing_count>=DRAW_LIMIT)return;p=&drawing[drawing_count++];m_zero(p,sizeof(*p));p->x=x;p->y=y;p->x2=x2;p->y2=y2;p->color=color;}
static void uint_text(unsigned n,char*out){char t[12];int i=0;do{t[i++]=(char)('0'+n%10);n/=10;}while(n);while(i)*out++=t[--i];*out=0;}
static void cat(char*d,const char*s,unsigned cap){unsigned n=s_len(d);if(n<cap)s_copy(d+n,s,cap-n);}
static int ieq(const char*a,const char*b){while(*a&&ascii_upper(*a)==ascii_upper(*b)){a++;b++;}return *a==*b;}
static void keep_visible(void){if(chosen_row<first_row||chosen_row>=first_row+SHOWN_ROWS)first_row=chosen_row/SHOWN_ROWS*SHOWN_ROWS;if(chosen_col<first_col||chosen_col>=first_col+SHOWN_COLS)first_col=chosen_col/SHOWN_COLS*SHOWN_COLS;}
static void sync_cell(int focus){int i=find_cell(&book,chosen_row,chosen_col);cell_name(chosen_row,chosen_col,selected_name);s_copy(editor_text,i>=0?book.cells[i].input:"",64);native_sync=1;native_focus=focus?2:0;edit_active=edit_cursor=edit_anchor=edit_scroll=0;}
static int commit(void){int i=find_cell(&book,chosen_row,chosen_col);const char*old=i>=0?book.cells[i].input:"";
 if(!s_eq(entry,old)){if(!edit_cell(chosen_row,chosen_col,entry))return 0;s_copy(message,"Cell updated.",160);}
 edit_active=edit_cursor=edit_anchor=edit_scroll=0;return 1;
}
/* All worksheet text uses the target's URW Mono 10-point font (0x1a00).
 * Fixed six-point advances keep hit tests and the in-cell caret aligned.
 * Native menus, dialogs and formula bar keep the user's system font. */
static void wrap_message(const char*s,int y){char b[TEXT_CAP];unsigned i=0,n;while(s[i]&&y<VIEW_H-10){n=0;while(s[i]&&n<62)b[n++]=s[i++];b[n]=0;text(5,y,b,0);y+=12;}}
static void update_edit(void){int n=(int)s_len(entry);if(edit_cursor>n)edit_cursor=n;if(edit_anchor>n)edit_anchor=n;
 if(edit_cursor<edit_scroll)edit_scroll=edit_cursor;
 if(edit_cursor>edit_scroll+EDIT_CHARS)edit_scroll=edit_cursor-EDIT_CHARS;
 s_copy(editor_text,entry,64);cell_name(chosen_row,chosen_col,selected_name);native_sync=1;
}
static void begin_edit(int replace){if(replace)entry[0]=0;edit_active=1;edit_cursor=(int)s_len(entry);edit_anchor=edit_cursor;edit_scroll=0;native_focus=2;update_edit();s_copy(message,"Editing: Enter accepts; Esc cancels; arrows move the caret.",160);}
static void delete_selection(void){int a=edit_cursor<edit_anchor?edit_cursor:edit_anchor,b=edit_cursor>edit_anchor?edit_cursor:edit_anchor;unsigned i;if(a==b)return;for(i=a;entry[i+b-a];i++)entry[i]=entry[i+b-a];entry[i]=0;edit_cursor=edit_anchor=a;}
static void move_caret(int pos,int extend){int n=(int)s_len(entry);if(pos<0)pos=0;if(pos>n)pos=n;edit_cursor=pos;if(!extend)edit_anchor=pos;update_edit();}
static void move_cell(int dr,int dc){if(!commit())return;chosen_row+=dr;chosen_col+=dc;if(chosen_row<0)chosen_row=0;if(chosen_row>=ROW_LIMIT)chosen_row=ROW_LIMIT-1;if(chosen_col<0)chosen_col=0;if(chosen_col>=COL_LIMIT)chosen_col=COL_LIMIT-1;keep_visible();sync_cell(1);}
static void keyboard(void){unsigned k=key_char,mods=key_flags>>8;int n,i,shift=(mods&12)!=0,ctrl=(mods&48)!=0;key_handled=0;
 /* Ignore releases, state-key and temporary-accent notifications. Leave
  * Alt/menu shortcuts and unsupported combinations to the native superclass. */
 if((key_flags&0x89)||!(key_flags&6)||(mods&0xc0))return;
 if(k==0xff80){native_request=6;key_handled=1;return;}
 if(k==0xff81&&!ctrl){begin_edit(0);key_handled=1;return;}
 if(k==0xff1b){if(edit_active){sync_cell(1);s_copy(message,"Edit cancelled. Original cell retained.",160);key_handled=1;}return;}
 if(k==0xff0d){key_handled=1;if(ctrl){if(commit())sync_cell(1);}else move_cell(shift?-1:1,0);return;}
 if(k==0xff09&&!ctrl){key_handled=1;move_cell(0,shift?-1:1);return;}
 if(ctrl){
  if(edit_active&&(k==1||k==0xff01||k=='a'||k=='A')){edit_anchor=0;edit_cursor=(int)s_len(entry);update_edit();key_handled=1;return;}
  if(!edit_active&&k==0xff94){if(commit()){chosen_row=chosen_col=0;keep_visible();sync_cell(1);}key_handled=1;return;}
  return;
 }
 if(k>=0xff90&&k<=0xff95){key_handled=1;
  if(edit_active&&(k==0xff92||k==0xff93||k==0xff94||k==0xff95)){
   int p=k==0xff94?0:k==0xff95?(int)s_len(entry):edit_cursor+(k==0xff92?1:-1);
   if(!shift&&edit_cursor!=edit_anchor&&(k==0xff92||k==0xff93))p=k==0xff92?(edit_cursor>edit_anchor?edit_cursor:edit_anchor):(edit_cursor<edit_anchor?edit_cursor:edit_anchor);
   move_caret(p,shift);
  }else if(k==0xff90||k==0xff91)move_cell(k==0xff90?-1:1,0);
  else if(k==0xff92||k==0xff93)move_cell(0,k==0xff92?1:-1);
  else {if(commit()){chosen_col=k==0xff94?0:COL_LIMIT-1;keep_visible();sync_cell(1);}}
  return;
 }
 if(k==0xff9a){key_handled=1;if(!edit_active){if(edit_cell(chosen_row,chosen_col,""))sync_cell(1);return;}n=(int)s_len(entry);if(edit_cursor==edit_anchor&&edit_cursor<n)edit_anchor++;delete_selection();update_edit();return;}
 if(k==0xff08){key_handled=1;if(!edit_active){begin_edit(1);return;}if(edit_cursor==edit_anchor&&edit_cursor>0)edit_anchor--;delete_selection();update_edit();return;}
 /* The native input ABI distinguishes numeric-keypad characters. */
 if(k>=0xff2a&&k<=0xff39)k&=0xff;
 if(k>=32&&k<=126){key_handled=1;if(!edit_active)begin_edit(1);delete_selection();n=(int)s_len(entry);if(n>=63){s_copy(message,"Cell input is limited to 63 characters.",160);return;}for(i=n+1;i>edit_cursor;i--)entry[i]=entry[i-1];entry[edit_cursor++]=(char)k;edit_anchor=edit_cursor;update_edit();return;}
}
static void draw_edit(int x,int y){char t[64];int i=0,n=(int)s_len(entry),a,b,start=edit_scroll,end=start+EDIT_CHARS;
 if(end>n)end=n;rect(x+1,y+1,x+CELL_W-3,y+CELL_H-3,15);
 a=edit_cursor<edit_anchor?edit_cursor:edit_anchor;b=edit_cursor>edit_anchor?edit_cursor:edit_anchor;
 if(a<start)a=start;if(b>end)b=end;
 /* Three short text runs are enough for a selected substring. */
 if(a<b){rect(x+4+(a-start)*CHAR_W,y+2,x+3+(b-start)*CHAR_W,y+CELL_H-4,0);
  for(i=start;i<a;i++)t[i-start]=entry[i];t[a-start]=0;text(x+4,y+4,t,0);
  for(i=a;i<b;i++)t[i-a]=entry[i];t[b-a]=0;text(x+4+(a-start)*CHAR_W,y+4,t,15);
  for(i=b;i<end;i++)t[i-b]=entry[i];t[end-b]=0;text(x+4+(b-start)*CHAR_W,y+4,t,0);
 }else {for(i=start;i<end;i++)t[i-start]=entry[i];t[end-start]=0;text(x+4,y+4,t,0);}
 x+=4+(edit_cursor-start)*CHAR_W;rect(x,y+2,x,y+CELL_H-4,0);
}
void prepare_display(void){int r,c,i,x,y;char b[128],v[70];drawing_count=0;native_dirty=changed;rect(0,0,VIEW_W-1,VIEW_H-1,15);
 rect(0,0,GRID_X+SHOWN_COLS*CELL_W-1,GRID_Y-1,7);rect(0,GRID_Y,GRID_X-1,GRID_Y+SHOWN_ROWS*CELL_H-1,7);
 for(c=0;c<=SHOWN_COLS;c++){x=GRID_X-1+c*CELL_W;rect(x,0,x,GRID_Y+SHOWN_ROWS*CELL_H,7);}
 for(r=0;r<=SHOWN_ROWS;r++){y=GRID_Y-1+r*CELL_H;rect(0,y,GRID_X+SHOWN_COLS*CELL_W-1,y,7);}
 for(c=0;c<SHOWN_COLS;c++){b[0]=(char)('A'+first_col+c);b[1]=0;if(first_col+c<COL_LIMIT)text(GRID_X+42+c*CELL_W,6,b,0);}
 for(r=0;r<SHOWN_ROWS;r++){if(first_row+r>=ROW_LIMIT)break;uint_text(first_row+r+1,b);text(5,GRID_Y+4+r*CELL_H,b,0);for(c=0;c<SHOWN_COLS;c++){if(first_col+c>=COL_LIMIT)break;cell_display(first_row+r,first_col+c,v,sizeof(v));if(s_len(v)>CELL_CHARS){v[CELL_CHARS-1]='~';v[CELL_CHARS]=0;}text(GRID_X+4+c*CELL_W,GRID_Y+4+r*CELL_H,v,0);}}
 if(chosen_row>=first_row&&chosen_row<first_row+SHOWN_ROWS&&chosen_col>=first_col&&chosen_col<first_col+SHOWN_COLS){x=GRID_X+(chosen_col-first_col)*CELL_W;y=GRID_Y+(chosen_row-first_row)*CELL_H;
  if(edit_active)draw_edit(x,y);
  rect(x,y,x+CELL_W-2,y,0);rect(x,y+CELL_H-2,x+CELL_W-2,y+CELL_H-2,0);rect(x,y,x,y+CELL_H-2,0);rect(x+CELL_W-2,y,x+CELL_W-2,y+CELL_H-2,0);
 }
 rect(0,228,VIEW_W-1,228,7);s_copy(b,document_path[0]?document_path:"Untitled",128);if(changed)cat(b," *",128);cat(b,"     ",128);cell_name(chosen_row,chosen_col,v);cat(b,v,128);if(edit_active)cat(b,"  [editing]",128);else {i=find_cell(&book,chosen_row,chosen_col);if(i>=0){cat(b," = ",128);cell_display(chosen_row,chosen_col,v,sizeof(v));cat(b,v,128);}}text(5,233,b,0);wrap_message(message,251);
}
static void new_sheet(void){new_book();chosen_row=chosen_col=first_row=first_col=0;sync_cell(0);s_copy(message,"Click, then type. F2 edits the formula; Enter accepts; Esc cancels.",160);}
static void request_document(int action){if(!commit())return;if(changed){pending_action=action;native_request=4;s_copy(message,"This sheet has unsaved changes. Discard them?",160);return;}if(action==2){native_request=1;s_copy(message,"Select an MCS working file, then choose Open.",160);}else new_sheet();}
static int valid_leaf(void){unsigned n=s_len(dialog_file),i;if(!n||n>12){s_copy(message,"Use a DOS 8.3 filename, such as BUDGET.MCS.",160);return 0;}for(i=0;i<n;i++){if(dialog_file[i]=='/'||dialog_file[i]=='\\'||dialog_file[i]==':'){s_copy(message,"Choose the directory above; enter a filename only.",160);return 0;}dialog_file[i]=(char)ascii_upper(dialog_file[i]);}return 1;}
static void document_io(int save,int selected){int ok;char oldpath[PATH_LIMIT];const char*dir=selected?dialog_dir:sheet_dir;u16 disk=selected?dialog_disk:sheet_disk;
 if(!native_path_ok&&!selected){s_copy(message,"Choose a folder with File > Save As first.",160);return;}
 if(selected&&!valid_leaf())return;
 if(!enter_dir(dir,disk)){s_copy(message,"Cannot enter the selected directory. No file changed.",160);return;}
 s_copy(oldpath,document_path,sizeof(oldpath));
 /* The same leaf in another directory is NOT the current saved document. */
 if(save&&selected&&(disk!=sheet_disk||!ieq(dir,sheet_dir)))document_path[0]=0;
 ok=save?save_document(selected?dialog_file:oldpath):read_document(dialog_file);
 if(!ok&&save)s_copy(document_path,oldpath,PATH_LIMIT);
 leave_dir();
 if(ok){if(selected){sheet_disk=disk;s_copy(sheet_dir,dir,sizeof(sheet_dir));native_path_ok=1;native_request=5;}if(!save){chosen_row=chosen_col=first_row=first_col=0;}native_success=1;sync_cell(0);}
}
/* Native trigger actions; file dialog commits (26/27) are private adapters.
 * Requests: 1 open;2 save-as;3 fill;4 discard confirmation;5 dismiss current;6 native help. */
void native_action(int action){int r,c;native_request=native_sync=native_focus=native_success=0;
 if(action==0){new_sheet();entry[0]=address_entry[0]=aux_entry[0]=0;pending_action=0;}
 else if(action==1){if(commit()){if(chosen_row+1<ROW_LIMIT)chosen_row++;keep_visible();sync_cell(1);}}
 else if(action==2||action==11){request_document(action);}
 else if(action==3){if(commit()){sync_cell(0);if(document_path[0]&&native_path_ok)document_io(1,0);else {native_request=2;s_copy(message,"Choose a folder and a new MCS filename.",160);}}}
 else if(action==4){if(commit()){sync_cell(0);native_request=2;s_copy(message,"Choose a folder and a new MCS filename.",160);}}
 else if(action==5){undo_book();sync_cell(0);}
 else if(action>=6&&action<=9){if(commit()){if(action==6&&first_row>=SHOWN_ROWS)first_row-=SHOWN_ROWS;if(action==7&&first_row+SHOWN_ROWS<ROW_LIMIT)first_row+=SHOWN_ROWS;if(action==8&&first_col>=SHOWN_COLS)first_col-=SHOWN_COLS;if(action==9&&first_col+SHOWN_COLS<COL_LIMIT)first_col+=SHOWN_COLS;chosen_row=first_row;chosen_col=first_col;sync_cell(0);}}
 else if(action==10){native_request=6;}
 else if(action==13){pending_action=0;native_path_ok=0;sync_cell(0);s_copy(message,"Session restored. Save As confirms the folder before saving.",160);}
 else if(action==14){if(pointer_x>=GRID_X&&pointer_x<GRID_X+CELL_W*SHOWN_COLS&&pointer_y>=GRID_Y&&pointer_y<GRID_Y+CELL_H*SHOWN_ROWS){r=first_row+(pointer_y-GRID_Y)/CELL_H;c=first_col+(pointer_x-GRID_X)/CELL_W;if(r<ROW_LIMIT&&c<COL_LIMIT){
 if(edit_active&&r==chosen_row&&c==chosen_col){int p=edit_scroll+((int)(pointer_x-GRID_X)%CELL_W-4+CHAR_W/2)/CHAR_W;move_caret(p,0);native_focus=2;}
 else if(commit()){chosen_row=r;chosen_col=c;sync_cell(1);if(pointer_info&0x40){int i=find_cell(&book,r,c);s_copy(entry,i>=0?book.cells[i].input:"",128);begin_edit(0);}}
 }}}
 else if(action==15){if(address(address_entry,&r,&c)){if(commit()){chosen_row=r;chosen_col=c;keep_visible();sync_cell(1);}}else s_copy(message,"Enter a cell address, A1 through Z999, then choose Go.",160);}
 else if(action==16){if(edit_cell(chosen_row,chosen_col,"")){sync_cell(1);s_copy(message,"Cell cleared. Edit > Undo restores it.",160);}}
 else if(action==17){if(commit()){sync_cell(0);native_request=3;s_copy(message,"Enter a destination such as B1:B10.",160);}}
 else if(action==18){if(copy_range(chosen_row,chosen_col,aux_entry)){native_request=5;sync_cell(0);}}
 else if(action==22){if(pending_action){int p=pending_action;pending_action=0;new_sheet();native_request=p==2?1:5;if(p==2)s_copy(message,"Select an MCS working file, then choose Open.",160);}}
 else if(action==23){pending_action=0;native_request=5;}
 else if(action==24){sync_cell(1);s_copy(message,"Uncommitted edit cancelled.",160);}
 else if(action==26){if(changed)s_copy(message,"Unsaved changes: cancel this dialog and save first.",160);else document_io(0,1);}
 else if(action==27){document_io(1,1);}
 else if(action==28){commit();}
 else if(action==29){begin_edit(0);}
 else if(action==30){keyboard();}
 prepare_display();
}
#ifndef MINICALC_HOST_UI
int file_open(const char*p){return native_file(0,p,0,0);}int file_create_new(const char*p){return native_file(1,p,0,0);}int file_read(int h,void*b,unsigned n){return native_file(2,b,n,(const char*)(unsigned)h);}int file_write(int h,const void*b,unsigned n){return native_file(3,b,n,(const char*)(unsigned)h);}int file_close(int h){return native_file(4,0,0,(const char*)(unsigned)h);}int file_rename(const char*p,const char*q){return native_file(5,p,0,q);}int file_remove(const char*p){return native_file(6,p,0,0);}
#endif
