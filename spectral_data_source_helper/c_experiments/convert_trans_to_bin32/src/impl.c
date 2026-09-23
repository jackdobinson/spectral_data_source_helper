
#include "impl.h"

const size_t MAX_CHUNK_SIZE = 8*1024; // bytes, try to match to cache size
const double TRANS_STR_FLOAT32_FACTOR = 1E20; // 32-bit floating point values do not have enough exponent to represent all trasition strength values, therefore multiply by this constant (and divide when loading from file)
const int16_t TRANS_STR_FLOAT32_EXP = 20; // 32-bit floating point values do not have enough exponent to represent all trasition strength values, therefore multiply by this constant (and divide when loading from file)

struct TransEntry TRANS_ENTRY;


void write_header(const char* msg, FILE* f){
	// Write header in 4-byte blocks. Finish with null byte of 4th byte of last block
	
	int n = 4 - (strlen(msg) % 4);
	fputs(msg, f);
	
	for(;n > 0; --n){
		fputc('\0', f);
	}
	
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
	n_bytes_consumed += ascii_read_uint32(buffer+n_bytes_consumed, &(TRANS_ENTRY.lo));
	//printf("n_bytes_consumed %d\n", n_bytes_consumed);
	n_bytes_consumed += ascii_read_uint32(buffer+n_bytes_consumed, &(TRANS_ENTRY.hi));
	//printf("n_bytes_consumed %d\n", n_bytes_consumed);
	//double tempf; n_bytes_consumed += read_float64(buffer+n_bytes_consumed, &tempf); tempf*=TRANS_STR_FLOAT32_FACTOR; TRANS_ENTRY.value=tempf;
	n_bytes_consumed += ascii_read_float32_fast_offset(buffer+n_bytes_consumed, &(TRANS_ENTRY.value), TRANS_STR_FLOAT32_EXP);
	//printf("n_bytes_consumed %d\n", n_bytes_consumed);
	//printf("INNER: %ld %ld %ld %d %d %f\n", rp, half_bytes_to_consume, i, trans_lo, trans_hi, value);
	//printf("INNER: %ud %ud %E\n", trans_lo, trans_hi, value);
	//write_bin32_entry_3col(g, TRANS_ENTRY.lo, TRANS_ENTRY.hi, (float)(1E20*TRANS_ENTRY.value));
	write_bin32_entry_3col(g, TRANS_ENTRY.lo, TRANS_ENTRY.hi, TRANS_ENTRY.value);
	
	//assert(n_bytes_consumed>0);
	
	return n_bytes_consumed;
}

size_t trans_read_from_buffer_write_bin32_4col(char* buffer, FILE* g){
	size_t n_bytes_consumed = 0;
	n_bytes_consumed += ascii_read_uint32(buffer+n_bytes_consumed, &(TRANS_ENTRY.lo));
	n_bytes_consumed += ascii_read_uint32(buffer+n_bytes_consumed, &(TRANS_ENTRY.hi));
	//n_bytes_consumed += read_float64(buffer+n_bytes_consumed, &(TRANS_ENTRY.value));
	//double tempf; n_bytes_consumed += read_float64(buffer+n_bytes_consumed, &tempf); tempf*=TRANS_STR_FLOAT32_FACTOR; TRANS_ENTRY.value=tempf;
	n_bytes_consumed += ascii_read_float32_fast_offset(buffer+n_bytes_consumed, &(TRANS_ENTRY.value), TRANS_STR_FLOAT32_EXP);
	//n_bytes_consumed += read_float64(buffer+n_bytes_consumed, &(TRANS_ENTRY.wavenumber));
	n_bytes_consumed += ascii_read_float32_fast(buffer+n_bytes_consumed, &(TRANS_ENTRY.wavenumber));
	
	//printf("INNER: %ld %ld %ld %d %d %f\n", rp, half_bytes_to_consume, i, trans_lo, trans_hi, value);
	//printf("INNER: %ud %ud %E\n", trans_lo, trans_hi, value);
	//write_bin32_entry_4col(g, TRANS_ENTRY.lo, TRANS_ENTRY.hi, (float)(1E20*TRANS_ENTRY.value), (float)(TRANS_ENTRY.wavenumber));
	write_bin32_entry_4col(g, TRANS_ENTRY.lo, TRANS_ENTRY.hi, TRANS_ENTRY.value, TRANS_ENTRY.wavenumber);
	
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
			if (__UNLIKELY(errno != 0)){
				printf("ERROR: TRANS_ENTRY .lo %u .hi %u .value %E\n", TRANS_ENTRY.lo, TRANS_ENTRY.hi, TRANS_ENTRY.value);
				table_progress->n_bytes = ftell(f);
				table_progress->n_entries = i;
				return;
			}
			++i;
			//printf("INNER: %ld %ld\n", rp, i);
		}
		wp = bytes_to_consume - rp;
		memmove(buffer, buffer+rp, wp);
		rp = 0;
		rp += ascii_skip_whitespace(buffer+rp);
	}
		
	buffer[wp]='\0'; // end of data marked with null character
	
	while(rp < wp){
		rp += trans_read_from_buffer_write_bin32_3col(buffer+rp, g);
		
		if (__UNLIKELY(errno != 0)){
			table_progress->n_bytes = ftell(f);
			table_progress->n_entries = i;
			return;
		}
		++i;
		rp += ascii_skip_whitespace(buffer+rp);
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
	
	errno = 0; // clear errno
	
	while ((bytes_read = fread(buffer+wp, sizeof(char), MAX_CHUNK_SIZE, f)) > 0){
		bytes_to_consume = bytes_read + wp;
		buffer[bytes_to_consume] = '\0';
		half_bytes_to_consume = bytes_to_consume / 2;
		//printf("OUTER: %s\n", buffer);
		//printf("OUTER: %ld %ld %ld %ld %ld %ld\n", bytes_read, bytes_to_consume, half_bytes_to_consume, rp, wp, i);
		while(rp < half_bytes_to_consume){
			rp += trans_read_from_buffer_write_bin32_4col(buffer+rp, g);
			if (__UNLIKELY(errno != 0)){
				table_progress->n_bytes = ftell(f);
				table_progress->n_entries = i;
				return;
			}
			++i;
		}
		wp = bytes_to_consume - rp;
		memmove(buffer, buffer+rp, wp);
		rp = 0;
		rp += ascii_skip_whitespace(buffer+rp);
	}
	
	buffer[wp]='\0'; // end of data marked with null character
	while(rp < wp){
		rp += trans_read_from_buffer_write_bin32_4col(buffer+rp, g);
		if (__UNLIKELY(errno != 0)) {
			table_progress->n_bytes = ftell(f);
			table_progress->n_entries = i;
			return;
		}
		++i;
		rp += ascii_skip_whitespace(buffer+rp);
	}
	
	table_progress->n_bytes = ftell(f);
	table_progress->n_entries = i;
	printf("%ld  %ld\n", table_progress->n_bytes, table_progress->n_entries);
	
	fclose(f);
	fclose(g);
}
