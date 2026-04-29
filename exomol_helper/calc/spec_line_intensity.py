"""
Routines to calculate absorption coefficients
"""


import numpy as np

from exomol_helper.cfg.const import (
	c_light_cgs,
	c2_cgs,
)

#from exomol_helper.cfg.log import pkg_logger as _lgr

def exp_c2_Epp(
		temp : np.ndarray,
		lower_state_energy : np.ndarray,
		out = None
):
	if out is None:
		return np.exp(-c2_cgs * lower_state_energy / temp)
	else:
		np.divide(lower_state_energy, temp, out=out)
		np.multiply(-c2_cgs, out, out=out)
		np.exp(out, out=out)
		

def one_minus_exp_c2_nu(
		temp : np.ndarray,
		wavenumber : np.ndarray,
		out = None
):
	if out is None:
		return (1 - np.exp(-c2_cgs * wavenumber / temp))
	else:
		np.divide(wavenumber, temp, out=out)
		np.multiply(-c2_cgs, out, out=out)
		np.exp(out, out=out)
		np.subtract(1, out, out=out)
		


def spec_line_intensity_lte(
		temp : np.ndarray,
		partition_fn : np.ndarray,
		lower_state_energy : np.ndarray,
		upper_state_degeneracy : np.ndarray,
		einstein_A : np.ndarray,
		wavenumber : np.ndarray,
		out: None | np.ndarray = None, # put the output in this array if it is not None
) -> np.ndarray:
	"""
	Compute spectral line intensity at local thermal equilibrium.
	
	spec_line_intensity = (gp * A)/(8 * pi * c * v^2) * ( exp(- c2 * Epp / T) * (1 - exp(- c2 * v / T)) ) / Q
	"""
	if out is None:
	
		#wn_nonzero_mask = wavenumber != 0
		#
		#spec_line_intensity_const = upper_state_degeneracy[wn_nonzero_mask] * einstein_A[wn_nonzero_mask] / (8 * np.pi * c_light_cgs * wavenumber[wn_nonzero_mask] * wavenumber[wn_nonzero_mask])
		#return spec_line_intensity_const * np.exp(-c2_cgs * lower_state_energy[wn_nonzero_mask] / temp) * (1 - np.exp(-c2_cgs * wavenumber[wn_nonzero_mask] / temp)) / partition_fn
	
		spec_line_intensity_const = upper_state_degeneracy * einstein_A / (8 * np.pi * c_light_cgs * wavenumber * wavenumber)
		return spec_line_intensity_const * np.exp(-c2_cgs * lower_state_energy / temp) * (1 - np.exp(-c2_cgs * wavenumber / temp)) / partition_fn
		
	else:
		wn_nonzero_mask = wavenumber != 0
		
		np.multiply(wavenumber[wn_nonzero_mask],wavenumber[wn_nonzero_mask], out=out[wn_nonzero_mask])
		np.multiply(8 * np.pi * c_light_cgs, out[wn_nonzero_mask], out=out[wn_nonzero_mask])
		np.divide(einstein_A[wn_nonzero_mask], out[wn_nonzero_mask], out=out[wn_nonzero_mask])
		np.multiply(upper_state_degeneracy[wn_nonzero_mask], out[wn_nonzero_mask], out=out[wn_nonzero_mask])
		
		t1 = np.empty_like(out[wn_nonzero_mask])
		t2 = np.empty_like(out[wn_nonzero_mask])
		
		exp_c2_Epp(temp, lower_state_energy[wn_nonzero_mask], out=t1)
		one_minus_exp_c2_nu(temp, wavenumber[wn_nonzero_mask], out=t2)
		
		np.multiply(t1, t2, out=t2)
		np.multiply(t2, out[wn_nonzero_mask], out=out[wn_nonzero_mask])
		np.divide(out[wn_nonzero_mask], partition_fn, out=out[wn_nonzero_mask])
		
	



