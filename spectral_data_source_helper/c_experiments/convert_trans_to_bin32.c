


#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <ctype.h>
#include <stdlib.h>
#include <errno.h>
#include <stdbool.h>
#include <time.h>

#define BIN32_HEADER_3_COLS "STRUCTURED{;upper_id;0;TYPE{;<u4;};lower_id;4;TYPE{;<u4;};einstein_A;8;TYPE{;<f4;};}"
#define BIN32_HEADER_4_COLS "STRUCTURED{;upper_id;0;TYPE{;<u4;};lower_id;4;TYPE{;<u4;};einstein_A;8;TYPE{;<f4;};wavenumber;8;TYPE{;<f4;};}"

#define MAX_ERR_MSG_SIZE (1024) // bytes

const size_t MAX_CHUNK_SIZE = 8*1024; // bytes, try to match to cache size
const double TRANS_STR_FLOAT32_FACTOR = 1E20; // 32-bit floating point values do not have enough exponent to represent all trasition strength values, therefore multiply by this constant (and divide when loading from file)

typedef bool (*CharFilterFn)(const char);

struct TransEntry {
	uint32_t lo;
	uint32_t hi;
	double value;
	double wavenumber;
} TRANS_ENTRY;

typedef struct TableProgress {
	size_t n_bytes; // number of bytes processed
	size_t n_entries; // number of entries processed
} TableProgress;

typedef struct FFI_INPUT {
	char* input_file;
	char* output_file;
} FFI_INPUT;

typedef struct FFI_TASK_INFO {
	bool complete;
	int errnum;
	char errmsg[MAX_ERR_MSG_SIZE];
} FFI_TASK_INFO;

typedef struct FFI_OUTPUT {
	FFI_TASK_INFO task_info;
	uint64_t n_bytes;
	uint64_t n_entries;
	double bytes_sec;
	double entries_sec;
	double time_elapsed_sec;
} FFI_OUTPUT;


bool is_newline(const char c){
	return c == '\n';
}

bool is_space(const char c){
	return (isspace((int)c) != 0);
}

void write_header(const char* msg, FILE* f){
	// Write header in 4-byte blocks. Finish with null byte of 4th byte of last block
	
	int n = 4 - (strlen(msg) % 4);
	fputs(msg, f);
	
	for(;n > 0; --n){
		fputc('\0', f);
	}
	
}

int count_cols_in_file_filters(
	FILE* f, 
	CharFilterFn is_col_separator_char_fn, 
	CharFilterFn is_cols_end_char
){
	char buffer[MAX_CHUNK_SIZE];
	int i = 0;
	int n_cols = 0;
	bool prev_was_col_sep = true;
	size_t bytes_read = 0;
	
	while ((bytes_read = fread(buffer, sizeof(char), MAX_CHUNK_SIZE, f)) > 0){
		for (i=0; i<bytes_read; ++i){
			if (buffer[i] == '\n'){ // we are at a new line so we have got all the columns
				return n_cols;
			}
			else if (is_col_separator_char_fn(buffer[i])) { // if current character is column separator, then skip
				prev_was_col_sep = true;
			}
			else { // if current character is printable, then we have a new column if the previous character was column separator, otherwise skip
				if (prev_was_col_sep){
					++n_cols;
				}
				prev_was_col_sep = false;
			}
		}
	}
}

int count_cols_in_file(FILE* f){
	return count_cols_in_file_filters(f, is_space, is_newline);
}

size_t read_uint32(char const* p, uint32_t * const x){
	size_t i=0;
	const char* p0 = p;
	int8_t y = 0;
	(*x) = 0;
	while (isspace(*p)){
		++p;
	}
	y = (*p) - '0';
	while ((y >= 0) && (y<10)){
		(*x) = 10*(*x) + y;
		++p;
		y = (*p) - '0';
	}
	return (p-p0);
}

size_t read_float32(char const* p, float * const x){
	char* q = (char*)p;
	*x = strtof(p,&q);
	return (q-p);
}

size_t read_float64(char const* p, double * const x){
	char* q = (char*)p;
	*x = strtod(p,&q);
	return (q-p);
}

void write_bin32_entry_3col(FILE* g, const uint32_t trans_lo, const uint32_t trans_hi, const float value){
	fputc(*((char*)(&trans_lo)), g);
	fputc(*(((char*)(&trans_lo))+1), g);
	fputc(*(((char*)(&trans_lo))+2), g);
	fputc(*(((char*)(&trans_lo))+3), g);
	
	fputc(*((char*)(&trans_hi)), g);
	fputc(*(((char*)(&trans_hi))+1), g);
	fputc(*(((char*)(&trans_hi))+2), g);
	fputc(*(((char*)(&trans_hi))+3), g);
	
	fputc(*((char*)(&value)), g);
	fputc(*(((char*)(&value))+1), g);
	fputc(*(((char*)(&value))+2), g);
	fputc(*(((char*)(&value))+3), g);
}

