


import numpy as np
from numba import njit, prange
#from numba.types import void, bool_, int_

PARALLEL = True
#PARALLEL = False


@njit(parallel=PARALLEL)
def add(
	a : np.ndarray,
	b : np.ndarray,
	out : np.ndarray
):
	for i in prange(out.shape[0]):
		out[i] = a[i] + b[i]

@njit(parallel=PARALLEL)
def multiply(
	a : np.ndarray,
	b : np.ndarray,
	out : np.ndarray
):
	for i in prange(out.shape[0]):
		out[i] = a[i] * b[i]

@njit(parallel=PARALLEL)
def multiply_s(
	a : np.ndarray,
	b : float,
	out : np.ndarray
):
	for i in prange(out.shape[0]):
		out[i] = a[i] * b

@njit(parallel=PARALLEL)
def multiply_j_2d(
	a : np.ndarray,
	b : np.ndarray,
	out : np.ndarray
):
	for i in prange(out.shape[1]):
		for j in range(out.shape[0]):
			out[j,i] = a[j,i] * b[j,i]

@njit(parallel=PARALLEL)
def multiply_j_1d(
	a : np.ndarray,
	b : np.ndarray,
	out : np.ndarray
):
	for i in prange(out.shape[1]):
		for j in range(out.shape[0]):
			out[j,i] = a[j,i] * b[j]

@njit(parallel=PARALLEL)
def multiply_1d_j(
	a : np.ndarray,
	b : np.ndarray,
	out : np.ndarray
):
	for i in prange(out.shape[1]):
		for j in range(out.shape[0]):
			out[j,i] = a[j,i] * b[i]

@njit(parallel=PARALLEL)
def divide(
	a : np.ndarray,
	b : np.ndarray,
	out : np.ndarray
):
	for i in prange(out.shape[0]):
		out[i] = a[i] / b[i]

@njit(parallel=PARALLEL)
def divide_s(
	a : np.ndarray,
	b : float,
	out : np.ndarray
):
	for i in prange(out.shape[0]):
		out[i] = a[i] / b

@njit(parallel=PARALLEL)
def divide_2d_1d(
	a : np.ndarray,
	b : np.ndarray,
	out : np.ndarray
):
	for i in prange(out.shape[1]):
		for j in prange(out.shape[0]):
			out[j,i] = a[j,i] / b[i]

@njit(parallel=PARALLEL)
def subtract(
	a : np.ndarray,
	b : np.ndarray,
	out : np.ndarray
):
	for i in prange(out.shape[0]):
		out[i] = a[i] - b[i]

@njit(parallel=PARALLEL)
def set_s(
	source : float,
	out : np.ndarray
):
	for i in prange(out.shape[0]):
		out[i] = source

@njit(parallel=PARALLEL)
def set_where(
	source : np.ndarray,
	mask : np.ndarray,
	out : np.ndarray
):
	for i in prange(out.shape[0]):
		if mask[i]:
			out[i] = source[i]

@njit(parallel=PARALLEL)
def set_where_scalar(
	value,
	mask : np.ndarray,
	out : np.ndarray
):
	for i in prange(out.shape[0]):
		if mask[i]:
			out[i] = value

#@njit(void(int_[:],int_[:],bool_[:]), parallel=PARALLEL)
@njit(parallel=PARALLEL)
def is_eq(
	a : np.ndarray,
	b : np.ndarray,
	out : np.ndarray,
):
	for i in prange(out.shape[0]):
		out[i] = (a[i] == b[i])

@njit(parallel=PARALLEL)
def is_eq_s(
	a : np.ndarray,
	b : int | float,
	out : np.ndarray,
):
	for i in prange(out.shape[0]):
		out[i] = (a[i] == b)

@njit(parallel=PARALLEL)
def is_neq(
	a : np.ndarray,
	b : np.ndarray,
	out : np.ndarray,
):
	for i in prange(out.shape[0]):
		out[i] = a[i] != b[i]

@njit(parallel=PARALLEL)
def is_gt_2d_0d(
	a : np.ndarray,
	b,
	out : np.ndarray,
):
	for i in prange(out.shape[1]):
		for j in range(out.shape[0]):
			out[j,i] = a[j,i] > b


@njit(parallel=PARALLEL)
def logical_and(
	a : np.ndarray,
	b : np.ndarray,
	out : np.ndarray,
):
	for i in prange(out.shape[0]):
		out[i] = a[i] & b[i]

@njit(parallel=PARALLEL)
def logical_not(
	a : np.ndarray,
	out : np.ndarray,
):
	for i in prange(out.shape[0]):
		out[i] = ~a[i]

@njit(parallel=PARALLEL)
def logical_not_2d(
	a : np.ndarray,
	out : np.ndarray,
):
	for i in prange(out.shape[1]):
		for j in range(out.shape[0]):
			out[j,i] = ~a[j,i]

