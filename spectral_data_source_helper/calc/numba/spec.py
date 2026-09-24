


import numpy as np
from numba import njit, prange

from .scipy import voigt_profile


from spectral_data_source_helper.cfg.const import (
	c_light_cgs,
	c2_cgs,
	GLOBAL_T_ref, 
	GLOBAL_P_ref,
	k_boltzmann_cgs,
	N_avogadro,
)

import spectral_data_source_helper.calc.numba

SQRT_2log2 = np.sqrt(2*np.log(2))

LINESHAPE_ID_VOIGT = 0

@njit(parallel=spectral_data_source_helper.calc.numba.PARALLEL)
def doppler_width(
		temp: float, 
		iso_mass : float,
		wavenumber : np.ndarray,
		out : np.ndarray
):
	"""
	Calculate Doppler width (HWHM), broadening due to thermal motion.
	NOTE: To get the standard deviation of the gaussian, multiply HWHM by 1/sqrt(2*ln(2))
	
		dlambda/lambda_0 = sqrt(2 ln(2) * (k_b * T)/(m_0 * c^2) )
							= sqrt(T/m_0) * 1/c * sqrt(2 ln(2) k_b)
							= sqrt(T/M_0) * 1/c * sqrt(2 ln(2) N_A k_b)
	dlambda - half-width-half-maximum in wavelength space
	lambda_0 - wavelength of line transition
	k_b - boltzmann const
	T - temperature (Kelvin)
	m_0 - mass of a single molecule
	c - speed of light
	M_0 - molecular mass (mass per mole of molecules)
	N_A - avogadro's constant
	
	"""
	doppler_width_const_cgs : float  = (1.0 / c_light_cgs) * np.sqrt(2 * np.log(2) * N_avogadro * k_boltzmann_cgs)
	for i in prange(wavenumber.shape[0]):
		out[i] = doppler_width_const_cgs * wavenumber[i] * np.sqrt( temp / iso_mass)

@njit(parallel=spectral_data_source_helper.calc.numba.PARALLEL)
def lorentz_width(
		pressure_ratio: float, 
		temp: float,
		amb_frac: float, # fraction of ambient gas
		gamma_self : np.ndarray,
		n_self : np.ndarray,
		gamma_amb : np.ndarray,
		n_amb : np.ndarray,
		
		out : np.ndarray,
		
		tref : float = GLOBAL_T_ref,
):
	"""
	Calculate pressure-broadened width HWHM (half-width-half-maximum) of cauchy-lorentz distribution.
	"""
	for i in prange(gamma_self.shape[0]):
		out[i] = (tref/temp)**(n_amb[i]*amb_frac + n_self[i]*(1-amb_frac))*(gamma_amb[i]*amb_frac + gamma_self[i]*(1-amb_frac))*pressure_ratio

