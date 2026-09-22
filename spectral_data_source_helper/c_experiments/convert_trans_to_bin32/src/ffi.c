

#include "ffi.h"

#define SHARED_LIB_EXPORT_FN __attribute__((visibility("default"))) 

SHARED_LIB_EXPORT_FN
void ffi_run(FFI_INPUT in, FFI_OUTPUT * const out){
	out->task_info.complete = false;
	out->task_info.errnum = 0;
	out->task_info.errmsg[0] = '\0';
	
	//printf("input_file %s\n",in.input_file);
	//printf("output_file %s\n",in.output_file);
	
	struct timespec ts_start, ts_end;
	TableProgress table_progress;
	double time_elapsed_sec;
	int n_cols = 0;

	
	
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
	
	n_cols = ascii_count_cols_in_file(f);
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
	
	if (__UNLIKELY(errno != 0)){
		out->task_info.errnum = errno;
		snprintf(out->task_info.errmsg, MAX_ERR_MSG_SIZE, "An error (errno %d :: %s) occured when processing record %lu (byte %lu) of input file", errno, strerror(errno), table_progress.n_entries, table_progress.n_bytes);
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
