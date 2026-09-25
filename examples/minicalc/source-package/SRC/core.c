#include "calc.h"
Sheet book,staging;
int changed,undo_ready;
char message[160];
static int eval_depth,parse_depth;
static u32 operations;
static const char *errnames[]={"","#SYNTAX!","#DIV/0!","#VALUE!","#REF!","#NAME?","#CYCLE!","#NUM!","#DEPTH!","#PREC!","#LIMIT!"};
void *m_copy(void *d,const void *s,unsigned n){u8 *a=d;const u8 *b=s;while(n--)*a++=*b++;return d;}
void *m_zero(void *d,unsigned n){u8 *a=d;while(n--)*a++=0;return d;}
unsigned s_len(const char*s){unsigned n=0;while(s[n])n++;return n;}
int s_eq(const char*a,const char*b){while(*a && *a==*b){a++;b++;}return *a==*b;}
void s_copy(char*d,const char*s,unsigned cap){if(!cap)return;while(--cap && *s)*d++=*s++;*d=0;}
int ascii_upper(int c){return c>='a' && c<='z'?c-32:c;}
int digit(int c){return c>='0'&&c<='9';}
const char *error_name(int e){return e>=0&&e<=E_LIMIT?errnames[e]:"#ERROR!";}
static void spaces(const char **p){while(**p==' ')(*p)++;}
static int reference(const char **p,int *row,int *col,int *ar,int *ac){
 const char *s=*p;int r=0,c;
 *ar=*ac=0;if(*s=='$'){*ac=1;s++;}
 c=ascii_upper(*s)-'A';if(c<0||c>=COL_LIMIT)return 0;s++;
 if(*s=='$'){*ar=1;s++;}if(!digit(*s))return 0;
 while(digit(*s)){r=r*10+(*s++-'0');if(r>ROW_LIMIT)return 0;}
 if(r<1)return 0;*row=r-1;*col=c;*p=s;return 1;
}
int address(const char*s,int*row,int*col){int ar,ac;spaces(&s);if(!reference(&s,row,col,&ar,&ac))return 0;spaces(&s);return !*s;}
static char *unsigned_text(u32 v,char *out){char t[12];int n=0;do{t[n++]=(char)('0'+v%10);v/=10;}while(v);while(n)*out++=t[--n];*out=0;return out;}
void cell_name(int row,int col,char*out){*out++=(char)('A'+col);unsigned_text((u32)row+1,out);}
void format_number(i32 v,char*out){u32 n;char *p;int f,i;if(v<0){*out++='-';n=(u32)(-(i64)v);}else n=(u32)v;p=unsigned_text(n/SCALE,out);f=n%SCALE;if(f){*p++='.';for(i=1000;i;i/=10)*p++=(char)('0'+f/i%10);while(p[-1]=='0')p--;*p=0;}}
/* Exact decimal input, maximum four nonzero fractional places. No hidden
   rounding of input literals. Multiplication/division round to four places. */
static i32 decimal(const char **p,int *error){const char*s=*p;u32 whole=0,frac=0;int digs=0,fd=0,bad=0;
 while(digit(*s)){digs++;if(whole>214748U || (whole==214748U && *s>'3'))bad=E_NUM; if(!bad)whole=whole*10+(*s-'0');s++;}
 if(*s=='.'){s++;while(digit(*s)){digs++;if(fd<4){frac=frac*10+(*s-'0');fd++;}else if(*s!='0'&&!bad)bad=E_PREC;s++;}}
 if(!digs)bad=E_SYNTAX;
 while(fd<4){frac*=10;fd++;}
 if(!bad && (whole>214748U || (whole==214748U && frac>3647U)))bad=E_NUM;
 *p=s;if(bad){*error=bad;return 0;}return (i32)(whole*SCALE+frac);
}
int parse_number(const char*s,i32*value){int sign=1,e=0;spaces(&s);if(*s=='-'||*s=='+'){if(*s=='-')sign=-1;s++;}if(!digit(*s)&&*s!='.')return E_VALUE;
 *value=decimal(&s,&e);spaces(&s);if(*s)return E_VALUE;if(e)return e;*value*=sign;return 0;}