@njit(parallel=spectral_data_source_helper.calc.numba.PARALLEL)
def pseudo_continuum(
		pressure : float,
		temp : np.ndarray, # [N_temp]
		partition_fn_at_temp : np.ndarray, # [N_temp]
		continuum_bin_centers : np.ndarray, # [N_bins]
		continuum_bin_widths : np.ndarray, # [N_bins]
		line_str_sum : np.ndarray, # [N_temp, N_bins]
		str_weighted_mean_lower_state_energy: np.ndarray, # [N_temp, N_bins]
		str_weighted_mean_gamma_self : np.ndarray, # [N_temp, N_bins]
		str_weighted_mean_n_self : np.ndarray, # [N_temp, N_bins]
		str_weighted_mean_gamma_amb : np.ndarray, # [N_temp, N_bins]
		str_weighted_mean_n_amb : np.ndarray, # [N_temp, N_bins]
		iso_mass_cgs : float, # Mass of isotopologue in cgs
		amb_frac : float, # Fraction of ambient gas
		Q_cont : float, # Partition function at `T_cont`
		
		out : np.ndarray, #[N_temp, N_bins]
		
		store_x : np.ndarray, #[3,N_bins]
		store_y : np.ndarray, #[2*n_neighbour_bins+1]
		
		T_cont : float = GLOBAL_T_ref, # Temperature the pseudo-continuum was calculate at
		P_cont : float = GLOBAL_P_ref, # Pressure the pseudo-continuum was calculated at
		n_neighbour_bins : int = 3, # number of bins around center to calculate line-spilling for
		
		lineshape_id : int = LINESHAPE_ID_VOIGT, # ID number of the lineshape to use
):
	#print('pseudo_continuum(...):', flush=True)
	if lineshape_id == LINESHAPE_ID_VOIGT:
		pass
	else:
		raise RuntimeError('Unknown lineshape id')
	
	line_strength_factor(
		continuum_bin_centers,
		str_weighted_mean_lower_state_energy,
		Q_cont,
		T_cont,
		store_x[:2],
		out = out[-1]
	)
	
	#print('    Q_ratio', flush=True)
	for j in range(temp.shape[0]):
	
		line_strength_from_ref(
			line_str_sum,
			continuum_bin_centers,
			str_weighted_mean_lower_state_energy,
			partition_fn_at_temp[j],
			temp[j],
			out[-1], # be careful here, want to use this later
			out = store_x[2],
			store=store_x[:2]
		)
		
		#print('    gamma_L', flush=True)
		lorentz_width(
			pressure / P_cont,
			temp[j],
			amb_frac,
			str_weighted_mean_gamma_self,
			str_weighted_mean_n_self,
			str_weighted_mean_gamma_amb,
			str_weighted_mean_n_amb,
			
			out = store_x[0],
			
			tref = T_cont,
		)
		
		#print('    alpha_D', flush=True)
		doppler_width(
			temp[j],
			iso_mass_cgs,
			continuum_bin_centers,
			
			out = store_x[1],
		)
		
		# zero output for summing later
		for i in prange(out.shape[1]):
			out[j,i] = 0
		
		# add absorption from lines accounting for spillage into neighbouring bins
		for i in range(out.shape[1]):
			lineshape_sum = 0.0
			for delta_k in range(-n_neighbour_bins, n_neighbour_bins+1):
				k = n_neighbour_bins + delta_k
				ii = i + delta_k
				if 0 <= ii and ii < out.shape[1]:
					# if neighbour region is within continuum bins, add lineshape
					if lineshape_id == LINESHAPE_ID_VOIGT:
						store_y[k] = voigt_profile(
							continuum_bin_centers[ii] - continuum_bin_centers[i],
							store_x[1,i] / SQRT_2log2,
							store_x[0,i],
						)
					lineshape_sum += store_y[k]
				else:
					store_y[k] = 0.0
				
				
			for delta_k in range(-n_neighbour_bins, n_neighbour_bins+1):
				k = n_neighbour_bins + delta_k
				ii = i + delta_k
				if (0 <= ii) and (ii < out.shape[1]) and (lineshape_sum != 0.0):
					out[j,ii] += store_x[2,i] * store_y[k] / lineshape_sum
		
		spectral_data_source_helper.calc.numba.divide(
			out[j],
			continuum_bin_widths,
			out = out[j]
		)


@njit(parallel=spectral_data_source_helper.calc.numba.PARALLEL)
def stimulated_emission_f(
		transition_wavenumber : np.ndarray, # Energy difference between upper and lower states. Can be approximated by center of bin wavenumber (may need to convert units)
		temp : float,
		out : np.ndarray,
):
	for i in prange(transition_wavenumber.shape[0]):
		out[i] = 1 - np.exp(-transition_wavenumber[i]*c2_cgs/temp)

@njit(parallel=spectral_data_source_helper.calc.numba.PARALLEL)
def stimulated_emission_v(
		transition_wavenumber : np.ndarray, # Energy difference between upper and lower states. Can be approximated by center of bin wavenumber (may need to convert units)
		temp : np.ndarray,
		out : np.ndarray,
):
	for i in prange(transition_wavenumber.shape[0]):
		for j in range(temp.shape[0]):
			out[j,i] = 1 - np.exp(-transition_wavenumber[i]*c2_cgs/temp[j])

@njit(parallel=spectral_data_source_helper.calc.numba.PARALLEL)
def boltzmann_population_f(
		lower_state_energy : np.ndarray,
		temp : float,
		out : np.ndarray,
):
	for i in prange(lower_state_energy.shape[0]):
		out[i] = np.exp(-lower_state_energy[i]*c2_cgs/temp)

@njit(parallel=spectral_data_source_helper.calc.numba.PARALLEL)
def boltzmann_population_v(
		lower_state_energy : np.ndarray,
		temp : np.ndarray,
		out : np.ndarray,
):
	for i in prange(lower_state_energy.shape[0]):
		for j in range(temp.shape[0]):
			out[j,i] = np.exp(-lower_state_energy[i]*c2_cgs/temp[j])

