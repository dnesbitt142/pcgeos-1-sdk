#define _GNU_SOURCE
#include <asm/ldt.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <ucontext.h>
#include <unistd.h>
/* Actual x86 execution using Linux LDT segments, with MODELED GEOS services.
 * Not a GEOS loader, DOS emulator, display driver, or live scheduler.
 * CPU probe is bypassed; CLI/STI are trapped in user mode. A simulated thread
 * switch scrambles upper 32-bit register halves at each interrupt window.
 */
static uint8_t *code,*dg,*engine,*nstack,*kernel,*temp,*state,*initial_engine;
static unsigned native_open_at,native_command_at,native_expose_at,native_close_at,native_select_at,native_key_at,probe_at;
static unsigned engine_used,entry_at,book_at,count_at,changed_at;
static int dirfd,logfd,script_count,script_pos,previous=-99;
static char lines[512][256],field[128],addrfield[16]="A1",namefield[128]="SHEET.MCS",rangefield[128]="B1:B10";
static char browser[2][104]={"\\","\\"},selection[40],current_path[104]="\\",path_stack[16][104];
static int currentfd,dir_stack[16],dir_depth,dialog,help_open,focus,selection_flags,pending_notify;
static unsigned actual_methods;
static char *text_field(unsigned h){switch(h){case 0x3a:return field;case 0x2c:return addrfield;case 0x74:return namefield;case 0x82:return rangefield;default:return 0;}}
static int switch_directory(const char *p){char rel[110];unsigned i=0,j=0;while(p[i]=='\\'||p[i]=='/')i++;for(;p[i]&&j<104;i++){char c=p[i];if(c==':'||c<32)return -1;rel[j++]=c=='\\'?'/':c;}rel[j]=0;if(strstr(rel,".."))return -1;int fd=openat(dirfd,j?rel:".",O_RDONLY|O_DIRECTORY);if(fd<0)return -1;close(currentfd);currentfd=fd;snprintf(current_path,sizeof current_path,"%s",p);return 0;}
static unsigned long polls,kcalls,draws,upper_scrambles,files_written;
static unsigned min_private_sp=65535,close_handle;
static int cpu_bad,fail_write=-1,fail_rename=-1,renames,writecalls;
static int corrupt_state,fail_alloc;
static unsigned short getds(void){unsigned short s;__asm__ volatile("mov %%ds,%0":"=r"(s));return s;}
static unsigned short getes(void){unsigned short s;__asm__ volatile("mov %%es,%0":"=r"(s));return s;}
static unsigned short w16(const void*p){unsigned short v;memcpy(&v,p,2);return v;}
static void s16(void*p,unsigned v){unsigned short s=v;memcpy(p,&s,2);}
static void set16(greg_t*g,int r,unsigned v){g[r]=(g[r]&~65535LL)|(v&65535);}
static unsigned ssreg(ucontext_t*u){return (u->uc_mcontext.gregs[REG_CSGSFS]>>48)&65535;}
static uint8_t*base(unsigned sel){switch(sel){case 15:return code;case 23:return dg;case 31:return engine;case 39:return nstack;case 47:return kernel;case 55:return temp;case 63:return state;}return 0;}
static void fail(ucontext_t*u,const char*why){char b[700];greg_t*g=u->uc_mcontext.gregs;unsigned cs=g[REG_CSGSFS]&65535,ip=g[REG_RIP]&65535;uint8_t*c=base(cs);int n=snprintf(b,sizeof b,"FAIL %s cs=%x ip=%x ss=%x ds=%x es=%x ax=%llx bx=%llx cx=%llx dx=%llx si=%llx di=%llx bp=%llx sp=%llx bytes=%02x %02x %02x %02x step=%d\n",why,cs,ip,ssreg(u),getds(),getes(),(long long)g[REG_RAX],(long long)g[REG_RBX],(long long)g[REG_RCX],(long long)g[REG_RDX],(long long)g[REG_RSI],(long long)g[REG_RDI],(long long)g[REG_RBP],(long long)g[REG_RSP],c?c[ip]:0,c?c[(ip+1)&65535]:0,c?c[(ip+2)&65535]:0,c?c[(ip+3)&65535]:0,script_pos);write(2,b,n);_exit(91);}
static int path_ok(const char*p){int n=0;while(*p){if(*p=='/'||*p=='\\'||*p==':'||*p<32)return 0;if(++n>20)return 0;p++;}return n>0;}
static int geos_error(int e){return e==ENOENT?2:e==EEXIST?130:e==ENOSPC?39:e==EACCES?5:31;}
static void log_state(void){char b[256];int count;memcpy(&count,engine+book_at+19456,4);int ch;memcpy(&ch,engine+changed_at,4);int n=snprintf(b,sizeof b,"STATE step=%d cells=%d changed=%d\n",script_pos,count,ch);write(logfd,b,n);for(int i=0;i<count&&i<256;i++){unsigned off=book_at+76*i;int val;memcpy(&val,engine+off+4,4);n=snprintf(b,sizeof b,"CELL %c%u value=%d error=%u kind=%u input=%s\n",'A'+engine[off+2],w16(engine+off)+1,val,engine[off+8],engine[off+9],engine+off+10);write(logfd,b,n);}}
static void finish(void){if(dir_depth){write(2,"directory stack leak\n",21);_exit(92);}log_state();char b[400];int n=snprintf(b,sizeof b,"OK driver_steps=%d native_methods=%u kernel_calls=%lu polling_windows=%lu upper_register_scrambles=%lu min_private_sp=%u engine_used=%u draw_calls=%lu write_calls=%d rename_calls=%d files_written=%lu\n",script_pos,actual_methods,kcalls,polls,upper_scrambles,min_private_sp,engine_used,draws,writecalls,renames,files_written);write(1,b,n);write(logfd,b,n);int f=openat(dirfd,"ENGINE.BIN",O_CREAT|O_TRUNC|O_WRONLY,0600);write(f,engine,65536);close(f);_exit(0);}
static void next_action(ucontext_t*u){greg_t*g=u->uc_mcontext.gregs;unsigned at,msg=0,bp=0,cx=0x1234,dx=0;char*l;int action;
 if(previous==2){close_handle=g[REG_RCX]&65535;char b[64];int n=snprintf(b,sizeof b,"CLOSED handle=%u\n",close_handle);write(logfd,b,n);}
 if(script_pos)log_state();
 if(pending_notify){pending_notify=0;l="[selector activation]";at=native_command_at;msg=0xc15;bp=0x2000;previous=1;goto dispatch;}
 if(script_pos>=script_count)finish();
 l=lines[script_pos++];
 if(!strcmp(l,"START")){at=native_open_at;msg=0xa01;previous=0;}
 else if(!strcmp(l,"RESTORE")){if(corrupt_state)state[28]^=1;memcpy(engine,initial_engine,65536);memset(dg+0x180,0,8);at=native_open_at;msg=0xa01;bp=close_handle;previous=0;}
 else if(!strcmp(l,"CLOSE")){at=native_close_at;msg=0xa03;previous=2;}
 else if(!strcmp(l,"EXPOSE")){at=native_expose_at;msg=0x49;previous=3;}
 else if(sscanf(l,"KEY %x %x",&cx,&dx)==2){at=native_key_at;msg=0x7b;previous=1;}
 else if(sscanf(l,"DBLCLICK %u %u",&cx,&dx)==2){at=native_select_at;msg=0xc3;bp=0x40;previous=1;}
 else if(!strcmp(l,"HELP_CLOSED")){help_open=0;at=native_command_at;msg=0xc15;previous=1;} /* driver models the help control closing itself */
 else if(sscanf(l,"CLICK %u %u",&cx,&dx)==2){at=native_select_at;msg=0xc3;previous=1;}
 else if(!strncmp(l,"FILE ",5)||!strncmp(l,"SEL ",4)){
   int active=l[0]=='F';snprintf(selection,sizeof selection,"%s",l+(active?5:4));selection_flags=0;
   if(strchr(selection,'\\'))selection_flags=0x4000;
   at=native_command_at;msg=dialog==0x70?0xc19:0xc15;bp=selection_flags|(active?0x2000:0);previous=1;
 }
 else if(!strncmp(l,"BROWSE ",7)){
   int i=dialog==0x70?1:0;snprintf(browser[i],104,"%s",l+7);selection[0]=0;selection_flags=0x4000;
   at=native_command_at;msg=dialog==0x70?0xc19:0xc15;bp=0x4000;previous=1;
 }
 else if(sscanf(l,"DO %d",&action)==1&&action>=1&&action<=29){
   char*p=strchr(l+3,' '),*dst=action==15?addrfield:action==20?namefield:action==18?rangefield:field;
   if(p&&(action==1||action==15||action==18||action==20)){unsigned cap=action==15?16:128;snprintf(dst,cap,"%s",p+1);}
   at=native_command_at;msg=0xc00+action;previous=1;
 }
 else if(!strncmp(l,"TYPE ",5)){snprintf(field,sizeof field,"%s",l+5);at=native_command_at;msg=0xc15;bp=0;previous=1;}
 else fail(u,"invalid driver script");
 dispatch:
 actual_methods++;s16(code+0xe802,at);s16(code+0xe804,15);
 set16(g,REG_RAX,msg);set16(g,REG_RBX,0);set16(g,REG_RCX,cx);set16(g,REG_RDX,dx);set16(g,REG_RSI,0);set16(g,REG_RDI,0);set16(g,REG_RBP,bp);
 char b[320];int n=snprintf(b,sizeof b,"ACTION %d %s\n",script_pos,l);write(logfd,b,n);
}
static void trap(int sig,siginfo_t*info,void*context){ucontext_t*u=context;greg_t*g=u->uc_mcontext.gregs;unsigned cs=g[REG_CSGSFS]&65535,ip=g[REG_RIP]&65535,ss=ssreg(u);uint8_t*c=base(cs);unsigned bp=g[REG_RBP]&65535,ax=g[REG_RAX]&65535,bx=g[REG_RBX]&65535,cx=g[REG_RCX]&65535,dx=g[REG_RDX]&65535,si=g[REG_RSI]&65535,di=g[REG_RDI]&65535;int r=0,e=0,ordinal;uint8_t*ds=base(getds()),*es=base(getes());char b[512];(void)sig;(void)info;
 if(!c)fail(u,"unknown CS");
 if(ss==31){unsigned sp=g[REG_RSP]&65535;if(sp<min_private_sp)min_private_sp=sp;if(sp<engine_used+64)fail(u,"private stack guard");}
 if(cs==15&&(c[ip]==0xfa||c[ip]==0xfb)){
  if(c[ip]==0xfb){if(ss!=39)fail(u,"interrupts enabled on non-native stack");if((g[REG_RSP]&65535)<0xe000)fail(u,"native stack bounds");polls++;unsigned savedsp;memcpy(&savedsp,engine+10,4);if(savedsp<min_private_sp)min_private_sp=savedsp;if(savedsp<engine_used+64||savedsp>65504)fail(u,"recorded private stack guard");int regs[]={REG_RAX,REG_RBX,REG_RCX,REG_RDX,REG_RSI,REG_RDI,REG_RBP};for(unsigned i=0;i<sizeof(regs)/sizeof(regs[0]);i++)g[regs[i]]=(g[regs[i]]&65535)|0xabcd0000U;upper_scrambles++;}
  g[REG_RIP]++;return;
 }
 if(c[ip]!=0xcd)fail(u,"unexpected instruction fault");
 if(cs==15&&c[ip+1]==0xf1){next_action(u);g[REG_RIP]+=2;return;}
 if(cs!=47||c[ip+1]!=0xf0||ip%4)fail(u,"unexpected trap");
 if(ss!=39)fail(u,"GEOS call on private stack");
 ordinal=ip/4;kcalls++;
 switch(ordinal){
 case 489:{int n=snprintf(b,sizeof b,"SUPER msg=%x cx=%x dx=%x\n",ax,cx,dx);write(logfd,b,n);break;}
 case 0:if(ax!=engine_used||cx!=0x6050)fail(u,"MemAlloc contract");if(fail_alloc){g[REG_EFL]|=1;break;}memset(state,0,65536);set16(g,REG_RAX,63);set16(g,REG_RBX,0x2001);g[REG_EFL]&=~1LL;break;
 case 5:if(bx==0x2000)set16(g,REG_RAX,55);else if(bx==0x2001)set16(g,REG_RAX,63);else fail(u,"MemLock handle");break;
 case 2:case 6:break;
 case 150:if(bx!=3)fail(u,"resource handle request");set16(g,REG_RBX,0x3003);break;
 case 169:{
  if(bx!=0x3003||di!=0x8000)fail(u,"native ObjMessage destination/flags");
  char *f=text_field(si);int bi=si==0x72?1:0;
  if(ax==0x2204){if(!f||cx!=31||dx+strlen(f)+1>65536)fail(u,"native GenText get contract");if(*f)strcpy((char*)engine+dx,f);set16(g,REG_RAX,0);set16(g,REG_RCX,strlen(f));}
  else if(ax==0x2200){if(dx!=31||cx||bp>65375)fail(u,"native text replacement contract");const char*t=(char*)engine+bp;
   if(f){size_t cap=si==0x2c?16:128;if(strlen(t)>=cap)fail(u,"UI text overflow");strcpy(f,t);}
   else if(si!=0x64&&si!=0x76&&si!=0x84)fail(u,"unknown display field");
   int n=snprintf(b,sizeof b,"FIELD %x %s\n",si,t);write(logfd,b,n);
  }
  else if(ax==0x418c){if(!f&&si!=0x3e)fail(u,"focus object");focus=si;int n=snprintf(b,sizeof b,"FOCUS %x\n",si);write(logfd,b,n);}
  else if(ax==0x7b){if(!f||cx!=0xff94||dx!=0x0804||bp||focus!=(int)si)fail(u,"native single-line Shift+Home contract");int n=snprintf(b,sizeof b,"SELECT_TEXT %x\n",si);write(logfd,b,n);}
  else if(ax==0x4197&&si==0xa0){help_open=1;write(logfd,"HELP_OPEN a0\n",13);}
  else if(ax==0x4197){if(si!=0x60&&si!=0x70&&si!=0x80&&si!=0x90)fail(u,"unknown dialog");if(dialog)fail(u,"overlapping modal dialogs");dialog=si;int n=snprintf(b,sizeof b,"DIALOG_OPEN %x\n",si);write(logfd,b,n);}
  else if(ax==0x419b){if(dialog!=(int)si)fail(u,"dismissing wrong dialog");dialog=0;int n=snprintf(b,sizeof b,"DIALOG_CLOSE %x\n",si);write(logfd,b,n);}
  else if(ax==0x4203){if(si!=0x62&&si!=0x72)fail(u,"path init destination");if(cx!=31||bp!=0x1001||dx>65432)fail(u,"file-selector SET_PATH contract");snprintf(browser[bi],104,"%s",engine+dx);selection[0]=0;selection_flags=0;}
  else if(ax==0x4202){if((si!=0x62&&si!=0x72)||cx!=31||dx>65432)fail(u,"file-selector GET_PATH contract");strcpy((char*)engine+dx,browser[bi]);set16(g,REG_RBP,0x1001);}
  else if(ax==0x4200){if(si!=0x62&&si!=0x72)fail(u,"file-selector GET_SELECTION destination");if(cx){if(cx!=31||dx>65500)fail(u,"selection copy contract");strcpy((char*)engine+dx,selection);}set16(g,REG_RBP,selection_flags);}
  else if(ax==0x421a){if(si!=0x62)fail(u,"activate selector");if(!(selection_flags&0xc000)&&selection[0])pending_notify=1;int n=snprintf(b,sizeof b,"SELECTOR_ACTIVATE %s flags=%x\n",selection,selection_flags);write(logfd,b,n);}
  else { fail(u,"unmodeled native object message"); }
  break;
 }
 case 73:if(dir_depth>=16)fail(u,"directory push overflow");dir_stack[dir_depth]=dup(currentfd);strcpy(path_stack[dir_depth++],current_path);break;
 case 74:if(!dir_depth)fail(u,"directory pop underflow");close(currentfd);currentfd=dir_stack[--dir_depth];strcpy(current_path,path_stack[dir_depth]);break;
 case 75:if(!ds||si+cx>65536||cx<104)fail(u,"get current path contract");strcpy((char*)ds+si,current_path);set16(g,REG_RBX,0x1001);g[REG_EFL]&=~1LL;break;
 case 51:if(!ds||bx!=0x1001||dx>65432)fail(u,"set current path contract");if(getenv("FAIL_SET_DIRECTORY")||switch_directory((char*)ds+dx)<0){set16(g,REG_RAX,3);g[REG_EFL]|=1;}else g[REG_EFL]&=~1LL;break;
 case 76:if(ax!=5)fail(u,"standard path");if(getenv("FAIL_DOCUMENT_PATH"))g[REG_EFL]|=1;else{switch_directory("\\");g[REG_EFL]&=~1LL;}break;
 case 211:set16(g,REG_RDI,0x1111);break;
 case 212:case 446:case 447:case 362:break;
 case 366:if(cx!=0x1a00||dx!=10||(ax>>8))fail(u,"worksheet font is not native URW Mono 10");break;
 case 355:case 359:{int n=snprintf(b,sizeof b,"COLOR %d %u\n",ordinal,ax);write(logfd,b,n);break;}
 case 336:{int n=snprintf(b,sizeof b,"RECT %u %u %u %u\n",ax,bx,cx,dx);write(logfd,b,n);draws++;break;}
 case 330:if(!ds||si>65472)fail(u,"text bounds");{int n=snprintf(b,sizeof b,"TEXT %u %u %.80s\n",ax,bx,ds+si);write(logfd,b,n);draws++;break;}
 case 52:case 53:if(!ds||!path_ok((char*)ds+dx))fail(u,"unsafe file path");if((ordinal==52&&ax!=0xc0)||(ordinal==53&&(ax!=0x2c1||cx)))fail(u,"file access flags");r=openat(currentfd,(char*)ds+dx,ordinal==52?O_RDONLY:O_WRONLY|O_CREAT|O_EXCL,0600);if(ordinal==53&&r>=0)files_written++;goto file_return;
 case 54:r=close(bx);goto file_return;
 case 56:if(!ds||!path_ok((char*)ds+dx))fail(u,"unsafe delete");r=unlinkat(currentfd,(char*)ds+dx,0);goto file_return;
 case 57:if(!ds||!es||!path_ok((char*)ds+dx)||!path_ok((char*)es+di))fail(u,"unsafe rename");if(renames++==fail_rename){errno=EACCES;r=-1;}else r=renameat2(currentfd,(char*)ds+dx,currentfd,(char*)es+di,RENAME_NOREPLACE);goto file_return;
 case 58:case 59:if(!ds||dx+cx>65536||(ax&255))fail(u,"read/write contract");if(ordinal==58&&getenv("HIGH_READ_ERROR")){set16(g,REG_RAX,131);g[REG_EFL]|=1;break;}if(ordinal==59&&getenv("HIGH_WRITE_ERROR")){set16(g,REG_RAX,131);g[REG_EFL]|=1;break;}if(ordinal==58)r=read(bx,ds+dx,cx);else if(writecalls++==fail_write){errno=ENOSPC;r=-1;}else r=write(bx,ds+dx,cx);if(r<0)goto file_return;set16(g,REG_RCX,r);if(r<(int)cx){set16(g,REG_RAX,128);g[REG_EFL]|=1;}else g[REG_EFL]&=~1LL;break;
 default:fail(u,"unmodeled GEOS ordinal");
 }
 g[REG_RIP]+=2;return;
file_return:
 if(r<0){e=geos_error(errno);set16(g,REG_RAX,e);g[REG_EFL]|=1;}else{set16(g,REG_RAX,r);g[REG_EFL]&=~1LL;}g[REG_RIP]+=2;
}
static uint8_t*segment(int index,int exec){struct user_desc d={0};uint8_t*p=mmap(0,65536,PROT_READ|PROT_WRITE|PROT_EXEC,MAP_PRIVATE|MAP_ANONYMOUS|MAP_32BIT,-1,0);if(p==MAP_FAILED){perror("mmap");exit(1);}d.entry_number=index;d.base_addr=(unsigned long)p;d.limit=65535;d.seg_32bit=0;d.contents=exec?2:0;d.read_exec_only=0;d.limit_in_pages=0;d.seg_not_present=0;d.useable=1;if(syscall(SYS_modify_ldt,1,&d,sizeof d)<0){perror("modify_ldt");exit(1);}return p;}
static void load(const char*p,uint8_t*out){FILE*f=fopen(p,"rb");if(!f){perror(p);exit(1);}if(fread(out,1,65536,f)==0)exit(1);fclose(f);}
int main(int argc,char**argv){FILE*f;char line[256],name[100];unsigned a;struct sigaction sa={0};stack_t stack={0};
 if(argc!=8){fprintf(stderr,"runner RELOCATED_CODE ENGINE DGROUP SYMBOLS WORKDIR SCRIPT TRACE\n");return 1;}
 code=segment(1,1);dg=segment(2,0);engine=segment(3,0);nstack=segment(4,0);kernel=segment(5,1);temp=segment(6,0);state=segment(7,0);initial_engine=malloc(65536);
 load(argv[1],code);load(argv[2],engine);load(argv[3],dg);memcpy(initial_engine,engine,65536);memset(nstack,0x5a,64);
 f=fopen(argv[4],"r");if(!f)return 1;while(fgets(line,sizeof line,f)){char type;if(sscanf(line,"%x %c %99s",&a,&type,name)==3){if(!strcmp(name,"native_open"))native_open_at=a;if(!strcmp(name,"native_command"))native_command_at=a;if(!strcmp(name,"native_select"))native_select_at=a;if(!strcmp(name,"native_key"))native_key_at=a;if(!strcmp(name,"native_close"))native_close_at=a;if(!strcmp(name,"native_expose"))native_expose_at=a;if(!strcmp(name,"cpu_probe"))probe_at=a;if(!strcmp(name,"__engine_used"))engine_used=a;if(!strcmp(name,"entry"))entry_at=a;if(!strcmp(name,"book"))book_at=a;if(!strcmp(name,"drawing_count"))count_at=a;if(!strcmp(name,"changed"))changed_at=a;}}fclose(f);
 if(getenv("BAD_CPU"))cpu_bad=1;
 if(getenv("CORRUPT_STATE"))corrupt_state=1;
 if(getenv("FAIL_ALLOC"))fail_alloc=1;
 if(getenv("FAIL_WRITE"))fail_write=atoi(getenv("FAIL_WRITE"));
 if(getenv("FAIL_RENAME"))fail_rename=atoi(getenv("FAIL_RENAME"));
 code[probe_at]=cpu_bad?0xf9:0xf8;code[probe_at+1]=0xc3;
 for(int i=0;i<512;i++){kernel[i*4]=0xcd;kernel[i*4+1]=0xf0;kernel[i*4+2]=0xcb;kernel[i*4+3]=0x90;}
 /* Driver starts on the native thread stack. Per-event stub restores DS/ES
    before a true far call to the public GEOS method, then returns to driver. */
 uint8_t start[]={0xb8,39,0,0x8e,0xd0,0x66,0xbc,0xf0,0xef,0,0,0xe9,0,0};s16(start+12,0xe7f0-(0xe700+sizeof start));memcpy(code+0xe700,start,sizeof start);
 uint8_t driver[]={0xb8,23,0,0x8e,0xd8,0x8e,0xc0,0xcd,0xf1,0xe9,0,0};s16(driver+10,0xe801-(0xe7f0+sizeof driver));memcpy(code+0xe7f0,driver,sizeof driver);
 code[0xe801]=0x9a;s16(code+0xe802,0);s16(code+0xe804,15);code[0xe806]=0xe9;s16(code+0xe807,0xe7f0-0xe809);
 f=fopen(argv[6],"r");if(!f)return 1;while(fgets(line,sizeof line,f)&&script_count<512){line[strcspn(line,"\r\n")]=0;if(*line&&*line!='#')strcpy(lines[script_count++],line);}fclose(f);
 dirfd=open(argv[5],O_DIRECTORY|O_RDONLY);logfd=open(argv[7],O_CREAT|O_TRUNC|O_WRONLY,0600);if(dirfd<0||logfd<0)return 1;currentfd=dup(dirfd);
 stack.ss_sp=mmap(0,1<<20,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);stack.ss_size=1<<20;if(sigaltstack(&stack,0)<0)return 1;sa.sa_sigaction=trap;sa.sa_flags=SA_SIGINFO|SA_ONSTACK;sigemptyset(&sa.sa_mask);sigaction(SIGSEGV,&sa,0);sigaction(SIGILL,&sa,0);sigaction(SIGBUS,&sa,0);alarm(35);fflush(0);
 __asm__ volatile("pushq $15;pushq $0xe700;lretq":::"memory");return 99;
}
