

#include "binary_utils.h"

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
