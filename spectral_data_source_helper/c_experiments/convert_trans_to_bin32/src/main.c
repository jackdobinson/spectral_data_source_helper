

#include "ffi.h"

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