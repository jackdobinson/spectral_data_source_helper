#ifndef __BINARY_UTILS__INCLUDED__
#define __BINARY_UTILS__INCLUDED__

#include <stdint.h>
#include <stddef.h>

size_t binary_count_lhs_zeros_uint64(uint64_t x);
size_t binary_shift_lhs_zeros_uint64(uint64_t * const x);
size_t binary_count_rhs_zeros_uint64(uint64_t x);
size_t binary_shift_rhs_zeros_uint64(uint64_t * const x);
size_t binary_count_lhs_zeros_uint32(uint32_t x);
size_t binary_shift_lhs_zeros_uint32(uint32_t * const x);
size_t binary_count_rhs_zeros_uint32(uint32_t x);
size_t binary_shift_rhs_zeros_uint32(uint32_t * const x);
int binary_shift_uint64_to_uint32(uint64_t * const x);


#endif // __BINARY_UTILS__INCLUDED__