void write_bin32_entry_4col(FILE* g, const uint32_t trans_lo, const uint32_t trans_hi, const float value, const float wavenumber){
	write_bin32_entry_3col(g, trans_lo, trans_hi, value);
	
	fputc(*((char*)(&wavenumber)), g);
	fputc(*(((char*)(&wavenumber))+1), g);
	fputc(*(((char*)(&wavenumber))+2), g);
	fputc(*(((char*)(&wavenumber))+3), g);
}

size_t trans_read_from_buffer_write_bin32_3col(char* buffer, FILE* g){
	size_t n_bytes_consumed = 0;
	n_bytes_consumed += read_uint32(buffer+n_bytes_consumed, &(TRANS_ENTRY.lo));
	n_bytes_consumed += read_uint32(buffer+n_bytes_consumed, &(TRANS_ENTRY.hi));
	n_bytes_consumed += read_float64(buffer+n_bytes_consumed, &(TRANS_ENTRY.value));
	
	//printf("INNER: %ld %ld %ld %d %d %f\n", rp, half_bytes_to_consume, i, trans_lo, trans_hi, value);
	//printf("INNER: %ud %ud %E\n", trans_lo, trans_hi, value);
	write_bin32_entry_3col(g, TRANS_ENTRY.lo, TRANS_ENTRY.hi, (float)(1E20*TRANS_ENTRY.value));
	
	return n_bytes_consumed;
}

size_t trans_read_from_buffer_write_bin32_4col(char* buffer, FILE* g){
	size_t n_bytes_consumed = 0;
	n_bytes_consumed += read_uint32(buffer+n_bytes_consumed, &(TRANS_ENTRY.lo));
	n_bytes_consumed += read_uint32(buffer+n_bytes_consumed, &(TRANS_ENTRY.hi));
	n_bytes_consumed += read_float64(buffer+n_bytes_consumed, &(TRANS_ENTRY.value));
	n_bytes_consumed += read_float64(buffer+n_bytes_consumed, &(TRANS_ENTRY.wavenumber));
	
	//printf("INNER: %ld %ld %ld %d %d %f\n", rp, half_bytes_to_consume, i, trans_lo, trans_hi, value);
	//printf("INNER: %ud %ud %E\n", trans_lo, trans_hi, value);
	write_bin32_entry_4col(g, TRANS_ENTRY.lo, TRANS_ENTRY.hi, (float)(1E20*TRANS_ENTRY.value), (float)(TRANS_ENTRY.wavenumber));
	
	return n_bytes_consumed;
}

void convert_to_bin32_3col(
	FILE* f, 
	FILE* g,
	TableProgress * const table_progress
){
	char buffer[2*MAX_CHUNK_SIZE];
	size_t bytes_read = 0;
	size_t bytes_to_consume = 0;
	size_t half_bytes_to_consume = 0;
	size_t rp=0;
	size_t wp=0;
	size_t i=0;
	
	
	while ((bytes_read = fread(buffer+wp, sizeof(char), MAX_CHUNK_SIZE, f)) > 0){
		bytes_to_consume = bytes_read + wp;
		buffer[bytes_to_consume] = '\0';
		half_bytes_to_consume = bytes_to_consume / 2;
		//printf("OUTER: %s\n", buffer);
		//printf("OUTER: %ld %ld %ld %ld %ld %ld\n", bytes_read, bytes_to_consume, half_bytes_to_consume, rp, wp, i);
		while(rp < half_bytes_to_consume){
			rp += trans_read_from_buffer_write_bin32_3col(buffer+rp, g);
			++i;
		}
		wp = bytes_to_consume - rp;
		memmove(buffer, buffer+rp, wp);
		rp = 0;
		
	}
	
	buffer[wp]='\0'; // end of data marked with null character
	while(rp < wp){
		rp += trans_read_from_buffer_write_bin32_3col(buffer+rp, g);
		++i;
	}
	
	table_progress->n_bytes = ftell(f);
	table_progress->n_entries = i;
	printf("%ld  %ld\n", table_progress->n_bytes, table_progress->n_entries);
	
	fclose(f);
	fclose(g);
}

