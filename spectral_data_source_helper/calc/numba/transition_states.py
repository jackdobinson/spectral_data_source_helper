
import numpy as np
from numba import njit, prange

from ..numba import PARALLEL

#PARALLEL = True
#PARALLEL = False

@njit(parallel=PARALLEL)
def transition_states_populate_state(
		state : np.ndarray,
		trans_lower_id : np.ndarray,
		trans_upper_id : np.ndarray,
		
		out_lower_state : np.ndarray,
		out_upper_state : np.ndarray,
):
	for i in prange(trans_lower_id.shape[0]):
		out_lower_state[i] = state[trans_lower_id[i] - 1]
		out_upper_state[i] = state[trans_upper_id[i] - 1]
		


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