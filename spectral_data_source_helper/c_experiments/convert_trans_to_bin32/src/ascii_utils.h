#ifndef __ASCII_UTILS__INCLUDED__
#define __ASCII_UTILS__INCLUDED__

#include <stdint.h>
#include <stdlib.h>
#include <stdbool.h>
#include <stdio.h>
#include <ctype.h>

extern const size_t MAX_CHUNK_SIZE; // bytes, try to match to cache size

typedef bool (*CharFilterFn)(const char);

bool ascii_is_newline(const char c);
bool ascii_is_space(const char c);
size_t ascii_skip_whitespace(char const* const p);
int ascii_count_cols_in_file_filters(
	FILE* f, 
	CharFilterFn is_col_separator_char_fn, 
	CharFilterFn is_cols_end_char
);
int ascii_count_cols_in_file(FILE* f);
size_t ascii_read_float32(char const* p, float * const x);
size_t ascii_read_float32_fast(char const* p, float * const x);
size_t ascii_read_float32_fast_offset(char const* p, float * const x, const int16_t exp_10_offset);
size_t ascii_read_float64(char const* p, double * const x);
size_t ascii_read_direct_uint32(char const* p, uint32_t * const x);
size_t ascii_read_uint32(char const* p, uint32_t * const x);
size_t ascii_read_direct_decimal_uint32(char const* p, uint32_t * const x);
size_t ascii_read_direct_int32(char const* p, uint32_t * const x);
size_t ascii_read_direct_uint16(char const* p, uint16_t * const x);
size_t ascii_read_direct_int16(char const* p, int16_t * const x);
void ascii_consume_whitespace(char const** const p);
void ascii_consume_sign(char const**const p, int8_t * const sign);
bool ascii_consume_int16_unsafe(char const ** const p, int16_t *const x);
bool ascii_consume_int16(char const ** const p, int16_t *const x);
bool ascii_consume_exponent(char const ** const p, int16_t *const exponent);
bool ascii_consume_uint32_unsafe(char const ** const p, uint32_t *const x);
bool ascii_consume_uint32(char const ** const p, uint32_t *const x);
bool ascii_consume_decimal_as_uint32(char const ** const p, uint32_t * const x, int16_t * const exp_10);
bool ascii_consume_sci_notation_by_parts(char const ** const p, int8_t *const sign, uint32_t * const x, int16_t * const exp_10);
float XX__ascii_assemble_float32(const int8_t sign, const uint32_t mantissa, const uint8_t exp_2);
void XX__ascii_exp_10_to_exp_2(int16_t exp_10, int16_t * const exp_2, uint64_t * const factor);

#endif // __ASCII_UTILS__INCLUDED__