int find_cell(const Sheet*s,int row,int col){int i;for(i=0;i<s->count;i++)if(s->cells[i].row==row&&s->cells[i].col==col)return i;return -1;}
int put_cell(Sheet*s,int row,int col,const char*input){int i,j;unsigned n=s_len(input);
 if(row<0||row>=ROW_LIMIT||col<0||col>=COL_LIMIT){s_copy(message,"Cell address is outside A1:Z999.",160);return 0;}
 if(n>INPUT_LIMIT){s_copy(message,"Cell input is longer than 63 characters; nothing was changed.",160);return 0;}
 for(j=0;j<(int)n;j++)if((u8)input[j]<32||(u8)input[j]>126){s_copy(message,"This version accepts printable ASCII cell text only.",160);return 0;}
 i=find_cell(s,row,col);if(!n){if(i>=0){s->cells[i]=s->cells[--s->count];}return 1;}
 if(i<0){if(s->count==CELL_LIMIT){s_copy(message,"The 256 populated-cell limit was reached; nothing was changed.",160);return 0;}i=s->count++;}
 m_zero(&s->cells[i],sizeof(Cell));s->cells[i].row=(u16)row;s->cells[i].col=(u8)col;s_copy(s->cells[i].input,input,INPUT_LIMIT+1);return 1;
}
int edit_cell(int row,int col,const char*input){m_copy(&staging,&book,sizeof(Sheet));if(!put_cell(&book,row,col,input)){undo_ready=0;return 0;}changed=undo_ready=1;recalculate();message[0]=0;return 1;}
void new_book(void){m_zero(&book,sizeof(Sheet));m_zero(&staging,sizeof(Sheet));changed=undo_ready=0;message[0]=0;reset_session();}

typedef struct{const char *p;int error;} Parser;
static i32 expression(Parser*p);
static i32 evaluate_cell(int index);
static i32 checked(i64 x,Parser*p){if(x>NUM_LIMIT||x<-(i64)NUM_LIMIT){p->error=E_NUM;return 0;}return (i32)x;}
static i32 rounded(i64 n,i64 d,Parser*p){int neg;u64 a,b,q;if(!d){p->error=E_DIVZERO;return 0;}neg=(n<0)!=(d<0);a=n<0?(u64)(-n):(u64)n;b=d<0?(u64)(-d):(u64)d;q=(a+b/2)/b;if(q>NUM_LIMIT){p->error=E_NUM;return 0;}return neg?-(i32)q:(i32)q;}
static int consume(Parser*p,int c){spaces(&p->p);if(*p->p==c){p->p++;return 1;}return 0;}
static i32 ref_value(int r,int c,Parser*p,int ignore_text,int *numeric){int i=find_cell(&book,r,c);i32 v;*numeric=0;if(i<0)return 0;v=evaluate_cell(i);if(book.cells[i].error){p->error=book.cells[i].error;return 0;}
 if(book.cells[i].kind==K_TEXT){if(!ignore_text)p->error=E_VALUE;return 0;}*numeric=1;return v;}