@njit(parallel=spectral_data_source_helper.calc.numba.PARALLEL)
def boltzmann_population_ratio_v(
		lower_state_energy : np.ndarray,
		temp : np.ndarray,
		t_ref : float,
		out : np.ndarray,
):
	# exp(- c2 * Epp / T_i) / exp(- c2 * Epp / T_ref) = exp(- c2 * Epp / T_i + c2*Epp / T_ref) = exp(- c2 * Epp (1/T_i - 1/T_ref))
	for i in prange(lower_state_energy.shape[0]):
		for j in range(temp.shape[0]):
			out[j,i] = np.exp(-lower_state_energy[i]*c2_cgs*(1.0/temp[j] - 1.0/t_ref))

@njit(parallel=spectral_data_source_helper.calc.numba.PARALLEL)
def spec_line_intensity_lte_f(
		temperature : float, 
		partition_fn : float,
		lower_state_energy : np.ndarray, #[N_lines]
		upper_state_degeneracy : np.ndarray, #[N_lines]
		einstein_A : np.ndarray, #[N_lines]
		wavenumber : np.ndarray, #[N_lines]
		
		out_boltz_pop : np.ndarray, #[N_lines]
		out_stim_emission : np.ndarray, #[N_lines]
		out: np.ndarray, #[N_lines]
):
	"""
	Compute spectral line intensity at local thermal equilibrium.
	
	spec_line_intensity = (gp * A)/(8 * pi * c * v^2) * ( exp(- c2 * Epp / T) * (1 - exp(- c2 * v / T)) ) / Q
	"""
	
	boltzmann_population_f(lower_state_energy, temperature, out=out_boltz_pop)
	stimulated_emission_f(wavenumber, temperature, out=out_stim_emission)
	
	for i in prange(wavenumber.shape[0]):
		out[i] = (out_boltz_pop[i] * out_stim_emission[i] / partition_fn) * upper_state_degeneracy[i] * einstein_A[i] / (8 * np.pi * c_light_cgs * wavenumber[i] * wavenumber[i])


@njit(parallel=spectral_data_source_helper.calc.numba.PARALLEL)
def line_strength_from_temp_ratios(
		line_intensity : np.ndarray, #[N_lines]
		Q_ratio : np.ndarray, #[N_temp]
		stimulated_emission_ratio : np.ndarray, #[N_temp, N_lines]
		boltz_pop_ratio : np.ndarray, #[N_temp, N_lines]
		
		out : np.ndarray, #[N_temp, N_lines]
):
	"""
	Compute line strengths from temperature ratios of values
	"""
	for i in prange(line_intensity.shape[0]):
		for j in range(Q_ratio.shape[0]):
			out[j,i] = line_intensity[i] * Q_ratio[j] * stimulated_emission_ratio[j,i] * boltz_pop_ratio[j,i]


@njit(parallel=False)
def line_strength_factor(
		wavenumber : np.ndarray, #[N_lines]
		lower_energy_state_wavenumber : np.ndarray, #[N_lines]
		partition_fn_value_at_T : float,
		T : float,
		
		store : np.ndarray, #[2, N_lines]
		
		out : np.ndarray, #[N_lines]
		
):
	"""
	Compute line strength factor at temperature T,
	
	factor = (stimulated_emission * boltzmann_population) /  Q(T)
	"""
	
	stimulated_emission_f(
		wavenumber,
		T,
		out = store[0]	
	)
	
	boltzmann_population_f(
		lower_energy_state_wavenumber,
		T,
		out = store[1]
	)
	
	spectral_data_source_helper.calc.numba.multiply(
		store[0],
		store[1],
		out=out
	)
	spectral_data_source_helper.calc.numba.divide_s(
		out,
		partition_fn_value_at_T,
		out=out
	)
	


