#include "calc.h"
char document_path[PATH_LIMIT];
u32 saved_master_hash,saved_master_size,saved_view_hash,saved_view_size;
int master_known,view_known;
static int order[CELL_LIMIT];
static u8 buffer[512];
static int reader_fd,reader_at,reader_count,reader_failed;
static int writer_fd,writer_count,writer_failed;
static u32 writer_hash,writer_size;
static u32 export_hash,export_size;
void reset_session(void){document_path[0]=0;master_known=view_known=0;saved_master_hash=saved_master_size=saved_view_hash=saved_view_size=0;}
static void append(char*out,const char*in){unsigned n=s_len(out);s_copy(out+n,in,PATH_LIMIT-n);}
static void replace_ext(const char*path,const char*ext,char*out){char*p;s_copy(out,path,PATH_LIMIT);p=out+s_len(out);while(p>out&&p[-1]!='.'&&p[-1]!='/'&&p[-1]!='\\')p--;if(p>out&&p[-1]=='.')p[-1]=0;append(out,ext);}
static int iequal(const char*a,const char*b){while(*a&&ascii_upper(*a)==ascii_upper(*b)){a++;b++;}return *a==*b;}
int normalize_path(const char*path,char*master,char*view,int*is_view){const char*leaf=path,*p,*dot=0;char name[10];unsigned n=s_len(path),k=0;
 if(!n||n>=PATH_LIMIT-5){s_copy(message,"Use a DOS 8.3 filename and a path shorter than 75 characters.",160);return 0;}
 for(p=path;*p;p++){if((u8)*p<33||(u8)*p>126||*p=='*'||*p=='?'||*p=='"'||*p=='|'){s_copy(message,"The path contains an unsupported character.",160);return 0;}if(*p=='/'||*p=='\\'||*p==':')leaf=p+1;}
 for(p=leaf;*p;p++){if(*p=='.'){dot=p;break;}if(k>=8||!((ascii_upper(*p)>='A'&&ascii_upper(*p)<='Z')||digit(*p)||*p=='_'||*p=='-'))goto bad;name[k++]=(char)ascii_upper(*p);}name[k]=0;if(!k)goto bad;
 if(s_eq(name,"CON")||s_eq(name,"PRN")||s_eq(name,"AUX")||s_eq(name,"NUL")||s_eq(name,"CLOCK$")||(k==4&&((name[0]=='C'&&name[1]=='O'&&name[2]=='M')||(name[0]=='L'&&name[1]=='P'&&name[2]=='T'))&&digit(name[3])))goto bad;
 *is_view=0;if(dot){if(iequal(dot,".WK1"))*is_view=1;else if(!iequal(dot,".MCS")){s_copy(message,"Open .MCS working files or their matching .WK1 display copies only.",160);return 0;}}
 s_copy(master,path,PATH_LIMIT);if(dot)master[dot-path]=0;append(master,".MCS");replace_ext(master,".WK1",view);return 1;
 bad:s_copy(message,"Use a non-device DOS base name of 1-8 letters, digits, '-' or '_'.",160);return 0;
}
int file_digest(const char*path,u32*hash,u32*size){int f,n,close_result;u32 h=2166136261U,s=0;u8 b[256];f=file_open(path);if(f==-2||f==-3)return 0;if(f<0)return -1;
 while((n=file_read(f,b,sizeof(b)))>0){h=fnv_bytes(h,b,(unsigned)n);s+=(u32)n;if(s>1048576U){file_close(f);return -1;}}
 close_result=file_close(f);if(n<0||close_result<0)return -1;*hash=h;*size=s;return 1;
}
static void reader_init(int fd){reader_fd=fd;reader_at=reader_count=reader_failed=0;}
static int get_byte(void){if(reader_at==reader_count){reader_count=file_read(reader_fd,buffer,sizeof(buffer));reader_at=0;if(reader_count<0){reader_failed=1;return -1;}if(!reader_count)return -1;}return buffer[reader_at++];}
static int read_line(char*out,int cap){int c,n=0;while((c=get_byte())>=0){if(c=='\n'){out[n]=0;return 1;}if(c=='\r'){c=get_byte();if(c!='\n'){reader_failed=1;return 0;}out[n]=0;return 1;}
 if(n==cap-1||(c<32&&c!='\t')||c>126){reader_failed=1;return 0;}out[n++]=(char)c;}if(n)reader_failed=1;out[0]=0;return 0;}