@njit(parallel=PARALLEL)
def logical_or(
	a : np.ndarray,
	b : np.ndarray,
	out : np.ndarray,
):
	for i in prange(out.shape[0]):
		out[i] = (a[i] | b[i])


@njit(parallel=PARALLEL)
def count_true_1d(
	a : np.ndarray,
) -> int:
	sum = 0
	for i in prange(a.shape[0]):
		if a[i]:
			sum += 1
	return sum

@njit(parallel=False)
def count_true_2d_to_1d(
	a : np.ndarray, #[N,M],
	out_count : np.ndarray, #[N]
):
	for j in range(a.shape[0]):
		out_count[j] = count_true_1d(a[j])
	

@njit(parallel=PARALLEL)
def fill(
	a : np.ndarray,
	value
):
	for i in prange(a.shape[0]):
		a[i] = value

@njit(parallel=PARALLEL)
def copy(
	source : np.ndarray,
	dest : np.ndarray,
):
	for i in prange(dest.shape[0]):
		dest[i] = source[i]


@njit(parallel=PARALLEL)
def copy_pair_if_value_then_const(
	source1 : np.ndarray,
	source2 : np.ndarray,
	dest1 : np.ndarray,
	dest2 : np.ndarray,
	source_1_comp_value : float = 0,
	dest_1_const : float = 1,
	dest_2_const : float = 0,
):
	for i in prange(dest1.shape[0]):
		if source1[i] == source_1_comp_value:
			dest1[i] = dest_1_const
			dest2[i] = dest_2_const
		else:
			dest1[i] = source1[i]
			dest2[i] = source2[i]


@njit(parallel=False)
def idx_gt_s(
	bin_edges : np.ndarray, #[N_bins+1]
	value : float,
	idx_min : int,
	idx_max : int,
) -> int:
	"""
	Find index in `bin_edges` that is greater than `value` and between `idx_min` and `idx_max`.
	I.e. `out_inde` is the index that `value` would be storted to in `bin_edges`
	"""
	while idx_min != idx_max:
		x1 = (idx_min + idx_max) // 2
		if bin_edges[x1] < value:
			idx_min = x1 + 1
		else:
			idx_max = x1
	
	return idx_min

@njit(parallel=False)
def lin_interp_s(
	x : np.ndarray, #[N_in]
	y : np.ndarray, #[N_in]
	at_x : float,
) -> float:
	if at_x >= x[-1]:
		return y[-1]
	if at_x <= x[0]:
		return y[0]
		
	i = idx_gt_s(x,at_x,0,x.shape[0])
	
	x0 = x[i-1]
	x1 = x[i]
	y0 = y[i-1]
	y1 = y[i]
	dx = x1 - x0
	dy = y1 - y0
	dp = x1 - at_x
	
	return (dp/dx)*dy + y0

@njit(parallel=PARALLEL)
def lin_interp_v(
	x : np.ndarray, #[N_in]
	y : np.ndarray, #[N_in]
	at_x : np.ndarray, #[N_out]
	out : np.ndarray, #[N_out]
):
	for j in prange(at_x.shape[0]):
		out[j] = lin_interp_s(x,y,at_x[j])


@njit(parallel=True)
def get_valid_bin_indices_at_mask(
	bin_edges : np.ndarray, #[N_bins+1]
	values : np.ndarray, #[N_values]
	in_out_valid_mask : np.ndarray, #[N_values] bool
	out_indices : np.ndarray, #[N_values] integer
) -> int: # return number of valid indices
	"""
	Find indices in `bin_edges` that are greater than elements in `values` where `valid_mask` is true.
	I.e. `out_indices` is the index that elements of `values` would be storted to in `bin_edges`
	"""
	n_valid_idxs = 0
	idx_min = 0
	idx_max = bin_edges.shape[0]
	for i in prange(values.shape[0]):
		if not in_out_valid_mask[i]:
			out_indices[i] = -1
			continue
		
		x1 = idx_gt_s(bin_edges, values[i], idx_min, idx_max)
		
		#print(f'{i=} {x1=}')
		if (idx_min < x1) and (x1 < idx_max):
			#print('VALID')
			out_indices[i] = x1-1
			n_valid_idxs += 0
			in_out_valid_mask[i] = True
		else:
			#print('INVALID')
			in_out_valid_mask[i] = False
	return n_valid_idxs


# NOTE: THIS DOES NOT WORK YET, HAS AN INFINITE LOOP
@njit(parallel=False)
def get_valid_bin_indices_of_sets(
	bin_edges : np.ndarray, #[N_bins+1]
	values : np.ndarray, #[N_values]
	valid_mask : np.ndarray, #[N_sets, N_values] bool
	out_indices : np.ndarray, #[N_sets, N_values] integer
	out_n_indices : np.ndarray, #[N_sets] int
):
	for j in range(valid_mask.shape[0]):
		out_n_indices[j] = get_valid_bin_indices_at_mask(bin_edges, values, valid_mask[j], out_indices[j])