


#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <ctype.h>
#include <stdlib.h>
#include <errno.h>
#include <stdbool.h>
#include <time.h>
#include <assert.h>
#include <math.h>

#include "power_of_two_factor_lut.h"


#define BIN32_HEADER_3_COLS "STRUCTURED{;upper_id;0;TYPE{;<u4;};lower_id;4;TYPE{;<u4;};einstein_A;8;TYPE{;<f4;};}"
#define BIN32_HEADER_4_COLS "STRUCTURED{;upper_id;0;TYPE{;<u4;};lower_id;4;TYPE{;<u4;};einstein_A;8;TYPE{;<f4;};wavenumber;8;TYPE{;<f4;};}"

#define MAX_ERR_MSG_SIZE (1024) // bytes

const size_t MAX_CHUNK_SIZE = 8*1024; // bytes, try to match to cache size
const double TRANS_STR_FLOAT32_FACTOR = 1E20; // 32-bit floating point values do not have enough exponent to represent all trasition strength values, therefore multiply by this constant (and divide when loading from file)
const double TRANS_STR_FLOAT32_EXP = 20; // 32-bit floating point values do not have enough exponent to represent all trasition strength values, therefore multiply by this constant (and divide when loading from file)

typedef bool (*CharFilterFn)(const char);

struct TransEntry {
	uint32_t lo;
	uint32_t hi;
	//double value;
	//double wavenumber;
	float value;
	float wavenumber;
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



size_t read_direct_uint32(char const* p, uint32_t * const x){
	const char* p0 = p;
	int8_t y = 0;
	(*x) = 0;
	y = (*p) - '0';
	while ((y >= 0) && (y<10)){
		(*x) = 10*(*x) + y;
		++p;
		y = (*p) - '0';
	}
	return (p-p0);
}

size_t read_uint32(char const* p, uint32_t * const x){
	const char* p0 = p;
	while (isspace(*p)){
		++p;
	}
	
	return (p-p0) + read_direct_uint32(p, x);
}

size_t read_direct_decimal_uint32(char const* p, uint32_t * const x){
	const char* p0 = p;
	uint32_t exp = 1<<31; // 0001 -> 1000
	uint32_t pos = 0;
	uint32_t rem = 0;
	uint32_t pow = 10;
	uint32_t a=0;
	uint32_t y = 0;
	bool y_valid = true;
	
	(*x) = 0;
	
	printf("*p %c\n", *p);
	
	y = (*p) - '0';
	y_valid = (y >= 0) && (y<10);
	while ((y_valid || (a !=0)) && (exp > 0)){
		//printf("y=%d\n", y); fflush(0);
		//printf("rem %u y %u pos %u pow %u\n", rem, y, pos, pow);
		//printf("exp 0x%08X\n", exp);
		//printf("y<<pos %u\n", y<<pos);
		//printf("(rem + (y<<pos)) %u\n", (rem + (y<<pos)));
		a = (rem + (y<<pos))<<1;
		//printf("a %u\n", a);
		if (a > pow){
			(*x) |= exp;
			a -= pow;
		}
		//printf("*x 0x%08X\n", *x);
		rem = a*10;
		
		pow *= 10;
		exp >>= 1;
		++pos;
		if (y_valid){
			++p;
			//printf("*p %c\n", *p);
			y = (*p) - '0';
			y_valid = (y >= 0) && (y<10);
		} else {
			y = 0;
		}
		
	}
	
	//printf("*x %u\n", *x);
	//printf("*x 0x%08X\n", *x);
	return (p-p0);
}


size_t read_direct_int32(char const* p, uint32_t * const x){
	const char* p0 = p;
	int8_t y = 0;
	short sign = 1;
	short ipsign = 0;
	short insign = 0;
	(*x) = 0;
	
	ipsign = ((*p) == '+');
	insign = ((*p) == '-');
	
	sign -= 2*insign;
	
	p+=(ipsign|insign);
	
	y = (*p) - '0';
	while ((y >= 0) && (y<10)){
		(*x) = 10*(*x) + y;
		++p;
		y = (*p) - '0';
	}
	(*x) *= sign;
	return (p-p0);
}

size_t read_direct_uint16(char const* p, uint16_t * const x){
	size_t i=0;
	const char* p0 = p;
	int8_t y = 0;
	(*x) = 0;

	y = (*p) - '0';
	while ((y >= 0) && (y<10)){
		(*x) = 10*(*x) + y;
		++p;
		y = (*p) - '0';
	}
	return (p-p0);
}

size_t read_direct_int16(char const* p, int16_t * const x){
	size_t i=0;
	const char* p0 = p;
	int8_t y = 0;
	short sign = 1;
	short ipsign = 0;
	short insign = 0;
	(*x) = 0;
	
	ipsign = ((*p) == '-');
	insign = ((*p) == '+');
	
	sign -= 2*insign;
	
	p+=(ipsign|insign);
	
	y = (*p) - '0';
	while ((y >= 0) && (y<10)){
		(*x) = 10*(*x) + y;
		++p;
		y = (*p) - '0';
	}
	return (p-p0);
	
	
}

void consume_sign(char const**const p, int8_t * const sign){
	(*sign) = 1 - 2*((**p) == '-');
	(*p)+=(((*sign)==-1)|((**p) == '+'));
} 

void consume_int16_unsafe(char const ** const p, int16_t *const x){
	int8_t sign;
	int8_t y = 0;
	
	consume_sign(p, &sign);
	
	y = (**p) - '0';
	while ((y >= 0) && (y<10)){
		(*x) = 10*(*x) + y;
		++(*p);
		y = (**p) - '0';
	}
	(*x) *= sign;
}

void consume_int16(char const ** const p, int16_t *const x){
	(*x) = 0;
	consume_int16_unsafe(p, x);
}

void consume_exponent(char const ** const p, int16_t *const exponent){
	if ( ((**p) == 'E') | ((**p) == 'e') | ((**p) == 'D') | ((**p) == 'd') ){
		++(*p);
		consume_int16(p, exponent);
	}
}




void consume_uint32_unsafe(char const ** const p, uint32_t *const x){
	// NOTE: Does not zero `x` before consuming number
	int8_t y = 0;
	y = (**p) - '0';
	while ((y >= 0) && (y<10)){
		(*x) = 10*(*x) + y;
		++(*p);
		y = (**p) - '0';
	}
}

void consume_uint32(char const ** const p, uint32_t *const x){
	(*x) = 0;
	consume_uint32_unsafe(p,x);
}


void consume_decimal_as_uint32(char const ** const p, uint32_t * const x, int16_t * const exp_10){
	
	(*x) = 0;
	(*exp_10) = 0;
	
	//printf("DEBUG :: consume_decimal_as_uint32 :: **p '%c'\n", **p);
	consume_uint32_unsafe(p, x);
	//printf("DEBUG :: consume_decimal_as_uint32 :: x %u\n", *x);
	//printf("DEBUG :: consume_decimal_as_uint32 :: **p '%c'\n", **p);
	
	if ((**p) == '.'){ // decimal point detected
		++(*p);
		const char* p0 = *p;
		consume_uint32_unsafe(p, x);
		//printf("DEBUG :: consume_decimal_as_uint32 :: x %u\n", *x);
		(*exp_10) = (p0 - (*p));
	}
}



void skip_whitespace(char const** const p){
	while (isspace(**p)){
		++(*p);
	}
}

void consume_sci_notation_by_parts(char const ** const p, int8_t *const sign, uint32_t * const x, int16_t * const exp_10){
	int16_t decimal_exp_10 = 0;
	int16_t exponent_exp_10 = 0;
	
	consume_sign(p, sign);
	//printf("DEBUG :: consume_sci_notation_by_parts :: sign %d\n", *sign);
	consume_decimal_as_uint32(p, x, &decimal_exp_10);
	//printf("DEBUG :: consume_sci_notation_by_parts :: x %u decimal_exp_10 %d\n", *x, decimal_exp_10);
	consume_exponent(p, &exponent_exp_10);
	//printf("DEBUG :: consume_sci_notation_by_parts :: exponent_exp_10 %d\n", exponent_exp_10);
	(*exp_10) = decimal_exp_10 + exponent_exp_10;
}





size_t binary_count_lhs_zeros_uint64(uint64_t x){
	size_t count = 0;
	if ((x & 0xFFFFFFFF00000000u) == 0){ // 1111 1111 1111 1111 1111 1111 1111 1111
		count += 32;
		x <<= 32;
	}
	if ((x & 0xFFFF000000000000u) == 0){ // 1111 1111 1111 1111 0000 0000 0000 0000
		count += 16;
		x <<= 16;
	}
	if ((x & 0xFF00000000000000u) == 0){ // 1111 1111 0000 0000 0000 0000 0000 0000
		count += 8;
		x <<= 8;
	}
	if ((x & 0xF000000000000000u) == 0){ // 1111 0000 0000 0000 0000 0000 0000 0000
		count += 4;
		x <<= 4;
	}
	if ((x & 0xC000000000000000u) == 0){ // 1100 0000 0000 0000 0000 0000 0000 0000
		count += 2;
		x <<= 2;
	}
	if ((x & 0x8000000000000000u) == 0){ // 1000 0000 0000 0000 0000 0000 0000 0000
		count += 1;
		x <<= 1;
	}
	return count;
}
size_t binary_shift_lhs_zeros_uint64(uint64_t * const x){
	size_t shift = binary_count_lhs_zeros_uint64(*x);
	(*x) <<= shift;
	return shift;
}


size_t binary_count_rhs_zeros_uint64(uint64_t x){
	size_t count = 0;
	if ((x & 0x00000000FFFFFFFFu) == 0){ // 0000 0000 0000 0000 1111 1111 1111 1111
		count += 32;
		x >>= 32;
	}
	if ((x & 0x000000000000FFFFu) == 0){ // 0000 0000 0000 0000 1111 1111 1111 1111
		count += 16;
		x >>= 16;
	}
	if ((x & 0x00000000000000FFu) == 0){ // 0000 0000 0000 0000 0000 0000 1111 1111
		count += 8;
		x >>= 8;
	}
	if ((x & 0x000000000000000Fu) == 0){ // 0000 0000 0000 0000 0000 0000 0000 1111
		count += 4;
		x >>= 4;
	}
	if ((x & 0x0000000000000003u) == 0){ // 0000 0000 0000 0000 0000 0000 0000 0011
		count += 2;
		x >>= 2;
	}
	if ((x & 0x0000000000000001u) == 0){ // 0000 0000 0000 0000 0000 0000 0000 0001
		count += 1;
		x >>= 1;
	}
	return count;
}
size_t binary_shift_rhs_zeros_uint64(uint64_t * const x){
	size_t shift = binary_count_rhs_zeros_uint64(*x);
	(*x) >>= shift;
	return shift;
}


int binary_shift_uint64_to_uint32(uint64_t * const x){
	// +ve is shift to LHS, -ve is shift to RHS
	int count = 32 - binary_count_lhs_zeros_uint64(*x);
	//printf("DEBUG :: binary_shift_uint64_to_uint32 :: count %d\n", count);
	
	if (count > 0){
		(*x) >>= count;
	} else {
		(*x) <<= (-1*count);
	}
	return count;
}

size_t binary_count_lhs_zeros_uint32(uint32_t x){
	size_t count = 0;
	if ((x & 0xFFFF0000u) == 0){ // 1111 1111 1111 1111 0000 0000 0000 0000
		count += 16;
		x <<= 16;
	}
	if ((x & 0xFF000000u) == 0){ // 1111 1111 0000 0000 0000 0000 0000 0000
		count += 8;
		x <<= 8;
	}
	if ((x & 0xF0000000u) == 0){ // 1111 0000 0000 0000 0000 0000 0000 0000
		count += 4;
		x <<= 4;
	}
	if ((x & 0xC0000000u) == 0){ // 1100 0000 0000 0000 0000 0000 0000 0000
		count += 2;
		x <<= 2;
	}
	if ((x & 0x80000000u) == 0){ // 1000 0000 0000 0000 0000 0000 0000 0000
		count += 1;
		x <<= 1;
	}
	return count;
}
size_t binary_shift_lhs_zeros_uint32(uint32_t * const x){
	size_t shift = binary_count_lhs_zeros_uint32(*x);
	(*x) <<= shift;
	return shift;
}


size_t binary_count_rhs_zeros_uint32(uint32_t x){
	size_t count = 0;
	if ((x & 0x0000FFFFu) == 0){ // 0000 0000 0000 0000 1111 1111 1111 1111
		count += 16;
		x >>= 16;
	}
	if ((x & 0x000000FFu) == 0){ // 0000 0000 0000 0000 0000 0000 1111 1111
		count += 8;
		x >>= 8;
	}
	if ((x & 0x0000000Fu) == 0){ // 0000 0000 0000 0000 0000 0000 0000 1111
		count += 4;
		x >>= 4;
	}
	if ((x & 0x00000003u) == 0){ // 0000 0000 0000 0000 0000 0000 0000 0011
		count += 2;
		x >>= 2;
	}
	if ((x & 0x00000001u) == 0){ // 0000 0000 0000 0000 0000 0000 0000 0001
		count += 1;
		x >>= 1;
	}
	return count;
}
size_t binary_shift_rhs_zeros_uint32(uint32_t * const x){
	size_t shift = binary_count_rhs_zeros_uint32(*x);
	//printf("binary_shift_rhs_zeros_uint32 :: shift %lu\n", shift);
	(*x) >>= shift;
	return shift;
}


float assemble_float(const int8_t sign, const uint32_t mantissa, const uint8_t exp_2){
	// sign - Sign of float (-1 or +1)
	// mantissa - 32-bit unsigned integer representation of bytes that should go in mantissa
	//            NOTE: should be aligned to LHS of bits
	// exp_2 - power of 2 exponent
	// RETURNS: float - assembled floating point number
	//printf("DEBUG :: assemble_float :: sign %d mantissa %u (0x%08X) exp2 %u\n", sign, mantissa, mantissa, exp_2);
	
	// TESTING
	//sign = 1;
	//           12345678
	//mantissa = 0x80000000u;
	//exp_2 = 127;
	
	union FloatMask{
		uint32_t u32;
		float f32;
	} float_mask = {0};
	// Floating point format:
	//      1     8          23
	//      S EEEEEEEE XXXXXXXXXXXXXXXXXXXXXXX
	// [sign] [exponent]  [1.xxxx]
	
	if (sign < 0){
		float_mask.u32 |= 0x80000000u;
	}
	//printf("DEBUG :: assemble_float :: float_mask 0x%08X float %E\n", float_mask.u32, float_mask.f32);
	float_mask.u32 |= ((uint32_t)(exp_2) << 23);
	//float_mask.u32 |= 0x00800000u;
	//printf("DEBUG :: assemble_float :: float_mask 0x%08X float %E\n", float_mask.u32, float_mask.f32);
	float_mask.u32 |= (mantissa >> 9);
	//float_mask |= ((mantissa<<1) >> 10);
	//printf("DEBUG :: assemble_float :: float_mask 0x%08X float %E\n", float_mask.u32, float_mask.f32);
	return float_mask.f32;
}


void exp_10_to_exp_2(int16_t exp_10, int16_t * const exp_2, uint64_t * const factor){
	
	const PowerOfTwoFactorEntry* p = power_of_two_factor_lut + (POWER_OF_TWO_FACTOR_LUT_ZERO_INDEX+exp_10);
	(*exp_2) = p->exp_2;
	(*factor) = p->factor;
	
	//printf("DEBUG :: exp_10_to_exp_2 :: exp_10 %d p.exp_10 %d exp_2 %d factor %lu\n", exp_10, p.exp_10, *exp_2, *factor);
}

size_t read_float32_sci_trans(char const* p, float * const x){
	// Quick and dirty method to convert scientific notation number to a float32 (with 1E20 factor to not bottom out when reading transition strengths)
	// Probably does not return exact IEEE floating point representation, but should be good enough
	const char * p0 = p;
	uint64_t mantissa_extended = 0;
	uint32_t mantissa = 0;
	uint64_t exp_factor = 0;
	int16_t exp_10 = 0;
	int16_t exp_2 = 0;
	int8_t mantissa_sign = 1;
	
	skip_whitespace(&p);
	
	// TESTING
	//printf("DEBUG :: \n");
	//char c = *(p+20);
	//(*((char*)p+20)) = '\0';
	//printf("DEBUG :: read_float32_sci_trans :: %s\n", p);
	//(*((char*)p+20)) = c;
	// END TESTING
	
	consume_sci_notation_by_parts(&p, &mantissa_sign, &mantissa, &exp_10);
	
	exp_10 += TRANS_STR_FLOAT32_EXP; // multiply by factor of 1E20 to avoid bottoming out float32 exponent when reading transition strengths
	
	// TESTING   NOTE: exp_factor is limiting size of exp_10, we don't have enough space to store 5^27 or so.
	//mantissa = 155;
	//exp_10 = 10;
	
	//printf("DEBUG :: read_float32_sci_trans :: mantissa_sign %d mantissa %d exp_10 %d\n", mantissa_sign, mantissa, exp_10);
	exp_10_to_exp_2(exp_10, &exp_2, &exp_factor);
	
	//printf("DEBUG :: read_float32_sci_trans :: exp_2 %d exp_factor %lu\n", exp_2, exp_factor);
	
	
	//printf("DEBUG :: read_float32_sci_trans :: mantissa %u (0x%08X)\n", mantissa, mantissa);
	exp_2 += binary_shift_rhs_zeros_uint32(&mantissa); // put any remaining factors of 2 into `exp_2`
	//printf("DEBUG :: read_float32_sci_trans :: mantissa %u (0x%08X) exp_2 %d\n", mantissa, mantissa, exp_2);
	
	//printf("DEBUG :: read_float32_sci_trans :: POSITIVE EXPONENT\n");
	mantissa_extended = mantissa;
	//printf("DEBUG :: read_float32_sci_trans :: mantissa_extended %lu (0x%016lX)\n", mantissa_extended, mantissa_extended);
	mantissa_extended *= exp_factor;
	//printf("DEBUG :: read_float32_sci_trans :: mantissa_extended %lu (0x%016lX)\n", mantissa_extended, mantissa_extended);
	
	exp_2 += binary_shift_uint64_to_uint32(&mantissa_extended);
	//printf("DEBUG :: read_float32_sci_trans :: mantissa_extended %lu (0x%016lX)\n", mantissa_extended, mantissa_extended);
	//printf("DEBUG :: read_float32_sci_trans :: exp_2 %d\n", exp_2);
	mantissa = mantissa_extended;
	
	
	//printf("DEBUG :: read_float32_sci_trans :: AFTER EXPONENT HANDLING\n");
	//printf("DEBUG :: read_float32_sci_trans :: mantissa %u (0x%08X) exp_2 %d\n", mantissa, mantissa, exp_2);
	exp_2 += 31;
	//printf("DEBUG :: read_float32_sci_trans :: mantissa %u (0x%08X)\n", mantissa, mantissa);
	
	mantissa <<= 1;
	
	(*x) = assemble_float(mantissa_sign, mantissa, (uint8_t)(exp_2+127));
	//printf("DEBUG :: read_float32_sci_trans :: (*x) %E\n", *x);
	
	//printf("DEBUG :: read_float32_sci_trans :: (p-p0) %ld\n", (p-p0));
	
	
	//exit(1); // TESTING
	return (p-p0);
}

size_t read_float32_sci(char const* p, float * const x){
	// Quick and dirty method to convert scientific notation number to a float32 (DOES NOT INCLUDE ANY MULTIPLYING FACTORS)
	// Probably does not return exact IEEE floating point representation, but should be good enough
	const char * p0 = p;
	uint64_t mantissa_extended = 0;
	uint32_t mantissa = 0;
	uint64_t exp_factor = 0;
	int16_t exp_10 = 0;
	int16_t exp_2 = 0;
	int8_t mantissa_sign = 1;
	
	skip_whitespace(&p);
	
	consume_sci_notation_by_parts(&p, &mantissa_sign, &mantissa, &exp_10);
	exp_10_to_exp_2(exp_10, &exp_2, &exp_factor);
	exp_2 += binary_shift_rhs_zeros_uint32(&mantissa); // put any remaining factors of 2 into `exp_2`

	mantissa_extended = mantissa;
	mantissa_extended *= exp_factor;
	exp_2 += binary_shift_uint64_to_uint32(&mantissa_extended);
	mantissa = mantissa_extended;
	exp_2 += 31;
	mantissa <<= 1;
	
	(*x) = assemble_float(mantissa_sign, mantissa, (uint8_t)(exp_2+127));
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
	//printf("n_bytes_consumed %d\n", n_bytes_consumed);
	n_bytes_consumed += read_uint32(buffer+n_bytes_consumed, &(TRANS_ENTRY.hi));
	//printf("n_bytes_consumed %d\n", n_bytes_consumed);
	//double tempf; n_bytes_consumed += read_float64(buffer+n_bytes_consumed, &tempf); tempf*=TRANS_STR_FLOAT32_FACTOR; TRANS_ENTRY.value=tempf;
	n_bytes_consumed += read_float32_sci_trans(buffer+n_bytes_consumed, &(TRANS_ENTRY.value));
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
	n_bytes_consumed += read_uint32(buffer+n_bytes_consumed, &(TRANS_ENTRY.lo));
	n_bytes_consumed += read_uint32(buffer+n_bytes_consumed, &(TRANS_ENTRY.hi));
	//n_bytes_consumed += read_float64(buffer+n_bytes_consumed, &(TRANS_ENTRY.value));
	//double tempf; n_bytes_consumed += read_float64(buffer+n_bytes_consumed, &tempf); tempf*=TRANS_STR_FLOAT32_FACTOR; TRANS_ENTRY.value=tempf;
	n_bytes_consumed += read_float32_sci_trans(buffer+n_bytes_consumed, &(TRANS_ENTRY.value));
	//n_bytes_consumed += read_float64(buffer+n_bytes_consumed, &(TRANS_ENTRY.wavenumber));
	n_bytes_consumed += read_float32_sci(buffer+n_bytes_consumed, &(TRANS_ENTRY.wavenumber));
	
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
			++i;
			//printf("INNER: %ld %ld\n", rp, i);
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