void convert_to_bin32_4col(
	FILE* f, 
	FILE* g,
	TableProgress * const table_progress
){
	char buffer[2*MAX_CHUNK_SIZE];
	size_t bytes_read = 0;
	size_t bytes_to_consume = 0;
	size_t half_bytes_to_consume = 0;
	size_t rp=0;
	size_t wp=0;
	size_t i=0;
	
	while ((bytes_read = fread(buffer+wp, sizeof(char), MAX_CHUNK_SIZE, f)) > 0){
		bytes_to_consume = bytes_read + wp;
		buffer[bytes_to_consume] = '\0';
		half_bytes_to_consume = bytes_to_consume / 2;
		//printf("OUTER: %s\n", buffer);
		//printf("OUTER: %ld %ld %ld %ld %ld %ld\n", bytes_read, bytes_to_consume, half_bytes_to_consume, rp, wp, i);
		while(rp < half_bytes_to_consume){
			rp += trans_read_from_buffer_write_bin32_4col(buffer+rp, g);
			++i;
		}
		wp = bytes_to_consume - rp;
		memmove(buffer, buffer+rp, wp);
		rp = 0;
		
	}
	
	buffer[wp]='\0'; // end of data marked with null character
	while(rp < wp){
		rp += trans_read_from_buffer_write_bin32_4col(buffer+rp, g);
		++i;
	}
	
	table_progress->n_bytes = ftell(f);
	table_progress->n_entries = i;
	printf("%ld  %ld\n", table_progress->n_bytes, table_progress->n_entries);
	
	fclose(f);
	fclose(g);
}

void ffi_run(FFI_INPUT in, FFI_OUTPUT * const out){
	out->task_info.complete = false;
	out->task_info.errnum = 0;
	out->task_info.errmsg[0] = '\0';
	
	//printf("input_file %s\n",in.input_file);
	//printf("output_file %s\n",in.output_file);
	
	struct timespec ts_start, ts_end;
	TableProgress table_progress;
	double time_elapsed_sec;
	int MAX_LINE_SIZE=1024;
	int MAX_CHUNK_SIZE=128;
	
	char chunk[MAX_CHUNK_SIZE];
	char line[MAX_LINE_SIZE];
	char* cptr;
	
	int n_cols = 0;
	int n_fmt_ok = 0;
	int trans_lo, trans_hi;
	double value;
	
	uint32_t t1, t2;
	float v;
	
	
	timespec_get(&ts_start, TIME_UTC);
	
	FILE* f = fopen(in.input_file, "rb");
	FILE* g = fopen(in.output_file, "wb");
	
	
	if (f==NULL){
		out->task_info.errnum = errno;
		snprintf(out->task_info.errmsg, MAX_ERR_MSG_SIZE, "Could not open file '%s'\n", in.input_file);
		return;
	}
	
	if (g==NULL){
		out->task_info.errnum = errno;
		snprintf(out->task_info.errmsg, MAX_ERR_MSG_SIZE, "Could not open file '%s'\n", in.output_file);
		return;
	}
	
	n_cols = count_cols_in_file(f);
	if (fseek(f, 0, SEEK_SET)){
		out->task_info.errnum = errno;
		snprintf(out->task_info.errmsg, MAX_ERR_MSG_SIZE, "Could not seek to start of file '%s' after counting number of columns\n", in.input_file);
		return;
	}
	
	switch (n_cols){
		case 3:
			write_header(BIN32_HEADER_3_COLS, g);
			convert_to_bin32_3col(f, g, &table_progress);
			break;
		case 4:
			write_header(BIN32_HEADER_4_COLS, g);
			convert_to_bin32_4col(f, g, &table_progress);
			break;
		default:
			out->task_info.errnum = 1;
			snprintf(out->task_info.errmsg, MAX_ERR_MSG_SIZE, "Input file '%s' must have 3 or 4 columns, but found %d columns.", in.input_file, n_cols);
			return;
	}
	
	
	timespec_get(&ts_end, TIME_UTC);
	time_elapsed_sec = (ts_end.tv_sec - ts_start.tv_sec) + 1E-9*(ts_end.tv_nsec - ts_start.tv_nsec);
	
	out->n_bytes = table_progress.n_bytes;
	out->n_entries = table_progress.n_entries;
	out->time_elapsed_sec = time_elapsed_sec;
	out->bytes_sec = out->n_bytes/time_elapsed_sec;
	out->entries_sec = out->n_entries/time_elapsed_sec;
	
	out->task_info.complete = true;
	return;
	
}

int main(int argc, char** argv){
	printf("argc=%d\n", argc);
	for(int i=0; i<argc; ++i){
		printf("argv[%d]=%s\n",i,argv[i]);
	}
	
	FFI_INPUT in = {.input_file=argv[1], .output_file=argv[2]};
	FFI_OUTPUT out = {.task_info={.complete=false, .errnum=0, .errmsg[0]='\0'}};
	
	ffi_run(in, &out);
	
	if (!out.task_info.complete){
		printf("ERROR: %s\n", out.task_info.errmsg);
		return out.task_info.errnum;
	}
	
	printf("INFO :: FILE CONVERTED in %.2lf sec %.2lf MB/s %.2lf Million Entries/s\n", out.time_elapsed_sec, out.bytes_sec/(1024*1024), out.entries_sec*1E-6);
	
	
	return 0;
}