@njit(parallel=False)
def line_strength_from_ref(
		line_intensity : np.ndarray, #[N_lines]
		wavenumber : np.ndarray, #[N_lines]
		lower_energy_state_wavenumber : np.ndarray, #[N_lines]
		partition_fn_value_at_T : float,
		T : float,
		line_strength_factor_ref : np.ndarray, #[N_lines]
		
		store : np.ndarray, #[2, N_lines]
		
		out : np.ndarray, #[N_lines]
):
	"""
	Compute line strength at a temperature given a reference line strength factor
	"""
	
	line_strength_factor(
		wavenumber,
		lower_energy_state_wavenumber,
		partition_fn_value_at_T,
		T,
		store,
		out = out
	)
	spectral_data_source_helper.calc.numba.divide(
		out,
		line_strength_factor_ref,
		out = out
	)
	spectral_data_source_helper.calc.numba.multiply(
		out,
		line_intensity,
		out = out
	)


@njit(parallel=False)
def line_strength_at_temp(
		line_intensity : np.ndarray, #[N_lines]
		wavenumber : np.ndarray, #[N_lines]
		lower_energy_state_wavenumber : np.ndarray, #[N_lines]
		partition_fn : np.ndarray, #[N_pf, 2], (temperature, partition_fn_value)
		T : np.ndarray, #[N_temp]
		
		out : np.ndarray, #[N_temp, N_lines]
		
		store : None | np.ndarray = None, #[3, N_lines]
		
		T_ref : float = GLOBAL_T_ref,
):
	"""
	Compute line strength at a temperatures `T`
	"""
	n_lines = line_intensity.shape[0]
	n_temp = T.shape[0]
	
	if store is None:
		store = np.ones((3,n_lines,), dtype=float)
	else:
		for j in range(3):
			for i in prange(n_lines):
				store[j,i] = 1
	
	Q_ref = spectral_data_source_helper.calc.numba.lin_interp_s(
		partition_fn[:,0],
		partition_fn[:,1],
		T_ref
	)
	
	line_strength_factor(
		wavenumber,
		lower_energy_state_wavenumber,
		Q_ref,
		T_ref,
		store[:2],
		out = store[2]
	)
	
	for j in range(n_temp):
		Q_temp = spectral_data_source_helper.calc.numba.lin_interp_s(
			partition_fn[:,0],
			partition_fn[:,1],
			T[j]
		)
		line_strength_from_ref(
			line_intensity,
			wavenumber,
			lower_energy_state_wavenumber,
			Q_temp,
			T[j],
			store[2],
			store[:2],
			out = out[j]
		)



#@njit(parallel=spectral_data_source_helper.calc.numba.PARALLEL)
@njit(parallel=False)
def accumulate_pseudocontinuum_1d(
	weak_line_mask : np.ndarray, #[N_lines]
	bin_indices : np.ndarray, #[N_lines]
	line_strengths_at_temp : np.ndarray, #[N_lines]
	line_strength_sum : np.ndarray, #[N_bins]
	input_block : np.ndarray, #[N_lines, N_pairs]
	output_block : np.ndarray, #[N_bins, N_pairs]
	n_lines : int,
	n_bins : int,
	n_pairs : int,
):

	# Reset accumulators
	for x in range(n_bins):
		line_strength_sum[x] = 0
		for k in range(n_pairs):
			output_block[x][k] = 0

	# NOTE: parallel loop may have race condition on accumulators, NUMBA says it
	# accounts for that but this should be checked
	for i in range(n_lines):
		if not weak_line_mask[i]:
			continue
		
		x = bin_indices[i]
		
		line_strength_sum[x] += line_strengths_at_temp[i]
		
		for k in range(n_pairs):
			output_block[x][k] += line_strengths_at_temp[i] * input_block[i][k]


@njit(parallel=spectral_data_source_helper.calc.numba.PARALLEL)
def accumulate_pseudocontinuum(
	weak_line_mask : np.ndarray, #[N_temp, N_lines]
	bin_indices : np.ndarray, #[N_temp, N_lines]
	line_strengths_at_temp : np.ndarray, #[N_temp, N_lines]
	line_strength_sum : np.ndarray, #[N_temp, N_bins]
	input_block : np.ndarray, #[N_lines, N_pairs]
	output_block : np.ndarray, #[N_temp, N_bins, N_pairs]
):
	n_temp = weak_line_mask.shape[0]
	n_lines = weak_line_mask.shape[1]
	n_bins = output_block.shape[1]
	n_pairs = output_block.shape[2]
	for j in prange(n_temp):
		accumulate_pseudocontinuum_1d(
			weak_line_mask[j],
			bin_indices[j],
			line_strengths_at_temp[j],
			line_strength_sum[j],
			input_block,
			output_block[j],
			n_lines,
			n_bins,
			n_pairs,
		)
