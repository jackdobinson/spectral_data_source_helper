"""
Routines to calculate absorption coefficients
"""


import numpy as np

from exomol_helper.cfg.const import (
	c_light_cgs,
	c2_cgs,
)

#from exomol_helper.cfg.log import pkg_logger as _lgr



def spec_line_intensity_lte(
		temp : np.ndarray,
		partition_fn : np.ndarray,
		lower_state_energy : np.ndarray,
		upper_state_degeneracy : np.ndarray,
		einstein_A : np.ndarray,
		wavenumber : np.ndarray,
		out: None | np.ndarray, # put the output in this array if it is not None
) -> np.ndarray:
	"""
	Compute spectral line intensity at local thermal equilibrium.
	
	spec_line_intensity = (gp * A)/(8 * pi * c * v^2) * ( exp(- c2 * Epp / T) * (1 - exp(- c2 * v / T)) ) / Q
	"""
	wn_nonzero_mask = wavenumber != 0
	
	spec_line_intensity_const = upper_state_degeneracy[wn_nonzero_mask] * einstein_A[wn_nonzero_mask] / (8 * np.pi * c_light_cgs * wavenumber[wn_nonzero_mask] * wavenumber[wn_nonzero_mask])
	
	if out is not None:
		out[wn_nonzero_mask] = spec_line_intensity_const * np.exp(-c2_cgs * lower_state_energy[wn_nonzero_mask] / temp) * (1 - np.exp(-c2_cgs * wavenumber[wn_nonzero_mask] / temp)) / partition_fn
	else:
		return spec_line_intensity_const * np.exp(-c2_cgs * lower_state_energy[wn_nonzero_mask] / temp) * (1 - np.exp(-c2_cgs * wavenumber[wn_nonzero_mask] / temp)) / partition_fn
	



