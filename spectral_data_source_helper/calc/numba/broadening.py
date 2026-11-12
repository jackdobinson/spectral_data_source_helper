


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
	"""
		Check each transition against each *.broad file entry, use the first entry that matches
	"""
	
	n_trans = trans_states_chunk_bytes.shape[0]
	n_broad_for_gas = broad_array_bytes.shape[0]
	n_bytes = broad_array_bytes.shape[1]
	#n_broad_vals = broad_values.shape[1]
	
	for i in prange(n_trans): # Loop over the transitions
		#print(f'{i=}')
		matching_broad_entry_idx = -1
		for j in range(n_broad_for_gas): # Loop over the *.broad entries, each transition checks against every entry
			#print(f'  {j=}')
			any_comparison_performed = False # Only select broadening parameters if we have performed comparisons
			all_selected_bytes_equal = True # Only select broadening parameters if transition matches all values of entry. Stop as soon as a non-matching entry is found.
			for k in range(n_bytes):
				#print(f'    {i=} {j=} {k=} {broad_comp_mask[j,k]=}')
				if broad_comp_mask[j,k]: # Only compare if `broad_comp_mask` tells us to make a comparison
					
					#print(f'      {trans_states_chunk_bytes[i,k]=}')
					#print(f'      {broad_array_bytes[j,k]=}')
					#print(f'      {trans_states_chunk_bytes[i,k] == broad_array_bytes[j,k]=}')
					
					any_comparison_performed = True
					if trans_states_chunk_bytes[i,k] != broad_array_bytes[j,k]: # Break out of loop on the first failure, we only select entries where all `broad_comp_mask` comparisons are successful
						#print('      FAIL', flush=True)
						all_selected_bytes_equal = False
						break
			#print(f'  {all_selected_bytes_equal=}')
			#print(f'  {any_comparison_performed=}')
			
			if any_comparison_performed and all_selected_bytes_equal: # If we have done comparisons, and a match is found then set broadening paramters for this transition and move onto the next one.
				out_line_data_chunk_broad_param_0[i] = broad_value_0[j]
				out_line_data_chunk_broad_param_1[i] = broad_value_1[j]
				out_line_data_chunk_broad_source[i] = source_id
				matching_broad_entry_idx = j
				break
		
		if matching_broad_entry_idx == -1: # If no broadening parameters were set for this transition, use the fallback values.
			out_line_data_chunk_broad_param_0[i] = fallback_broad_val_0
			out_line_data_chunk_broad_param_1[i] = fallback_broad_val_1
			out_line_data_chunk_broad_source[i] = fallback_source_id
			
		#print(f'{i=} BROAD: idx={matching_broad_entry_idx} source={out_line_data_chunk_broad_source[i]} param_0={out_line_data_chunk_broad_param_0[i]} param_1={out_line_data_chunk_broad_param_1[i]}')
