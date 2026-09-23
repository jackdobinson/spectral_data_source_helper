

#include <errno.h>
#include "ascii_utils.h"
#include "power_of_two_factor_lut.h"
#include "binary_utils.h"


bool ascii_is_newline(const char c){
	return c == '\n';
}

bool ascii_is_space(const char c){
	return (isspace((int)c) != 0);
}

size_t ascii_skip_whitespace(char const * p){
	size_t i=0;
	while (isspace(*p)){
		++p;
		++i;
	}
	return i;
}



int ascii_count_cols_in_file_filters(
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

int ascii_count_cols_in_file(FILE* f){
	return ascii_count_cols_in_file_filters(f, ascii_is_space, ascii_is_newline);
}

size_t ascii_read_float32(char const* p, float * const x){
	char* q = (char*)p;
	*x = strtof(p,&q);
	return (q-p);
}


size_t ascii_read_float32_fast(char const* p, float * const x){
	return ascii_read_float32_fast_offset(p, x, 0);
}

size_t ascii_read_float32_fast_offset(char const* p, float * const x, const int16_t exp_10_offset){
	// Quick and dirty method to convert scientific notation number to a float32 (`exp_10_offset` is used to adjust number exponent so it is within correct range for float32)
	// Probably does not return exact IEEE floating point representation, but should be good enough
	const char * p0 = p;
	uint64_t mantissa_extended = 0;
	uint32_t mantissa = 0;
	uint64_t exp_factor = 0;
	int16_t exp_10 = 0;
	int16_t exp_2 = 0;
	int8_t mantissa_sign = 1;
	
	ascii_consume_whitespace(&p);
	
	if (!ascii_consume_sci_notation_by_parts(&p, &mantissa_sign, &mantissa, &exp_10)){ // if something went wrong when reading sci notation, set value to NAN and set errno
		(*x) = XX__ascii_assemble_float32(mantissa_sign, (uint32_t)(0x80000200u), (uint8_t)(0xFF)); // S 11111111 10000000000000000000001 is signalling NaN (S - Sign)
		errno = EDOM; // domain invaid (i.e. cannot convert to float)
		return (p-p0);
	}
	//printf("ascii_read_float32_fast_offset :: mantissa_sign %d mantissa %d exp_10 %d\n", mantissa_sign, mantissa, exp_10);
	
	if ((mantissa & 0xFFFFFFFFu) == 0){ // If value is identically zero (e.g. 0.00000E12)
		(*x) = XX__ascii_assemble_float32(mantissa_sign, (uint32_t)(0x00000000u), (uint8_t)(0x00)); // S 00000000 00000000000000000000000 is +/- zero (S - Sign)
		return (p-p0);
	}
	
	exp_10 += exp_10_offset; // Add exponent offset here, used to fit very large or small numbers into float32 representation
	
	//printf("ascii_read_float32_fast_offset ::exp_10 %d\n", exp_10);
	
	
	XX__ascii_exp_10_to_exp_2(exp_10, &exp_2, &exp_factor);
	//printf("ascii_read_float32_fast_offset :: exp_2 %d exp_factor %lu\n", exp_2, exp_factor);
	
	exp_2 += binary_shift_rhs_zeros_uint32(&mantissa); // put any remaining factors of 2 into `exp_2`
	//printf("ascii_read_float32_fast_offset :: exp_2 %d mantissa %u\n", exp_2, mantissa);
	
	mantissa_extended = mantissa;
	//printf("ascii_read_float32_fast_offset :: mantissa_extended %lu\n", mantissa_extended);
	mantissa_extended *= exp_factor;
	//printf("ascii_read_float32_fast_offset :: mantissa_extended %lu\n", mantissa_extended);
	exp_2 += binary_shift_uint64_to_uint32(&mantissa_extended);
	//printf("ascii_read_float32_fast_offset :: mantissa_extended %lu exp_2 %d\n", mantissa_extended, exp_2);
	mantissa = mantissa_extended;
	exp_2 += 31;
	//printf("ascii_read_float32_fast_offset :: exp_2 %d mantissa %u\n", exp_2, mantissa);
	mantissa <<= 1;
	
	
	exp_2 += 127; // zero-point of float32 exponent is 127
	//printf("ascii_read_float32_fast_offset :: exp_2 %d mantissa %u\n", exp_2, mantissa);
	
	if (exp_2 > 255) {
		//printf("ascii_read_float32_fast_offset :: mantissa_sign %d mantissa %u exp_10 %d exp_2 %d mantissa_extended %lu\n", mantissa_sign, mantissa, exp_10, exp_2, mantissa_extended);
		(*x) = XX__ascii_assemble_float32(mantissa_sign, (uint32_t)(0x00000000u), (uint8_t)(0xFF)); // S 11111111 00000000000000000000000 is +/- infinity (S - Sign)
		//errno = EDOM; // domain invaid (i.e. cannot convert to float)
		return (p-p0);
	}
	else if (exp_2 < 0){
		exp_2 = 0;
	}
	
	(*x) = XX__ascii_assemble_float32(mantissa_sign, mantissa, (uint8_t)(exp_2));
	
	//printf("ascii_read_float32_fast_offset :: x %E\n", *x);
	
	//exit(1);
	return (p-p0);
}


size_t ascii_read_float64(char const* p, double * const x){
	char* q = (char*)p;
	*x = strtod(p,&q);
	return (q-p);
}

size_t ascii_read_direct_uint32(char const* p, uint32_t * const x){
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

size_t ascii_read_uint32(char const* p, uint32_t * const x){
	const char* p0 = p;
	while (isspace(*p)){
		++p;
	}
	
	return (p-p0) + ascii_read_direct_uint32(p, x);
}

size_t ascii_read_direct_decimal_uint32(char const* p, uint32_t * const x){
	const char* p0 = p;
	uint32_t exp = 1<<31; // 0001 -> 1000
	uint32_t pos = 0;
	uint32_t rem = 0;
	uint32_t pow = 10;
	uint32_t a=0;
	uint32_t y = 0;
	bool y_valid = true;
	
	(*x) = 0;
	
	//printf("*p %c\n", *p);
	
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

size_t ascii_read_direct_int32(char const* p, uint32_t * const x){
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

size_t ascii_read_direct_uint16(char const* p, uint16_t * const x){
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

size_t ascii_read_direct_int16(char const* p, int16_t * const x){
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

void ascii_consume_whitespace(char const** const p){
	while (isspace(**p)){
		++(*p);
	}
}

void ascii_consume_sign(char const**const p, int8_t * const sign){
	// NOTE: If not sign to consume, *p is not advanced
	(*sign) = 1 - 2*((**p) == '-');
	(*p)+=(((*sign)==-1)|((**p) == '+'));
} 

bool ascii_consume_int16_unsafe(char const ** const p, int16_t *const x){
	// Consumes number as far as it can, stops when non numeral is reached, return value indicates if any numeral was consumed or not.
	//
	// RETURNS: bool - `true` if a number was consumed, `false` otherwise
	// AGUMENTS:
	// p - double pointer to input characters
	// x - pointer to variable to fill with value.
	int8_t sign;
	int8_t y = 0;
	
	ascii_consume_sign(p, &sign);
	
	y = (**p) - '0';
	if ((y >= 0) && (y<10)){
		(*x) = 10*(*x) + y;
		++(*p);
		y = (**p) - '0';
	} else{
		return false;
	}
	while ((y >= 0) && (y<10)){
		(*x) = 10*(*x) + y;
		++(*p);
		y = (**p) - '0';
	}
	(*x) *= sign;
	
	return true;
}

bool ascii_consume_int16(char const ** const p, int16_t *const x){
	// Consumes number as far as it can, stops when non numeral is reached, return value indicates if any numeral was consumed or not.
	//
	// RETURNS: bool - `true` if a number was consumed, `false` otherwise
	// AGUMENTS:
	// p - double pointer to input characters
	// x - pointer to variable to fill with value.
	(*x) = 0;
	return ascii_consume_int16_unsafe(p, x);
}

bool ascii_consume_exponent(char const ** const p, int16_t *const exponent){
	// Consumes exponent as far as it can, expects either no exponent or one of 'EeDd' followed by numeral. Stops when non numeral is reached, return value indicates if any numeral was consumed or not.
	//
	// RETURNS: bool - `true` if exponent was consumed or not present, `false` otherwise
	// AGUMENTS:
	// p - double pointer to input characters
	// x - pointer to variable to fill with value.
	if ( ((**p) == 'E') | ((**p) == 'e') | ((**p) == 'D') | ((**p) == 'd') ){
		++(*p);
		return ascii_consume_int16(p, exponent);
	}
	return true;
}

bool ascii_consume_uint32_unsafe(char const ** const p, uint32_t *const x){
	// Consumes number as far as it can, stops when non numeral is reached, return value indicates if any numeral was consumed or not.
	//
	// RETURNS: bool - `true` if a number was consumed, `false` otherwise
	// AGUMENTS:
	// p - double pointer to input characters
	// x - pointer to variable to fill with value.
	// NOTE: Does not zero `x` before consuming number
	int8_t y = 0;
	y = (**p) - '0';
	if ((y >= 0) && (y<10)){
		(*x) = 10*(*x) + y;
		++(*p);
		y = (**p) - '0';
	} else {
		return false;
	}
	while ((y >= 0) && (y<10)){
		(*x) = 10*(*x) + y;
		++(*p);
		y = (**p) - '0';
	}
	
	return true;
}

bool ascii_consume_uint32(char const ** const p, uint32_t *const x){
	// Consumes number as far as it can, stops when non numeral is reached, return value indicates if any numeral was consumed or not.
	//
	// RETURNS: bool - `true` if a number was consumed, `false` otherwise
	// AGUMENTS:
	// p - double pointer to input characters
	// x - pointer to variable to fill with value.
	(*x) = 0;
	return ascii_consume_uint32_unsafe(p,x);
}

bool ascii_consume_decimal_as_uint32(char const ** const p, uint32_t * const x, int16_t * const exp_10){
	// Consumes number as far as it can, stops when non numeral is reached, return value indicates if any numeral was consumed or not.
	//
	// RETURNS: bool - `true` if a number was consumed, `false` otherwise
	// AGUMENTS:
	// p - double pointer to input characters
	// x - pointer to variable to fill with value.
	// exp_10 - pointer to variable to fill with power of 10 offset
	
	bool result = true;
	
	(*x) = 0;
	(*exp_10) = 0;
	
	//printf("DEBUG :: consume_decimal_as_uint32 :: **p '%c'\n", **p);
	result &= ascii_consume_uint32_unsafe(p, x);
	//if (!result){
	//	printf("ascii_consume_decimal_as_uint32 :: ERROR FIRST PART :: %s\n", (*p));
	//}
	//printf("DEBUG :: consume_decimal_as_uint32 :: x %u\n", *x);
	//printf("DEBUG :: consume_decimal_as_uint32 :: **p '%c'\n", **p);
	
	if ((**p) == '.'){ // decimal point detected
		++(*p);
		const char* p0 = *p;
		ascii_consume_uint32_unsafe(p, x);
		//printf("DEBUG :: consume_decimal_as_uint32 :: x %u\n", *x);
		(*exp_10) = (p0 - (*p));
	}
	
	return result;
}

bool ascii_consume_sci_notation_by_parts(char const ** const p, int8_t *const sign, uint32_t * const x, int16_t * const exp_10){
	bool result=true;
	int16_t decimal_exp_10 = 0;
	int16_t exponent_exp_10 = 0;
	
	ascii_consume_sign(p, sign);
	//printf("DEBUG :: consume_sci_notation_by_parts :: sign %d\n", *sign);
	result &= ascii_consume_decimal_as_uint32(p, x, &decimal_exp_10);
	
	//if (!result){
	//	printf("ascii_consume_sci_notation_by_parts :: ERROR DECIMAL :: %s\n", (*p)-16);
	//}
	//printf("DEBUG :: consume_sci_notation_by_parts :: x %u decimal_exp_10 %d\n", *x, decimal_exp_10);
	result &= ascii_consume_exponent(p, &exponent_exp_10);
	//if (!result){
	//	printf("ascii_consume_sci_notation_by_parts :: ERROR EXPONENT :: %s\n", (*p)-16);
	//}
	
	//printf("DEBUG :: consume_sci_notation_by_parts :: exponent_exp_10 %d\n", exponent_exp_10);
	(*exp_10) = decimal_exp_10 + exponent_exp_10;
	
	return result;
}

float XX__ascii_assemble_float32(const int8_t sign, const uint32_t mantissa, const uint8_t exp_2){
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

void XX__ascii_exp_10_to_exp_2(int16_t exp_10, int16_t * const exp_2, uint64_t * const factor){
	
	const PowerOfTwoFactorEntry* p = power_of_two_factor_lut + (POWER_OF_TWO_FACTOR_LUT_ZERO_INDEX+exp_10);
	(*exp_2) = p->exp_2;
	(*factor) = p->factor;
	
	//printf("DEBUG :: exp_10_to_exp_2 :: exp_10 %d p.exp_10 %d exp_2 %d factor %lu\n", exp_10, p.exp_10, *exp_2, *factor);
}


