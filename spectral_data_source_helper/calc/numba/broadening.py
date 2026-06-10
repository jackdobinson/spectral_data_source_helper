


import numpy as np
from numba import njit, prange

from ..numba import PARALLEL

@njit(parallel=PARALLEL)
def assign_broadening_parameters(
	trans_states_chunk_bytes : np.ndarray, #[N_trans, N_bytes]
	broad_array_bytes : np.ndarray, #[N_broad_for_gas, N_bytes]
	broad_comp_mask : np.ndarray, #[N_broad_for_gas, N_bytes]
	broad_value_0 : np.ndarray, #[N_broad_for_gas]
	broad_value_1 : np.ndarray, #[N_broad_for_gas]
	source_id : int,
	fallback_broad_val_0 :float,
	fallback_broad_val_1 :float,
	fallback_source_id : int,
	out_line_data_chunk_broad_param_0 : np.ndarray, #[N_trans]
	out_line_data_chunk_broad_param_1 : np.ndarray, #[N_trans]
	out_line_data_chunk_broad_source : np.ndarray, #[N_trans]
):

	n_trans = trans_states_chunk_bytes.shape[0]
	n_broad_for_gas = broad_array_bytes.shape[0]
	n_bytes = broad_array_bytes.shape[1]
	#n_broad_vals = broad_values.shape[1]
	
	for i in prange(n_trans):
		was_set = False
		for j in range(n_broad_for_gas):
			any_comparison_performed = False
			all_selected_bytes_equal = True
			for k in range(n_bytes):
				if broad_comp_mask[j,k]:
					#print(f'{i=} {j=} {k=}')
					#print(f'{trans_states_chunk_bytes[i,k]=}')
					#print(f'{broad_array_bytes[j,k]=}')
					#print(f'{trans_states_chunk_bytes[i,k] == broad_array_bytes[j,k]=}')
					#z = trans_states_chunk_bytes[i,k] != broad_array_bytes[j,k]
					#print(f'{z=}')
					if trans_states_chunk_bytes[i,k] != broad_array_bytes[j,k]:
						#print('FAIL', flush=True)
						all_selected_bytes_equal = False
						break
					any_comparison_performed = True
			#print(f'{all_selected_bytes_equal=}')
			#print(f'{any_comparison_performed=}')
			
			if any_comparison_performed and all_selected_bytes_equal:
				out_line_data_chunk_broad_param_0[i] = broad_value_0[j]
				out_line_data_chunk_broad_param_1[i] = broad_value_1[j]
				out_line_data_chunk_broad_source[i] = source_id
				was_set = True
				break
		if not was_set:
			out_line_data_chunk_broad_param_0[i] = fallback_broad_val_0
			out_line_data_chunk_broad_param_1[i] = fallback_broad_val_1
			out_line_data_chunk_broad_source[i] = fallback_source_id
				
				