static void hex8(u32 n,char*out){static const char h[]="0123456789ABCDEF";int i;for(i=7;i>=0;i--){out[i]=h[n&15];n>>=4;}out[8]=0;}
static int read_hex(const char*s,u32*out){int i,c;u32 n=0;for(i=0;i<8;i++){c=ascii_upper(s[i]);if(c>='0'&&c<='9')c-='0';else if(c>='A'&&c<='F')c=c-'A'+10;else return 0;n=(n<<4)|(u32)c;}if(s[8])return 0;*out=n;return 1;}
static void decimal_text(unsigned n,char*out){char t[12];int i=0;do{t[i++]=(char)('0'+n%10);n/=10;}while(n);while(i)*out++=t[--i];*out=0;}
static int parse_master(int fd,Sheet*s){char line[96],*tab,*end;int row,col,entries=0,footer=0,i;u32 h=2166136261U,expected;unsigned count;
 m_zero(s,sizeof(Sheet));reader_init(fd);if(!read_line(line,sizeof(line))||!s_eq(line,"MINICALC 1"))return 0;h=fnv_bytes(h,"MINICALC 1\n",11);
 while(read_line(line,sizeof(line))){if(line[0]=='E'&&line[1]=='N'&&line[2]=='D'&&line[3]=='\t'){
  count=0;end=line+4;if(!digit(*end))return 0;while(digit(*end)){count=count*10+(*end++-'0');if(count>CELL_LIMIT)return 0;}
  if(*end++!='\t'||!read_hex(end,&expected)||expected!=h||count!=(unsigned)entries)return 0;footer=1;break;
 }
 h=fnv_bytes(h,line,s_len(line));h=fnv_bytes(h,"\n",1);tab=0;for(i=0;line[i];i++)if(line[i]=='\t'){if(tab)return 0;tab=line+i;}
 if(!tab)return 0;*tab++=0;if(!*tab||!address(line,&row,&col)||find_cell(s,row,col)>=0||!put_cell(s,row,col,tab))return 0;entries++;}
 if(!footer||get_byte()!=-1||reader_failed)return 0;return 1;
}
static void writer_init(int fd){writer_fd=fd;writer_count=writer_failed=0;writer_hash=2166136261U;writer_size=0;}
static void flush(void){int n;if(writer_count&&!writer_failed&&writer_fd>=0){n=file_write(writer_fd,buffer,(unsigned)writer_count);if(n!=writer_count)writer_failed=1;}writer_count=0;}
static void emit(const void*data,unsigned count){const u8*p=data;writer_hash=fnv_bytes(writer_hash,data,count);writer_size+=count;while(count--){buffer[writer_count++]=*p++;if(writer_count==(int)sizeof(buffer))flush();}}
static void sort_cells(void){int i,j,t;for(i=0;i<book.count;i++)order[i]=i;for(i=1;i<book.count;i++){t=order[i];j=i;while(j&&((int)book.cells[order[j-1]].row*26+book.cells[order[j-1]].col) > ((int)book.cells[t].row*26+book.cells[t].col)){order[j]=order[j-1];j--;}order[j]=t;}}
int write_master(int fd){int i;char addr[8],count[12],hash[9];u32 content_hash=2166136261U;const Cell*c;writer_init(fd);emit("MINICALC 1\r\n",12);content_hash=fnv_bytes(content_hash,"MINICALC 1\n",11);sort_cells();
 for(i=0;i<book.count;i++){c=&book.cells[order[i]];cell_name(c->row,c->col,addr);emit(addr,s_len(addr));emit("\t",1);emit(c->input,s_len(c->input));emit("\r\n",2);
 content_hash=fnv_bytes(content_hash,addr,s_len(addr));content_hash=fnv_bytes(content_hash,"\t",1);content_hash=fnv_bytes(content_hash,c->input,s_len(c->input));content_hash=fnv_bytes(content_hash,"\n",1);}
 decimal_text(book.count,count);hex8(content_hash,hash);emit("END\t",4);emit(count,s_len(count));emit("\t",1);emit(hash,8);emit("\r\n",2);flush();return !writer_failed;
}
static void word(u8*out,unsigned v){out[0]=(u8)v;out[1]=(u8)(v>>8);}
static void record(unsigned op,const u8*payload,unsigned n){u8 h[4];word(h,op);word(h+2,n);emit(h,4);if(n)emit(payload,n);}
int write_view(int fd){u8 p[80];char display[INPUT_LIMIT+1];int i,rmax=0,cmax=0;const Cell*c;writer_init(fd);word(p,0x0406);record(0,p,2);sort_cells();
 for(i=0;i<book.count;i++){if(book.cells[i].row>rmax)rmax=book.cells[i].row;if(book.cells[i].col>cmax)cmax=book.cells[i].col;}
 word(p,0);word(p+2,0);word(p+4,cmax);word(p+6,rmax);record(6,p,8);
 for(i=0;i<book.count;i++){c=&book.cells[order[i]];p[0]=0xFF;word(p+1,c->col);word(p+3,c->row);
  if(c->error||c->kind==K_TEXT){cell_display(c->row,c->col,display,sizeof(display));p[5]='\'';m_copy(p+6,display,s_len(display)+1);record(0x0F,p,7+s_len(display));}
  else if(c->value%SCALE==0 && c->value/SCALE>=-32768 && c->value/SCALE<=32767){word(p+5,(unsigned)(c->value/SCALE));record(0x0D,p,7);}
  else{ieee64(c->value,p+5);record(0x0E,p,13);}
 }record(1,0,0);flush();export_hash=writer_hash;export_size=writer_size;return !writer_failed;
}
int read_document(const char*path){char master[PATH_LIMIT],view[PATH_LIMIT];int requested_view,f,ok,status;u32 mh,ms,vh=0,vs=0,check_h,check_s;Sheet *s=&staging;
 if(!normalize_path(path,master,view,&requested_view))return 0;
 status=file_digest(master,&mh,&ms);if(status<=0){s_copy(message,"No readable MiniCalc .MCS file. Foreign WQ1/WK1 files are not editable here.",160);return 0;}
 f=file_open(master);if(f<0){s_copy(message,"Cannot open the working file; current sheet retained.",160);return 0;}
 ok=parse_master(f,s);if(file_close(f)<0)ok=0;if(!ok){undo_ready=0;s_copy(message,"Invalid, damaged or unsupported working file; current sheet retained.",160);return 0;}
 status=file_digest(view,&vh,&vs);if(status<0){undo_ready=0;s_copy(message,"Cannot read the matching WK1 file; current sheet retained.",160);return 0;}
 /* Make the load transactional, including verification of a Viewer-launched
    companion. Swap permits export hashing without losing the current book. */
 {Cell temp;int i,count=book.count;for(i=0;i<CELL_LIMIT;i++){temp=book.cells[i];book.cells[i]=staging.cells[i];staging.cells[i]=temp;}book.count=staging.count;staging.count=count;}
 recalculate();write_view(-1);ok=(!requested_view || (status==1&&vh==export_hash&&vs==export_size));
 /* Reject a working file changed during validation as well. */
 if(file_digest(master,&check_h,&check_s)!=1||check_h!=mh||check_s!=ms)ok=0;
 if(!ok){Cell temp;int i,count=book.count;for(i=0;i<CELL_LIMIT;i++){temp=book.cells[i];book.cells[i]=staging.cells[i];staging.cells[i]=temp;}book.count=staging.count;staging.count=count;recalculate();undo_ready=0;s_copy(message,"WK1 does not match its .MCS companion, or the input changed; load cancelled.",160);return 0;}
 s_copy(document_path,master,PATH_LIMIT);master_known=1;saved_master_hash=mh;saved_master_size=ms;view_known=status==1&&vh==export_hash&&vs==export_size;saved_view_hash=vh;saved_view_size=vs;changed=undo_ready=0;
 if(status==1&&!view_known)s_copy(message,"Loaded .MCS; WK1 differs. Use Save As to avoid overwriting that file.",160);else s_copy(message,"Working file loaded. Formulas recalculated; original expressions retained.",160);return 1;
}
static int unique_path(const char*master,char letter,char*out,int create){char ext[5];int i,f;u32 h,s;ext[0]='.';ext[1]=letter;ext[4]=0;for(i=0;i<100;i++){ext[2]=(char)('0'+i/10);ext[3]=(char)('0'+i%10);replace_ext(master,ext,out);
 if(create){f=file_create_new(out);if(f>=0)return f;if(f!=-80){out[0]=0;return -1;}}
 else{f=file_digest(out,&h,&s);if(f==0)return 0;if(f<0){out[0]=0;return -1;}}}
 out[0]=0;return -1;
}
static int same_version(const char*path,int expected,u32 hash,u32 size){u32 h=0,s=0;int found=file_digest(path,&h,&s);return expected?(found==1&&h==hash&&s==size):found==0;}
int save_document(const char*path){char master[PATH_LIMIT],view[PATH_LIMIT],mt[PATH_LIMIT],vt[PATH_LIMIT],mb[PATH_LIMIT],vb[PATH_LIMIT];int iv,same,me,ve,mf=-1,vf=-1,ok=0,mback=0,vback=0,mnew=0,vnew=0,rollback=1;u32 new_mh=0,new_ms=0,new_vh=0,new_vs=0;
 mt[0]=vt[0]=mb[0]=vb[0]=0;if(!normalize_path(path,master,view,&iv))return 0;same=s_eq(master,document_path);me=same&&master_known;ve=same&&view_known;
 if(!same_version(master,me,saved_master_hash,saved_master_size)||!same_version(view,ve,saved_view_hash,saved_view_size)){s_copy(message,"Save refused: destination exists or changed outside MiniCalc. Use a new name.",160);return 0;}
 recalculate();mf=unique_path(master,'T',mt,1);if(mf<0)goto failure;
 ok=write_master(mf);new_mh=writer_hash;new_ms=writer_size;if(file_close(mf)<0)ok=0;mf=-1;if(!ok)goto failure;
 vf=unique_path(master,'U',vt,1);if(vf<0)goto failure;ok=write_view(vf);new_vh=writer_hash;new_vs=writer_size;if(file_close(vf)<0)ok=0;vf=-1;if(!ok)goto failure;
 if(!same_version(master,me,saved_master_hash,saved_master_size)||!same_version(view,ve,saved_view_hash,saved_view_size))goto failure;
 if(me){if(unique_path(master,'C',mb,0)<0||file_rename(master,mb)<0)goto failure;mback=1;}
 if(ve){if(unique_path(master,'W',vb,0)<0||file_rename(view,vb)<0)goto failure;vback=1;}
 if(file_rename(mt,master)<0)goto failure;mnew=1;mt[0]=0;
 if(file_rename(vt,view)<0)goto failure;vnew=1;vt[0]=0;
 s_copy(document_path,master,PATH_LIMIT);saved_master_hash=new_mh;saved_master_size=new_ms;saved_view_hash=new_vh;saved_view_size=new_vs;master_known=view_known=1;changed=0;
 s_copy(message,"Saved formulas in .MCS and values in .WK1. Previous versions kept as backups.",160);return 1;
 failure:
 if(mf>=0)file_close(mf);if(vf>=0)file_close(vf);
 if(vnew&&file_remove(view)<0)rollback=0;if(mnew&&file_remove(master)<0)rollback=0;
 if(vback&&file_rename(vb,view)<0)rollback=0;if(mback&&file_rename(mb,master)<0)rollback=0;
 if(mt[0])file_remove(mt);if(vt[0])file_remove(vt);
 s_copy(message,rollback?"Save failed; previous documents retained. Check disk space/permissions/backups.":"Save/rollback failed. KEEP all .Cxx/.Wxx files: they contain previous versions.",160);return 0;
}
