
#ifndef __FFI__INCLUDED__
#define __FFI__INCLUDED__


#include "impl.h"

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


void ffi_run(FFI_INPUT in, FFI_OUTPUT * const out);

#endif //__FFI__INCLUDED__