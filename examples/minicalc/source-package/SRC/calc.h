#ifndef MINICALC_H
#define MINICALC_H
/* MiniCalc 0.1: portable calculation core; no GEOS ABI dependency. */
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef int i32;
typedef unsigned long long u64;
typedef long long i64;
#define CELL_LIMIT 256
#define INPUT_LIMIT 63
#define ROW_LIMIT 999
#define COL_LIMIT 26
#define SCALE 10000
#define NUM_LIMIT 2147483647
#define PATH_LIMIT 80
#define E_NONE 0
#define E_SYNTAX 1
#define E_DIVZERO 2
#define E_VALUE 3
#define E_REF 4
#define E_NAME 5
#define E_CYCLE 6
#define E_NUM 7
#define E_DEPTH 8
#define E_PREC 9
#define E_LIMIT 10
#define K_NUMBER 0
#define K_TEXT 1
#define K_BLANK 2

typedef struct {u16 row; u8 col, state; i32 value; u8 error, kind; char input[INPUT_LIMIT+1];} Cell;
typedef struct {Cell cells[CELL_LIMIT]; int count;} Sheet;
extern Sheet book, staging;
extern int changed, undo_ready;
extern char message[160];
extern char document_path[PATH_LIMIT];
extern u32 saved_master_hash, saved_master_size, saved_view_hash, saved_view_size;
extern int master_known, view_known;

void *m_copy(void *d,const void *s,unsigned n);
void *m_zero(void *d,unsigned n);
unsigned s_len(const char *s);
int s_eq(const char *a,const char *b);
void s_copy(char *d,const char *s,unsigned cap);
int ascii_upper(int c);
int digit(int c);
int address(const char *s,int *row,int *col);
void cell_name(int row,int col,char *out);
const char *error_name(int error);
int find_cell(const Sheet *s,int row,int col);
int put_cell(Sheet *s,int row,int col,const char *input);
int edit_cell(int row,int col,const char *input);
void new_book(void);
void recalculate(void);
void format_number(i32 v,char *out);
void cell_display(int row,int col,char *out,unsigned cap);
int copy_range(int sr,int sc,const char *destination);
int undo_book(void);
int parse_number(const char *s,i32 *value);
u32 fnv_bytes(u32 h,const void *s,unsigned n);
void ieee64(i32 value,u8 out[8]);

/* Platform adapter: negative DOS-style error code on failure. */
int file_open(const char *path);
int file_create_new(const char *path);
int file_read(int fd,void *buffer,unsigned count);
int file_write(int fd,const void *buffer,unsigned count);
int file_close(int fd);
int file_rename(const char *from,const char *to);
int file_remove(const char *path);
int read_document(const char *path);
int save_document(const char *path);
int normalize_path(const char *path,char *master,char *view,int *is_view);
int file_digest(const char *path,u32 *hash,u32 *size);
int write_master(int fd);
int write_view(int fd);
void reset_session(void);

void screen_start(void);
void screen_stop(void);
void screen_line(int row,int column,const char *text,int length,int attribute);
void screen_cursor(int row,int column,int visible);
int keyboard_read(void);
void interactive(const char *initial_path);
#endif