static void accumulate(i32 v,int fn,i64 *sum,i32*best,int*count){if(!*count|| (fn==2&&v<*best)||(fn==3&&v>*best))*best=v;*sum+=v;(*count)++;}
static i32 function(Parser*p,const char *name){int fn=-1,r,c,r2,c2,ar,ac,n=0,numeric,range,rr,cc,argn=0;const char *save; i32 v,best=0,args[2]={0,0};i64 sum=0;
 if(s_eq(name,"SUM"))fn=0;else if(s_eq(name,"AVERAGE"))fn=1;else if(s_eq(name,"MIN"))fn=2;else if(s_eq(name,"MAX"))fn=3;else if(s_eq(name,"COUNT"))fn=4;else if(s_eq(name,"ABS"))fn=5;else if(s_eq(name,"ROUND"))fn=6;
 if(fn<0){p->error=E_NAME;return 0;}if(!consume(p,'(')){p->error=E_SYNTAX;return 0;}
 if(consume(p,')')){if(fn==1)p->error=E_DIVZERO;else if(fn>=5)p->error=E_SYNTAX;return 0;}
 do{spaces(&p->p);save=p->p;range=0;
  if(fn<5 && reference(&p->p,&r,&c,&ar,&ac)){
   spaces(&p->p);if(consume(p,':')){spaces(&p->p);if(!reference(&p->p,&r2,&c2,&ar,&ac)){p->error=E_REF;return 0;}range=1;}
   else{r2=r;c2=c;spaces(&p->p);if(*p->p==','||*p->p==')')range=1;}
  }
  if(range){if(r2<r){rr=r;r=r2;r2=rr;}if(c2<c){cc=c;c=c2;c2=cc;}
   for(rr=r;rr<=r2&&!p->error;rr++)for(cc=c;cc<=c2&&!p->error;cc++){
    if(++operations>1000000U){p->error=E_LIMIT;break;}v=ref_value(rr,cc,p,1,&numeric);if(numeric)accumulate(v,fn,&sum,&best,&n);
   }
  }else{p->p=save;v=expression(p);if(fn>=5){if(argn>=2){p->error=E_SYNTAX;return 0;}args[argn++]=v;}else accumulate(v,fn,&sum,&best,&n);}
  if(p->error)return 0;
 }while(consume(p,','));
 if(!consume(p,')')){p->error=E_SYNTAX;return 0;}
 if(fn==0)return checked(sum,p);if(fn==1){if(!n){p->error=E_DIVZERO;return 0;}return rounded(sum,n,p);}if(fn==2||fn==3)return n?best:0;if(fn==4)return checked((i64)n*SCALE,p);
 if(fn==5){if(argn!=1){p->error=E_SYNTAX;return 0;}return args[0]<0?-args[0]:args[0];}
 if(argn!=2||args[1]%SCALE||args[1]<-4*SCALE||args[1]>4*SCALE){p->error=E_VALUE;return 0;}
 {i64 factor=1;int places=4-args[1]/SCALE;while(places--)factor*=10;v=rounded(args[0],factor,p);return checked((i64)v*factor,p);}
}
static i32 primary(Parser*p){i32 v=0;int r,c,ar,ac,numeric,len=0;char name[12];const char*s;
 if(p->error)return 0;if(++parse_depth>24){p->error=E_DEPTH;parse_depth--;return 0;}if(++operations>1000000U){p->error=E_LIMIT;goto done;}spaces(&p->p);
 if(consume(p,'(')){v=expression(p);if(!p->error&&!consume(p,')'))p->error=E_SYNTAX;goto done;}
 if(digit(*p->p)||*p->p=='.'){v=decimal(&p->p,&p->error);goto done;}
 if(*p->p=='#'){p->error=E_REF;goto done;}
 s=p->p;if(reference(&p->p,&r,&c,&ar,&ac)){v=ref_value(r,c,p,0,&numeric);goto done;}p->p=s;
 while(ascii_upper(*p->p)>='A'&&ascii_upper(*p->p)<='Z'){if(len<11)name[len++]=(char)ascii_upper(*p->p);p->p++;}name[len]=0;
 if(len)v=function(p,name);else p->error=E_SYNTAX;
 done:parse_depth--;return v;
}
static i32 unary(Parser*p){int neg=0,n=0;i32 v;spaces(&p->p);while(*p->p=='+'||*p->p=='-'){if(*p->p++=='-')neg=!neg;spaces(&p->p);if(++n>INPUT_LIMIT){p->error=E_DEPTH;return 0;}}v=primary(p);if(consume(p,'%'))v=rounded(v,100,p);return neg?-v:v;}
static i32 term(Parser*p){i32 a=unary(p),b;int op;while(!p->error){spaces(&p->p);op=*p->p;if(op!='*'&&op!='/')break;p->p++;b=unary(p);if(p->error)break;a=op=='*'?rounded((i64)a*b,SCALE,p):rounded((i64)a*SCALE,b,p);}return a;}
static i32 expression(Parser*p){i32 a=term(p),b;int op;while(!p->error){spaces(&p->p);op=*p->p;if(op!='+'&&op!='-')break;p->p++;b=term(p);if(p->error)break;a=checked(op=='+'?(i64)a+b:(i64)a-b,p);}return a;}
static i32 evaluate_cell(int index){Cell*c=&book.cells[index];Parser p;int e; i32 v=0;
 if(c->state==2)return c->value;if(c->state==1){c->error=E_CYCLE;return 0;}if(eval_depth>=24){c->error=E_DEPTH;c->state=2;return 0;}
 c->state=1;c->kind=K_NUMBER;c->error=0;eval_depth++;
 if(c->input[0]=='='){p.p=c->input+1;p.error=0;v=expression(&p);spaces(&p.p);if(!p.error&&*p.p)p.error=E_SYNTAX;c->error=(u8)p.error;}
 else if(c->input[0]=='\''){c->kind=K_TEXT;}
 else{e=parse_number(c->input,&v);if(e==E_VALUE)c->kind=K_TEXT;else c->error=(u8)e;}
 c->value=c->error?0:v;c->state=2;eval_depth--;return c->value;
}
void recalculate(void){int i;eval_depth=parse_depth=0;operations=0;for(i=0;i<book.count;i++){book.cells[i].state=0;book.cells[i].error=0;}for(i=0;i<book.count;i++)evaluate_cell(i);}
void cell_display(int row,int col,char*out,unsigned cap){int i=find_cell(&book,row,col);char buf[28];if(i<0){if(cap)*out=0;return;}if(book.cells[i].error)s_copy(out,error_name(book.cells[i].error),cap);else if(book.cells[i].kind==K_TEXT)s_copy(out,book.cells[i].input+(book.cells[i].input[0]=='\''),cap);else {format_number(book.cells[i].value,buf);s_copy(out,buf,cap);}}
static int translate(const char *src,int dr,int dc,char*out){const char*p=src,*save;int r,c,ar,ac,n=0,j;char temp[16];
 if(*src!='='){s_copy(out,src,INPUT_LIMIT+1);return 1;}
 while(*p){save=p;if(reference(&p,&r,&c,&ar,&ac)){if(!ar)r+=dr;if(!ac)c+=dc;j=0;if(r<0||r>=ROW_LIMIT||c<0||c>=COL_LIMIT)s_copy(temp,"#REF!",16);else{if(ac)temp[j++]='$';temp[j++]=(char)('A'+c);if(ar)temp[j++]='$';unsigned_text((u32)r+1,temp+j);}for(j=0;temp[j];j++){if(n==INPUT_LIMIT)return 0;out[n++]=temp[j];}}
 else{p=save;if(n==INPUT_LIMIT)return 0;out[n++]=*p++;}}
 out[n]=0;return 1;
}
int copy_range(int sr,int sc,const char*dest){int r,c,r2,c2,ar,ac,rr,cc,i;char source[INPUT_LIMIT+1],input[INPUT_LIMIT+1];spaces(&dest);if(!reference(&dest,&r,&c,&ar,&ac))goto bad;spaces(&dest);if(*dest==':'){dest++;spaces(&dest);if(!reference(&dest,&r2,&c2,&ar,&ac))goto bad;}else{r2=r;c2=c;}spaces(&dest);if(*dest||r2<r||c2<c)goto bad;
 i=find_cell(&book,sr,sc);source[0]=0;if(i>=0)s_copy(source,book.cells[i].input,sizeof(source));m_copy(&staging,&book,sizeof(Sheet));
 for(rr=r;rr<=r2;rr++)for(cc=c;cc<=c2;cc++){if(!translate(source,rr-sr,cc-sc,input)){s_copy(message,"Adjusted formula exceeds 63 characters; copy cancelled.",160);undo_ready=0;return 0;}if(!put_cell(&staging,rr,cc,input)){undo_ready=0;return 0;}}
 {Cell temp;int k,count=book.count;for(k=0;k<CELL_LIMIT;k++){temp=book.cells[k];book.cells[k]=staging.cells[k];staging.cells[k]=temp;}book.count=staging.count;staging.count=count;}
 changed=undo_ready=1;recalculate();message[0]=0;return 1;
 bad:s_copy(message,"Use a destination such as B2 or B2:D8.",160);return 0;
}
int undo_book(void){Cell temp;int k,n;if(!undo_ready){s_copy(message,"There is no edit to undo.",160);return 0;}for(k=0;k<CELL_LIMIT;k++){temp=book.cells[k];book.cells[k]=staging.cells[k];staging.cells[k]=temp;}n=book.count;book.count=staging.count;staging.count=n;changed=1;recalculate();message[0]=0;return 1;}
u32 fnv_bytes(u32 h,const void*s,unsigned n){const u8*p=s;while(n--){h^=*p++;h*=16777619U;}return h;}
/* IEEE-754 binary64 output from the exact fixed-point rational, using integer
   long division and round-to-nearest/even. No x87 instructions or FPU needed. */
void ieee64(i32 value,u8 out[8]){u32 n,d=10000,rem;u64 frac=0,bits;int e=0,i,guard,sign=value<0;n=sign?(u32)(-(i64)value):(u32)value;if(!n){m_zero(out,8);return;}
 if(n>=d){while((u64)n>=(u64)d*2){d*=2;e++;}}else while(n<d){n*=2;e--;}
 rem=n-d;for(i=0;i<52;i++){rem*=2;frac<<=1;if(rem>=d){frac|=1;rem-=d;}}
 rem*=2;guard=rem>=d;if(guard)rem-=d;if(guard&&(rem|| (frac&1)))frac++;
 if(frac==((u64)1<<52)){frac=0;e++;}bits=((u64)sign<<63)|((u64)(e+1023)<<52)|frac;for(i=0;i<8;i++){out[i]=(u8)bits;bits>>=8;}}
