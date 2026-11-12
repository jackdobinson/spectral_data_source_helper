
import numpy as np
from numba import njit, prange

from ..numba import PARALLEL

#PARALLEL = True
#PARALLEL = False

@njit(parallel=PARALLEL)
def transition_states_populate_state(
		state : np.ndarray, # <int|float>[N_states]
		trans_lower_id : np.ndarray, # int[N_trans]
		trans_upper_id : np.ndarray, # int[N_trans]
		
		out_lower_state : np.ndarray, # <int|float>[N_trans]
		out_upper_state : np.ndarray, # <int|float>[N_trans]
):
	for i in prange(trans_lower_id.shape[0]):
		out_lower_state[i] = state[trans_lower_id[i] - 1] # state ID numbers are 1-based, so convert to 0-based indexes
		out_upper_state[i] = state[trans_upper_id[i] - 1]

@njit(parallel=PARALLEL)
def transition_states_populate_m_and_abs_m(
		state_qn_J : np.ndarray, # <int|float>[N_states]
		trans_final_id : np.ndarray, # J"  int[N_trans]
		trans_initial_id : np.ndarray, # J'  int[N_trans]
		
		out_m : np.ndarray, # m float[N_trans]
		out_abs_m : np.ndarray, # m float[N_trans]
):
	trans_final_idx : int = -1
	trans_initial_idx : int = -1
	for i in prange(trans_final_id.shape[0]):
		trans_final_idx = trans_final_id[i] - 1 # state ID numbers are 1-based, so convert to 0-based indexes
		trans_initial_idx = trans_initial_id[i] - 1
		
		delta_J = state_qn_J[trans_final_idx] - state_qn_J[trans_initial_idx]
		if delta_J == -1:
			# m = -J"
			out_m[i] = -1*state_qn_J[trans_final_idx]
			out_abs_m[i] = state_qn_J[trans_final_idx]
		elif delta_J == 0:
			# m = J"
			out_m[i] = state_qn_J[trans_final_idx]
			out_abs_m[i] = state_qn_J[trans_final_idx]
		elif delta_J == 1:
			# m == J"+1
			out_m[i] = state_qn_J[trans_final_idx] + 1
			out_abs_m[i] = state_qn_J[trans_final_idx] + 1
		else:
			out_m[i] = np.nan
			out_abs_m[i] = np.nan


@njit(parallel=PARALLEL)
def transition_states_einstein_A_and_wavenumber(
		trans_einstein_A : np.ndarray,
		trans_Ep : np.ndarray,
		trans_Epp : np.ndarray,
		
		# trans_state_chunk
		out_einstein_A : np.ndarray,
		out_wavenumber : np.ndarray,
):
	for i in prange(trans_einstein_A.shape[0]):
		out_einstein_A[i] = trans_einstein_A[i]
		out_wavenumber[i] = trans_Ep[i] - trans_Epp[i]