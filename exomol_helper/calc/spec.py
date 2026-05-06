

import numpy as np
import numpy.lib.recfunctions

import exomol_helper.calc.numba
import exomol_helper.calc.numba.spec

def line_strengths(
	line_data_chunk : np.ndarray, #[N_lines]
	T : np.ndarray, # #[N_temp] temperatures
	partition_function : np.ndarray, #[N_pf]
	T_ref : float,
	squeeze = False,
) -> np.ndarray:

	store = np.empty((3, line_data_chunk.shape[0],), dtype=float)
	line_strengths = np.empty((T.shape[0], line_data_chunk.shape[0],), dtype=float)

	exomol_helper.calc.numba.spec.line_strength_at_temp(
		line_data_chunk['spec_line_intensity'],
		line_data_chunk['wavenumber'],
		line_data_chunk['E"'],
		np.lib.recfunctions.structured_to_unstructured(partition_function[['T','Q']], partition_function.dtype[0]),
		T,
		T_ref = T_ref,
		store = store,
		out = line_strengths
	)

	return np.squeeze(line_strengths) if squeeze else line_strengths
	