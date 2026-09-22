
#ifndef __IMPL__INCLUDED__
#define __IMPL__INCLUDED__

#include <stdio.h>
//#include <stdint.h>
//#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <errno.h>
#include <stdbool.h>
#include <time.h>
#include <assert.h>
#include <math.h>


#include "ascii_utils.h"


#define BIN32_HEADER_3_COLS "STRUCTURED{;upper_id;0;TYPE{;<u4;};lower_id;4;TYPE{;<u4;};einstein_A;8;TYPE{;<f4;};}"
#define BIN32_HEADER_4_COLS "STRUCTURED{;upper_id;0;TYPE{;<u4;};lower_id;4;TYPE{;<u4;};einstein_A;8;TYPE{;<f4;};wavenumber;8;TYPE{;<f4;};}"

#define MAX_ERR_MSG_SIZE (1024) // bytes

#define __UNLIKELY(X) __builtin_expect((X),0)


struct TransEntry {
	uint32_t lo;
	uint32_t hi;
	float value;
	float wavenumber;
};

typedef struct TableProgress {
	size_t n_bytes; // number of bytes processed
	size_t n_entries; // number of entries processed
} TableProgress;


void write_header(const char* msg, FILE* f);
void write_bin32_entry_3col(FILE* g, const uint32_t trans_lo, const uint32_t trans_hi, const float value);
void write_bin32_entry_4col(FILE* g, const uint32_t trans_lo, const uint32_t trans_hi, const float value, const float wavenumber);
size_t trans_read_from_buffer_write_bin32_3col(char* buffer, FILE* g);
size_t trans_read_from_buffer_write_bin32_4col(char* buffer, FILE* g);
void convert_to_bin32_3col(
	FILE* f, 
	FILE* g,
	TableProgress * const table_progress
);
void convert_to_bin32_4col(
	FILE* f, 
	FILE* g,
	TableProgress * const table_progress
);


#endif //__IMPL__INCLUDED__