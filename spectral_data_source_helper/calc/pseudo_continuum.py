

from typing import Callable

import numpy as np
from scipy.special import (
	voigt_profile,
)

from ..cfg.const import (
	T_ref, 
	P_ref,
	k_boltzmann_cgs,
	N_avogadro,
	c_light_cgs,
	c2_cgs,
)

import spectral_data_source_helper.calc.numba.spec


SQRT_2log2 = np.sqrt(2*np.log(2))

def voigt(
	delta_wn : np.ndarray, 
	alpha_d : float, 
	gamma_l : float
) -> np.ndarray:

	sigma = alpha_d / SQRT_2log2
	return voigt_profile(delta_wn, sigma, gamma_l)

def doppler_width(
		temp: float, 
		iso_mass : float,
		wavenumber : np.ndarray,
		
) -> np.ndarray:
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
	dws = doppler_width_const_cgs * wavenumber * np.sqrt( temp / iso_mass)
	
	return dws

def lorentz_width(
		pressure_ratio: float, 
		temp: float,
		amb_frac: float, # fraction of ambient gas
		gamma_self : np.ndarray,
		n_self : np.ndarray,
		gamma_amb : np.ndarray,
		n_amb : np.ndarray,
		tref : float = T_ref,
) -> np.ndarray:
	"""
	Calculate pressure-broadened width HWHM (half-width-half-maximum) of cauchy-lorentz distribution.
	"""
	return (tref/temp)**(n_amb*amb_frac + n_self*(1-amb_frac))*(gamma_amb*amb_frac + gamma_self*(1-amb_frac))*pressure_ratio


def stimulated_emission(
		transition_energy : np.ndarray, # Energy difference between upper and lower states. Can be approximated by center of bin wavenumber (may need to convert units)
		temp : float | np.ndarray,
):
	return 1 - np.exp(-transition_energy*c2_cgs/temp)

def boltzmann_population(
		str_weighted_mean_lower_state_energy : np.ndarray,
		temp : float | np.ndarray,
):
	return np.exp(-str_weighted_mean_lower_state_energy*c2_cgs/temp)


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
		lineshape_fn : Callable[[np.ndarray,float,float],np.ndarray] = voigt,
		T_cont : float = T_ref, # Temperature the pseudo-continuum was calculate at
		P_cont : float = P_ref, # Pressure the pseudo-continuum was calculated at
		n_neighbour_bins : int = 3, # number of bins around center to calculate line-spilling for
):
	if not isinstance(temp, np.ndarray):
		temp = np.array([temp], dtype=float)

	if not isinstance(partition_fn_at_temp, np.ndarray):
		partition_fn_at_temp = np.array([partition_fn_at_temp], dtype=float)

	result = np.zeros((temp.size, continuum_bin_centers.size,), dtype=float)
	store_x = np.empty((3, continuum_bin_centers.size,), dtype=float)
	store_y = np.empty((2*n_neighbour_bins+1,), dtype=float)
	
	print(f'{partition_fn_at_temp=}')

	spectral_data_source_helper.calc.numba.spec.pseudo_continuum(
		pressure,
		temp,
		partition_fn_at_temp,
		continuum_bin_centers,
		continuum_bin_widths,
		line_str_sum,
		str_weighted_mean_lower_state_energy,
		str_weighted_mean_gamma_self,
		str_weighted_mean_n_self,
		str_weighted_mean_gamma_amb,
		str_weighted_mean_n_amb,
		iso_mass_cgs,
		amb_frac,
		Q_cont,
		
		T_cont = T_cont,
		P_cont = P_cont,
		n_neighbour_bins = n_neighbour_bins,
		lineshape_id = spectral_data_source_helper.calc.numba.spec.LINESHAPE_ID_VOIGT,
		
		out = result,
		store_x = store_x,
		store_y = store_y,
	)
	
	return result