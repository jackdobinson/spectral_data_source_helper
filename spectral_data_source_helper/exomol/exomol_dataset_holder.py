

import json
import dataclasses as dc
from typing import Any, Generator, Literal, ClassVar, Iterable
import datetime as dt
from pathlib import Path

import numpy as np
import numpy.lib.recfunctions

from spectral_data_source_helper.utils import fetch
from spectral_data_source_helper.utils import read
from spectral_data_source_helper.utils import structured_array
from spectral_data_source_helper.cfg.cont import (
	PKG_CACHE,
)
from .cfg.const import (
	EXOMOL_API_URL_FMT,
	EXOMOL_URL_PREFIX,
	EXOMOL_STATE_FILE_ENDINGS,
	EXOMOL_TRANSITION_FILE_ENDINGS,
	EXOMOL_API_INTERNAL_URL_START,
	T_ref,
	Dalton_cgs,
	TRANS_STR_FLOAT32_FACTOR,
)

import qn_set_manager
import broad_file_manager

#from spectral_data_source_helper.cfg.log import progress_lgr
from spectral_data_source_helper.cfg.log import pkg_logger as _lgr

from .datatypes import (
	ExomolDatasetInfo,
	BroadeningSourceCode,
)

from .exomol_index_types import (
	mol_formula_to_api_mol,
	ExomolIsotopeDef,
)

import spectral_data_source_helper.calc.numba
import spectral_data_source_helper.calc.numba.transition_states
import spectral_data_source_helper.calc.numba.spec
import spectral_data_source_helper.calc.numba.broadening

#BYTES_DTYPE = np.dtype(np.uint8)
BYTES_DTYPE = np.dtype(np.uint64)


@dc.dataclass
class ExomolDatasetHolder:
	d : ExomolDatasetInfo
	
	# private attributes
	_api_linelist_urls : None | tuple[str,...] = None
	_api_partition_function_urls : None | tuple[str,...] = None
	_api_broad_urls : None | dict[str,str] = None
	_isotope_def : None | ExomolIsotopeDef = None
	_is_external : None | bool = None
	_all_data_urls : None | tuple[str,...] = None
	_n_transitions : None | int = None
	_states : None | np.ndarray = None
	_states_dtype : None | list[tuple[str,Any],...] = None
	_states_shape : None | tuple[int,...] = None
	_trans_dtype : None | list[tuple[str,Any]] = None
	_trans_n_cols : None | int = None
	_lower_state_names : None | tuple[str,...] = None
	_upper_state_names : None | tuple[str,...] = None
	_broad_gas_names : None | tuple[str,...] = None
	_broad_names_by_gas : None | tuple[list[str,...],...] = None
	_broad_dtype : None | list[tuple[str,np.dtype],...] = None
	_default_broad_vals : None | dict[str,tuple[float,float]] = None
	_fallback_broad_vals : None | tuple[float,float] = None
	emergency_broad_vals : ClassVar[tuple[float,float]] = (0.07, 0.5) # (gamma, n) to use when no other values are present (taken from PyExoCross)
	_partition_function : None | np.ndarray = None
	_broad_map : None | dict[str,dict[str,dict[tuple[Any,...],tuple[float,float]]]] = None
	_possible_qn_sets : None | dict[str,list[str]] = None
	_pseudo_continuum_contribution_dtype : None | np.dtype = None
	_pseudo_continuum_contribution_dtype_list : None | list[tuple[str,Any],...] = None
	
	@property
	def iso_mass_cgs(self) -> float:
		return Dalton_cgs * self.isotope_def.isotopologue.mass_in_Da
	
	@property
	def iso_path(self) -> str:
		return f'{self.d.mol_formula}/{self.d.iso_slug}'

	@property
	def datafile_prefix(self) -> str:
		return f'{self.d.iso_slug}__{self.d.dataset_name}'
	
	@property
	def data_dir(self) -> str:
		return f'{self.iso_path}/{self.d.dataset_name}'
	
	@property
	def short_info_str(self) -> str:
		external_tag = ' [EXTERNAL]' if self.is_external else ''
		return f'{self.d.mol_formula}/{self.d.iso_formula}/{self.d.dataset_name}{external_tag}'
	
	@property
	def isotope_def(self):
		if self._isotope_def is None:
			error = None
			isotope_def_url_candidates = tuple('https://www.' + EXOMOL_URL_PREFIX + '/' + self.data_dir + '/' + self.datafile_prefix + x for x in ('.def.json',))# '.def'))
			_lgr.info(f'{isotope_def_url_candidates=}')
			for isotope_def_url in isotope_def_url_candidates:
				try:
					self._isotope_def = ExomolIsotopeDef(mol_formula=self.d.mol_formula, **json.loads(fetch.file_from_cache(isotope_def_url, cache=PKG_CACHE)))
				except Exception as e:
					error = e
				else:
					error = None
					break
			if error is not None:
				_lgr.error(f'Could not load ExomolIsotopeDef file for {self.short_info_str}')
				raise error
	
		return self._isotope_def
	
	@property
	def api_data(self) -> str:
		api_json = json.loads(fetch.file_from_cache(EXOMOL_API_URL_FMT.format(mol_formula_to_api_mol(self.d.mol_formula)), cache=PKG_CACHE))
		return api_json[self.d.iso_formula]
	
	@property
	def api_linelist_urls(self)->tuple[str]:
		if self._api_linelist_urls is None:
			self._api_linelist_urls = tuple(x['url'] for x in self.api_data.get('linelist',dict()).get(self.d.dataset_name,dict()).get('files',tuple()))
		
		return self._api_linelist_urls
	
	@property
	def api_states_urls(self)->tuple[str]:
		return tuple(x for x in self.api_linelist_urls if any(x.endswith(y) for y in EXOMOL_STATE_FILE_ENDINGS))
	
	@property
	def api_transition_urls(self)->tuple[str]:
		return tuple(x for x in self.api_linelist_urls if any(x.endswith(y) for y in EXOMOL_TRANSITION_FILE_ENDINGS))
	
	@property
	def api_partition_function_urls(self)->tuple[str]:
		if self._api_partition_function_urls is None:
			self._api_partition_function_urls = tuple(x['url'] for x in self.api_data.get('partitionfunction',dict()).get(self.d.dataset_name,dict()).get('files',tuple()))
		
		return self._api_partition_function_urls
	
	@property
	def api_broad_urls(self) -> dict[str,str]:
		if self._api_broad_urls is None:
			#print(f'{self._api_broad_urls=}')
			self._api_broad_urls = broad_file_manager.search_broad_files_for(self.d.mol_formula, self.d.iso_slug)
			#print(f'{self._api_broad_urls=}')
		return self._api_broad_urls
	
	@property
	def all_data_urls(self) -> tuple[str,...]:
		if self._all_data_urls is None:
			self._all_data_urls = (
				*self.api_states_urls,
				*self.api_partition_function_urls,
				*tuple(self.api_broad_urls.values()),
				*self.api_transition_urls,
			)
		return self._all_data_urls
	
	@property
	def is_external(self):
		if self._is_external is None:
			self._is_external = any(not x.startswith(EXOMOL_API_INTERNAL_URL_START) for x in self.api_linelist_urls)
		return self._is_external
	
	@property
	def n_transitions(self) -> int:
		if self._n_transitions is None:
			self._n_transitions = self.isotope_def.dataset.transitions.number_of_transitions
		return self._n_transitions
	
	@property
	def states_dtype(self) -> np.dtype:
		if self._states_dtype is None:
			self._states_dtype = self.isotope_def.dataset.states.get_states_field_dtype()
		return self._states_dtype
	
	@property
	def states_shape(self) -> tuple[int,...]:
		if self._states_shape is None:
			self._states_shape = self.isotope_def.dataset.states.number_of_states
		return self._states_shape
	
	@property
	def states_short_names(self) -> list[str]:
		return [x.split(':')[-1] for x in self.states_dtype.names]
	
	@property
	def states(self) -> np.ndarray:
		if self._states is None:
			dt_start = dt.datetime.now()
			_lgr.info(f'Starting to load states at {dt_start}')

			states_url = self.api_states_urls[0]
			if states_url.endswith('.bz2'):
				states_numpy_fpath = (PKG_CACHE / f'{self.api_states_urls[0]}').with_suffix('.npz')
			else:
				states_numpy_fpath = (PKG_CACHE / f'{self.api_states_urls[0]}.npz')
			
			if states_numpy_fpath.exists():
				self._states = np.load(states_numpy_fpath)['states']
			else:
				# load from web/cache
				self._states = np.loadtxt(
					fetch.file_from_cache(f'https://www.{self.api_states_urls[0]}',cache=PKG_CACHE,return_fpath=True), 
					dtype = self.states_dtype,
					delimiter=None
				)
				
				# save to faster format
				np.savez_compressed(states_numpy_fpath, states=self._states)
			
			dt_end = dt.datetime.now()
			_lgr.info(f'States loaded at {dt_end}. Took {(dt_end-dt_start).total_seconds()} s')
		
		return self._states
	
	@property
	def trans_n_cols(self) -> int:
		if self._trans_n_cols is None:
			#print('### GETTING TRANS N COLS ### ')

			trans_fpath = self.trans_file_precidence(fetch.file_from_cache(f'https://www.{self.api_transition_urls[0]}',cache=PKG_CACHE,return_fpath=True))
			
			#print(f'{trans_fpath=}')
			
			if trans_fpath.name.endswith('.trans') or trans_fpath.name.endswith('.trans.bz2'):
				for n_bytes, aline in read.iter_line_records(trans_fpath):
					self._trans_n_cols = len(aline.split())
					break
			elif ('.trans.bin' in trans_fpath.name):
				self._trans_n_cols = len(spectral_data_source_helper.utils.read.bin_file_dtype(trans_fpath).names)
			else:
				raise RuntimeError(f"Could not read transitio file {trans_fpath} to get number of columns")
			
			#print(f'### GOT TRANS N COLS {self._trans_n_cols=} ### ')
			
			
			
		return self._trans_n_cols
	
	@property
	def trans_dtype(self) -> list[tuple[str,Any]]:
		if self._trans_dtype is None:
			self._trans_dtype = np.dtype([('upper_id',np.int64),('lower_id',np.int64), ('einstein_A', np.float64), ('wavenumber',np.float64)][:self.trans_n_cols], align=True)
		return self._trans_dtype
	
	@property
	def trans32_dtype(self) -> list[tuple[str,Any]]:
		return np.dtype([('upper_id',np.uint32),('lower_id',np.uint32), ('einstein_A', np.float32), ('wavenumber',np.float32)][:self.trans_n_cols], align=True)
	
	@property
	def lower_state_names(self):
		if self._lower_state_names is None:
			self._lower_state_names = [f'{x}"' for x in self.states_short_names]
		return self._lower_state_names
	
	@property
	def upper_state_names(self):
		if self._upper_state_names is None:
			self._upper_state_names = [f'{x}\'' for x in self.states_short_names]
		return self._upper_state_names
	
	@property
	def transition_state_names(self):
		return (*self.lower_state_names, *self.upper_state_names)
	
	@property
	def transition_state_quantum_number_names(self):
		non_quantum_number_state_names = ('tau\'', 'tau"', 'E\'', 'E"')
		return tuple(x for x in (*self.lower_state_names, *self.upper_state_names) if x not in non_quantum_number_state_names)
	
	@property
	def broad_gas_names(self) -> tuple[str,...]:
		if self._broad_gas_names is None:
			self._broad_gas_names = tuple(self.api_broad_urls.keys())
			if 'self' not in self._broad_gas_names:
				self._broad_gas_names = ('self', *self._broad_gas_names)
			#print(f'{self._broad_gas_names=}')
		return self._broad_gas_names
	
	@property
	def broad_names_by_gas(self) -> tuple[list[str,...],...]:
		if self._broad_names_by_gas is None:
			self._broad_names_by_gas = tuple([f'gamma_{gas_name}', f'n_{gas_name}'] for gas_name in self.broad_gas_names)
		return self._broad_names_by_gas
	
	@property
	def broad_dtype(self) -> list[tuple[str,np.dtype],...]:
		if self._broad_dtype is None:
			self._broad_dtype = []
			for broad_name_list in self.broad_names_by_gas:
				self._broad_dtype.extend(((broad_name, np.dtype(float)) for broad_name in broad_name_list))
		return self._broad_dtype
	
	@property
	def broad_source_var_names(self) -> list[str,...]:
		return [f'broad_source_{gas_name}' for gas_name in self.broad_gas_names]
	
	@property
	def broad_source_dtype_list(self) -> list[tuple[str,np.dtype],...]:
		"""
		dtype for column `broad_source_<GAS>`, where `<GAS>` is the gas name.
		
		Values: 
			* +1 means broadening parameters are from a *.broad file
			* -1 means broadening parameters are from the default for the isotope-gas combo
			* -2 means broadening parameters are the default for the gas
			* -3 means the broadening parameters are the emergency values from ExomolDatasetHolder.emergency_broad_vals
		"""
		return [(bs_var_name,'i8') for bs_var_name in self.broad_source_var_names]
	
	@property
	def default_broad_vals(self) -> dict[str,tuple[float,float]]:
		if self._default_broad_vals is None:
			self._default_broad_vals = dict((x.broad_gas_name,(x.lorentzian_half_width, x.temperature_exponent)) for x in self.isotope_def.broad.broadeners)
		return self._default_broad_vals
	
	@property
	def fallback_broad_vals(self) -> tuple[float,float]:
		if self._fallback_broad_vals is None:
			try:
				self._fallback_broad_vals = (self.isotope_def.broad.default_lorentzian_half_width, self.isotope_def.broad.default_temperature_exponent)
			except:
				self._fallback_broad_vals = tuple()
		return self._fallback_broad_vals
	
	@property
	def transition_states_dtype(self) -> list[tuple[str,Any]]:
		states_dtype = self.states_dtype
		
		lower_state_dtype = tuple((x, y) for x,y in zip(self.lower_state_names, (z[0].type for z in states_dtype.fields.values())))
		upper_state_dtype = tuple((x, y) for x,y in zip(self.upper_state_names, (z[0].type for z in states_dtype.fields.values())))
		
		dtype = np.dtype(
			[
				('einstein_A', float),
				('wavenumber', float),
				*lower_state_dtype,
				*upper_state_dtype,
			],
			align=True
		)
		return dtype
	
	@property
	def line_data_non_broadening_dtype_spec(self) -> list[tuple[str,Any]]:
		return [
			('spec_line_intensity', float), # Spectral line intensity (calculated from other properties)
			('wavenumber', float), # wavenumber of line center
			('einstein_A', float), # einstein A coefficient
			('E"', float), # lower state energy (in cm^{-1})
			('E\'', float), # upper state energy (in cm^{-1})
			('g_tot"', int), # lower state degeneracy
			('g_tot\'', int), # upper state degeneracy
			('spec_boltz_pop', float), # boltzman population part of the spectral line intensity
			('spec_stim_emission', float), # stimulated_emission part of the spectral line intensity
		]
	
	@property
	def line_data_dtype(self) -> list[tuple[str,Any]]:
	
		dtype = np.dtype([
			*self.line_data_non_broadening_dtype_spec,
			*self.broad_dtype,
			*self.broad_source_dtype_list,
		])
		
		return dtype
	
	@property
	def possible_qn_sets(self) -> dict[str, list[str]]:
		"""
		A dictionary mapping quantum number set codes (qn_codes) to the state names they use for all qn_codes that this dataset defines quantum numbers for
		"""
		if self._possible_qn_sets is None:
			transition_state_names = self.transition_state_names
			self._possible_qn_sets = dict((k,['J"',*v]) for k,v in qn_set_manager.qn_set.items() if all(x in transition_state_names for x in v))
			#_lgr.debug(f'{self._possible_qn_sets=}')
		return self._possible_qn_sets
	
	@property
	def broadening_data(self) -> tuple[dict[str,slice], np.ndarray, np.ndarray, np.ndarray]:
		"""
		Load broadening data into an array
		"""
		
		# Count number of entries across all broadening files
		n_broad_entries_dict = dict()
		for bg_name, broad_url in self._api_broad_urls.items():
			n_broad_entries_dict.setdefault(bg_name,0)
			fpath = fetch.file_from_cache(broad_url, cache=PKG_CACHE, return_fpath=True)
			
			with open(fpath, 'r') as f:
				for aline in f:
					n_broad_entries_dict[bg_name] += 1
					
		total_broad_entries = sum(n_broad_entries_dict.values())
		
		ts_dtype_dict = dict((x,y[0].type) for x,y in self.transition_states_dtype.fields.items())
		
		n = 0
		broad_array_gas_slices = dict()
		for bg_name, bgn in n_broad_entries_dict.items():
			broad_array_gas_slices[bg_name] = slice(n,bgn)
			n += bgn
		
		if 'self' not in broad_array_gas_slices:
			broad_array_gas_slices['self'] = slice(0,0)
		
			
		broad_array = np.zeros((total_broad_entries,), self.transition_states_dtype)
		broad_comp_mask = np.zeros((total_broad_entries, broad_array.dtype.itemsize // BYTES_DTYPE.itemsize), dtype=bool) # if `True` we should compare this byte, otherwise skip it
		broad_values = np.zeros((total_broad_entries,2), float) # (gamma, temp_exp)
		
		i_bg = dict()
		
		# populate broadening array
		for bg_name, broad_url in self._api_broad_urls.items():
			i_bg.setdefault(bg_name,0)
			fpath = fetch.file_from_cache(broad_url, cache=PKG_CACHE, return_fpath=True)
			
			with open(fpath, 'r') as f:
				for aline in f:
					split_line = aline.split()
					code, gamma, temp_exp, Jpp = split_line[:4]
					quantum_number_strings = split_line[4:]
					Jpp = ts_dtype_dict['J"'](Jpp)
				
					quantum_numbers = []
					for (name, value_string) in zip(self.possible_qn_sets[code][1:], quantum_number_strings):
						type_converter = ts_dtype_dict[name]
						quantum_numbers.append(type_converter(value_string) if not isinstance(type_converter, str) else value_string)
					
					qn_values = (Jpp,*quantum_numbers)
					
					#print(f'{broad_array[i_bg[bg_name]]=}')
					#print(f'{self.possible_qn_sets[code]=}')
					
					#not_shared_names = [x for x in self.possible_qn_sets[code] if x not in broad_array.dtype.names]
					#print(f'{not_shared_names=}')
					
					broad_array[self.possible_qn_sets[code]][i_bg[bg_name]] = qn_values
					broad_values[i_bg[bg_name]] = (float(gamma), float(temp_exp))
					
					for name in self.possible_qn_sets[code]:
						byte_start = broad_array.dtype.fields[name][1] / BYTES_DTYPE.itemsize
						byte_end = byte_start + (broad_array.dtype.fields[name][0].itemsize / BYTES_DTYPE.itemsize)
						
						assert byte_start == int(byte_start) and byte_end == int(byte_end)
						byte_start = int(byte_start)
						byte_end = int(byte_end)
						broad_comp_mask[i_bg[bg_name]][byte_start:byte_end] = True
					
					i_bg[bg_name] += 1
		
		
		broad_array = broad_array.view(BYTES_DTYPE).reshape(-1,broad_array.dtype.itemsize//BYTES_DTYPE.itemsize)
		
		return broad_array_gas_slices, broad_array, broad_comp_mask, broad_values
	
	@property
	def broad_map(self) -> dict[str,dict[str,dict[tuple[Any,...],tuple[float,float]]]]:
		if self._broad_map is None:
			self._broad_map = dict()
			# `broad_map` holds (gamma_X, temp_exp_X) broadening parameters for each broadening gas 
			# of the dataset in the below format. 
			#
			# NOTE: Note that as `broad_map` is built from EXOMOL's "*.broad" files, and python
			#       dictionaries preserve ordering. When iterating through `broad_map`, earlier values
			#       take precedence over later values. 
			#
			# 	{ 
			#		<bg_name> : { 
			#			<code> : { 
			#				<qn_values> : (
			#					<qn_values_comparator>, 
			#					(<gamma_X>, <temp_exp_X>)
			#				)
			#			} 
			#		} 
			#	}
			# Where :
			#  * <bg_name> is the name of the broadening gas
			#  * <code> is the name of a set of quantum numbers that the following broadening coefficients 
			#    are valid for.
			#  * <qn_values> is a tuple of the values of the quantum numbers in the set denoted by <code> 
			#    for which the following broadening coefficients are vaid.
			#  * <qn_values_comparator> is the same data as <qn_values> but in a structured array, this is
			#    required for performing comparisons (later on) which select the lines that are valid for a
			#    specific set of broadening coefficients
			#  * <gamma_X> and <temp_exp_X> are the broadening coefficients (lorentzian half-width and 
			#    temperature exponent respectively) that should be used if a line has compatible quantum 
			#    numbers.
			#
			# Example:
			#	broad_map = { 
			#		"H2" : { 
			#			"a0" : { 
			#				(0,) : (
			#					np.array((0,), dtype=[('J"', int)]),
			#					(<gamma_H2>, <temp_exp_H2>) # values are different for each entry
			#				),
			#				(1,) : (
			#					np.array((1,), dtype=[('J"', int)]),
			#					(<gamma_H2>, <temp_exp_H2>) # values are different for each entry
			#				),
			#				...
			#			},
			#			"a1" : {
			#				(0,1) : (
			#					np.array((0,1), dtype=[('J"', int), ('J\'', int)]),
			#					(<gamma_H2>, <temp_exp_H2>) # values are different for each entry
			#				),
			#				(1,2) : (
			#					np.array((1,2), dtype=[('J"', int), ('J\'', int)]),
			#					(<gamma_H2>, <temp_exp_H2>) # values are different for each entry
			#				),
			#				...
			#			},
			#			...
			#		},
			#		"self" : {
			#			"m0" : {
			#				(0,) : (
			#					np.array((0,), dtype=[('J"', int)]),
			#					(<gamma_H2>, <temp_exp_H2>) # values are different for each entry
			#				),
			#				(-1,) : (
			#					np.array((-1,), dtype=[('J"', int)]),
			#					(<gamma_H2>, <temp_exp_H2>) # values are different for each entry
			#				),
			#				...
			#			},
			#			...
			#		},
			#		...
			#	}
			
			ts_dtype_dict = dict((x,y[0].type) for x,y in self.transition_states_dtype.fields.items() if (x in self.transition_state_quantum_number_names))
			
			# Build `broad_map` for this dataset.
			for bg_name, broad_url in self._api_broad_urls.items():
				fpath = fetch.file_from_cache(broad_url, cache=PKG_CACHE, return_fpath=True)
				
				with open(fpath, 'r') as f:
					self._broad_map.setdefault(bg_name, dict())
					for aline in f:
						split_line = aline.split()
						code, gamma, temp_exp, Jpp = split_line[:4]
						quantum_number_strings = split_line[4:]
						Jpp = ts_dtype_dict['J"'](Jpp)
					
						quantum_numbers = []
						for (name, value_string) in zip(self.possible_qn_sets[code][1:], quantum_number_strings):
							type_converter = ts_dtype_dict[name]
							quantum_numbers.append(type_converter(value_string) if not isinstance(type_converter, str) else value_string)
						
						qn_values = (Jpp,*quantum_numbers)
						dtype = [(name,ts_dtype_dict[name]) for name in ('J"',*self.possible_qn_sets[code][1:])]
						self._broad_map[bg_name].setdefault(code, dict())[qn_values] = (
							np.array(qn_values, dtype=dtype),
							(float(gamma), float(temp_exp))
						)
		return self._broad_map
	
	@property
	def partition_function_dtype(self) -> list[tuple[str,Any]]:
		return np.dtype([('T',float), ('Q',float)])
		
	@property
	def partition_function(self) -> np.ndarray:
		if self._partition_function is None:
			self._partition_function = read.load_line_records_into_structured_array(
				tuple(
					fetch.file_from_cache(
						f'https://www.{x}',
						PKG_CACHE,
						return_fpath=True
					) for x in self.api_partition_function_urls
				),
				self.partition_function_dtype,
				delim = None
			)
		return self._partition_function
	
	
	def cache_data(
			self, 
			cache=PKG_CACHE, 
			refresh : bool = False
	) -> None:
		_lgr.info(f'Downloading data for "{self.d}"')
		n_urls = len(self.all_data_urls)
		for i, data_url in enumerate(self.all_data_urls):
			_lgr.info(f'Fetching file {i}/{n_urls} "{data_url}"')
			fpath = fetch.file_from_cache(
				f'https://www.{data_url}',
				cache = cache,
				return_fpath = True,
				refresh=refresh,
				check_web_first=True
			)
			_lgr.info(f'file fetched into "{fpath}"')
	
	
	def trans_file_precidence(self, fpath : str | Path):
		if isinstance(fpath, str):
			fpath = Path(fpath)
		
		if fpath.suffix == '.bz2':
			trans_fpath = fpath
		else:
			trans_fpath = fpath.with_name(fpath.name+'.bz2')
		
		# Paths at the top will be chosen first
		possible_fpaths = (
			trans_fpath.with_suffix('.bin32'),
			trans_fpath.with_suffix('.bin'),
			trans_fpath.with_suffix('.npy'),
			trans_fpath.with_suffix('.npz'),
			trans_fpath.with_suffix('.bin32.xz'), # faster and more space efficient than `.bz2`
			trans_fpath.with_suffix('.bin32.bz2'),
			trans_fpath.with_suffix('.bin.bz2'),
			trans_fpath.with_suffix(''),
			trans_fpath.with_suffix('.bz2'),
		)
		
		_lgr.debug(f'{trans_fpath=}')
		for new_fpath in possible_fpaths:
			_lgr.debug(f'{new_fpath=}')
			if new_fpath.exists():
				_lgr.debug('EXISTS')
				return new_fpath
			_lgr.debug('DOES NOT EXIST')
			
	
	def iter_transitions(
			self,
			chunk_size : int = 1_000_000,
			trans_files_slice : slice = slice(None),
			trans_fpaths : None | Iterable[Path] = None # If present iterate over these files, otherwise iterate over all of them
	) -> Generator[np.ndarray]:
		
		dt_start = dt.datetime.now()
		_lgr.debug(f'Starting reading transitions at {dt_start}')		
		_lgr.debug(f'Transition files have {self.trans_n_cols} columns.')
		
		if trans_fpaths is None:
			trans_fpaths = (self.trans_file_precidence(fetch.file_from_cache(f'https://www.{x}',cache=PKG_CACHE,return_fpath=True)) for x in self.api_transition_urls[trans_files_slice])
		
		for fpath, chunk in read.files_via_structured_array_chunk(
				trans_fpaths,
				dtype=self.trans_dtype,
				delim=None,
				chunk_size=chunk_size,
				yield_fpath = True,
		):
			if fpath.name.endswith('.bin32') or fpath.name.endswith('.bin32.bz2'):
				chunk['einstein_A'] /= TRANS_STR_FLOAT32_FACTOR
			yield chunk
		
		dt_end = dt.datetime.now()
		_lgr.debug(f'Finished reading transitions at {dt_end}. Took {(dt_end-dt_start).total_seconds()} s.')
	
	def convert_transition_files_to_fmt(
			self, 
			fmt : Literal['.npy', '.bin', '.bin32'],
			chunk_size : int = 1_000_000,
			trans_files_slice : slice = slice(None),
	):
		dt_start = dt.datetime.now()
		_lgr.info(f'Starting to convert transition files at {dt_start}')		
		_lgr.info(f'Transition files have {self.trans_n_cols} columns.')
		
		old_trans_fpaths = (self.trans_file_precidence(fetch.file_from_cache(f'https://www.{x}',cache=PKG_CACHE,return_fpath=True)) for x in self.api_transition_urls[trans_files_slice])
		
		for old_trans_fpath in old_trans_fpaths:
		
			new_trans_fpath = old_trans_fpath.with_name(old_trans_fpath.name + fmt) if old_trans_fpath.suffix == '.trans' else old_trans_fpath.with_suffix(fmt)
			_lgr.info(f'Converting {old_trans_fpath.name=} to {new_trans_fpath.name}')
			
			if new_trans_fpath.exists():
				_lgr.info('Converted file already exists, skipping...')
				continue
			
			dt_split_1 = dt.datetime.now()
			
			try:
				if fmt == '.bin':
					with structured_array.StructuredArrayFile(new_trans_fpath, 'wb') as f:
						for trans_chunk in self.iter_transitions(
								chunk_size=chunk_size,
								trans_fpaths=[old_trans_fpath]
						):
							f.write(trans_chunk)
				
				elif fmt == '.bin32':
					with structured_array.StructuredArrayFile(new_trans_fpath, 'wb') as f:
						new_chunk = np.empty((chunk_size,), dtype=self.trans32_dtype)
						
						for trans_chunk in self.iter_transitions(
								chunk_size=chunk_size,
								trans_fpaths=[old_trans_fpath]
						):
							# 32 bit floating point does not have enough exponent to represent the smallest line strength
							# values. Therefore multiply by a factor to bring them into range. When reading, divide by that
							# factor.
							chunk_slice = tuple(slice(s) for s in trans_chunk.shape)
							trans_chunk['einstein_A'] *= TRANS_STR_FLOAT32_FACTOR
							
							# Check that state ID numbers can fit into 32 bit unsigned integer
							assert np.all(
								(0 <= trans_chunk['lower_id']) 
								& (trans_chunk['lower_id'] <= ((2**32) - 1))
								& (0 <= trans_chunk['upper_id']) 
								& (trans_chunk['upper_id'] <= ((2**32) - 1))
							), f'State ID numbers must be within the range [0,{2**32-1}] to write to {fmt}'
							
							for name in trans_chunk.dtype.names:
								new_chunk[name][chunk_slice] = trans_chunk[name]
							
							f.write(new_chunk)
				
				elif fmt == '.npy':
					result = []
					for trans_chunk in self.iter_transitions(
							chunk_size=chunk_size,
							trans_fpaths=[old_trans_fpath]
					):
							result.append(trans_chunk)
					np.concatenate(result).save(new_trans_fpath)
				else:
					raise RuntimeError(f'Unknown format "{fmt}" to convert transition files to. ')
			except:
				# Remove the new file if anything goes wrong
				if new_trans_fpath.exists():
					new_trans_fpath.unlink()
				raise
			
			dt_split_2 = dt.datetime.now()
			
			_lgr.info(f'Converted {old_trans_fpath.name=} to {new_trans_fpath.name}. Took {(dt_split_2-dt_split_1).total_seconds()} s.')
			
			
		dt_end = dt.datetime.now()
		_lgr.info(f'Finished converting transitions at {dt_end}. Took {(dt_end-dt_start).total_seconds()} s.')
	
	
	def iter_transition_states(
			self,
			chunk_size : int = 1_000_000,
			trans_files_slice : slice = slice(None),
	) -> Generator[np.ndarray]:
		dt_start = dt.datetime.now()
		_lgr.info(f'Starting to get transition state information at {dt_start}')
		
		trans_states_chunk = np.empty((chunk_size,), dtype=self.transition_states_dtype)
		
		#lower_state_indices = np.zeros((chunk_size,), dtype=int)
		#upper_state_indices = np.zeros((chunk_size,), dtype=int)
		
		_lgr.info(f'Transition states are: {" ".join([x for x in self.transition_states_dtype.names])}')
		#states = self.states # local handle for faster access hopefully
		calc_wavenumber_flag = self.trans_n_cols < 4
		
		
		for i, trans_chunk in enumerate(self.iter_transitions(chunk_size=chunk_size, trans_files_slice=trans_files_slice)):
			chunk_slice = slice(None, trans_chunk.size)
			_lgr.debug(f'{trans_chunk.size=} {chunk_slice=} {chunk_size=}')
			
			trans_states_chunk_part = trans_states_chunk[chunk_slice]
			
			for state_name, lower_state_name, upper_state_name in zip(self.states_dtype.names, self.lower_state_names, self.upper_state_names):
				spectral_data_source_helper.calc.numba.transition_states.transition_states_populate_state(
					self.states[state_name],
					trans_chunk['lower_id'],
					trans_chunk['upper_id'],
					trans_states_chunk_part[lower_state_name],
					trans_states_chunk_part[upper_state_name]
				)
				#spectral_data_source_helper.calc.numba.transition_states.transition_states_populate_state.parallel_diagnostics(level=4)
				#raise RuntimeError('Parallel diagnostics')
				#print(f'{trans_states_chunk_part[lower_state_name]=}')
			
			if calc_wavenumber_flag:
				spectral_data_source_helper.calc.numba.transition_states.transition_states_einstein_A_and_wavenumber(
					trans_chunk['einstein_A'],
					trans_states_chunk_part['E\''],
					trans_states_chunk_part['E"'],
					trans_states_chunk_part['einstein_A'],
					trans_states_chunk_part['wavenumber'],
				)
			else:
				trans_states_chunk_part['einstein_A'][...] = trans_chunk['einstein_A']
				trans_states_chunk_part['wavenumber'][...] = trans_chunk['wavenumber']
			
			
			#print(f'{trans_states_chunk_part=}')
			
			yield trans_states_chunk_part
			
			
			"""
			# NOTE: This loop is a bit of a bottleneck
			
			# NOTE: self.state['StateID'] is always one more than the index. Therefore can
			# quickly select indices based upon the state ID numbers in `trans_chunk`
			
			# inplace operations are faster, but not by much
			trans_chunk['lower_id'] -= 1
			trans_chunk['upper_id'] -= 1
			
			#trans_states_chunk[self.lower_state_names][chunk_slice] = states[trans_chunk['lower_id']]
			#trans_states_chunk[self.upper_state_names][chunk_slice] = states[trans_chunk['upper_id']]
			#trans_states_chunk['einstein_A'][chunk_slice] = trans_chunk['einstein_A'][chunk_slice]
			
			# Not sure if these copies do anything
			np.copyto(trans_states_chunk[self.lower_state_names][chunk_slice], states[trans_chunk['lower_id']])
			np.copyto(trans_states_chunk[self.upper_state_names][chunk_slice], states[trans_chunk['upper_id']])
			np.copyto(trans_states_chunk['einstein_A'][chunk_slice], trans_chunk['einstein_A'][chunk_slice])
			
			if calc_wavenumber_flag:
				#trans_states_chunk['wavenumber'] = (trans_states_chunk['E\''] - trans_states_chunk['E"']) # Energy is in cm^{-1} so can just subtract
				# Swapping to `np.subtract` seems to make a big difference
				np.subtract(trans_states_chunk['E\''], trans_states_chunk['E"'], out=trans_states_chunk['wavenumber'])
			else:
				#trans_states_chunk['wavenumber'][chunk_slice] = trans_chunk['wavenumber']
				np.copyto(trans_states_chunk['wavenumber'][chunk_slice], trans_chunk['wavenumber'])
			
			yield trans_states_chunk[chunk_slice]
			"""
		
		dt_end = dt.datetime.now()
		_lgr.info(f'Finished getting transition state information at {dt_end}. Took {(dt_end-dt_start).total_seconds()} s.')
	
	
	def iter_line_data(
			self,
			chunk_size : int = 1_000_000,
			trans_files_slice : slice = slice(None),
	):		
		line_data_chunk = np.empty((chunk_size,), dtype=self.line_data_dtype)
		
		Q_ref = self.partition_function_at(T_ref)
		
		non_broad_names = tuple(x[0] for x in self.line_data_non_broadening_dtype_spec)
		trans_states_col_names = tuple(x for x in self.transition_states_dtype.names)
		cols_from_trans_states = [x for x in non_broad_names if x in trans_states_col_names]
		
		broad_var_names_list = [[f'gamma_{bg_name}', f'n_{bg_name}'] for bg_name in self.broad_gas_names] # broadening coefficent names in order of broadeing gas names
		broad_source_var_names = self.broad_source_var_names
		
		broad_array_gas_slices, broad_array, broad_comp_mask, broad_values = self.broadening_data
		
		
		for trans_states_chunk in self.iter_transition_states(chunk_size=chunk_size, trans_files_slice=trans_files_slice):
			chunk_slice = slice(None,len(trans_states_chunk))
			line_data_chunk_part = line_data_chunk[chunk_slice]
			
			
			trans_states_chunk_bytes = trans_states_chunk.view(
				BYTES_DTYPE
			).reshape(-1,trans_states_chunk.dtype.itemsize // BYTES_DTYPE.itemsize)
			
			
			#print(f'{trans_states_chunk=}')
			
			# When the wavenumber is zero we want to set the einstein_A to zero, and
			# set the wavenumber to 1 to avoid NANs, but still get zero contribution from
			# the line.
			spectral_data_source_helper.calc.numba.copy_pair_if_value_then_const(
				trans_states_chunk['wavenumber'],
				trans_states_chunk['einstein_A'],
				line_data_chunk_part['wavenumber'],
				line_data_chunk_part['einstein_A'],
				source_1_comp_value = 0,
				dest_1_const=1,
				dest_2_const=0,
			)
			
			for name in (x for x in cols_from_trans_states if x not in ('wavenumber', 'einstein_A')):
				spectral_data_source_helper.calc.numba.copy(
					trans_states_chunk[name],
					line_data_chunk_part[name]
				)
			
			spectral_data_source_helper.calc.numba.spec.spec_line_intensity_lte_f(
				T_ref,
				Q_ref,
				line_data_chunk_part['E"'],
				line_data_chunk_part['g_tot\''],
				line_data_chunk_part['einstein_A'],
				line_data_chunk_part['wavenumber'],
				
				out_boltz_pop = line_data_chunk_part['spec_boltz_pop'],
				out_stim_emission = line_data_chunk_part['spec_stim_emission'],
				out = line_data_chunk_part['spec_line_intensity'],
			)
			
			# NOTE: This is still the limiting factor
			for bg_name, broad_var_names, broad_source_name in zip(self.broad_gas_names, broad_var_names_list, broad_source_var_names):
				broad_slice = broad_array_gas_slices[bg_name]
				
				
				
				broad_array_part = broad_array[broad_slice]
				broad_comp_mask_part = broad_comp_mask[broad_slice]
				broad_values_part = broad_values[broad_slice]
				
				fallback_broad_vals = self.default_broad_vals.get(bg_name, None)
				fallback_source_id = BroadeningSourceCode.GAS_DEFAULT
				if fallback_broad_vals is None and len(self.fallback_broad_vals) == 2:
					fallback_broad_vals = self.fallback_broad_vals
					fallback_source_id = BroadeningSourceCode.ISO_DEFAULT
				else:
					fallback_broad_vals = self.emergency_broad_vals
					fallback_source_id = BroadeningSourceCode.EMERGENCY_FALLBACK
				
				
				
				#ldc = np.lib.recfunctions.structured_to_unstructured(line_data_chunk[broad_var_names], float)
				#print(f'{ldc=}')
				
				spectral_data_source_helper.calc.numba.broadening.assign_broadening_parameters(
					trans_states_chunk_bytes,
					broad_array_part,
					broad_comp_mask_part,
					broad_values_part[:,0],
					broad_values_part[:,1],
					BroadeningSourceCode.BROAD_FILE,
					fallback_broad_vals[0],
					fallback_broad_vals[1],
					fallback_source_id,
					line_data_chunk[broad_var_names[0]],
					line_data_chunk[broad_var_names[1]],
					line_data_chunk[broad_source_name]
				)
			
			yield line_data_chunk_part
			
		
	
	def partition_function_at(
			self, 
			T : float | np.ndarray
	) -> np.ndarray:
		return np.interp(T, self.partition_function['T'], self.partition_function['Q'])
	
	
	def get_line_and_continuum_fnames_at_temp(
			self,
			T_arr : np.ndarray,
			temp_fmt : str = 'T{}',
	) -> tuple[tuple[str,...],tuple[str,...],tuple[str,...]]:
		contbins_fnames = tuple(self.datafile_prefix + '_' + temp_fmt.format(T) +'.contbins' for T in T_arr)
		continuum_fnames = tuple(self.datafile_prefix + '_' + temp_fmt.format(T) +'.continuum' for T in T_arr)
		stronglines_fnames = tuple(self.datafile_prefix + '_' + temp_fmt.format(T) +'.stronglines' for T in T_arr)
		
		return (contbins_fnames, continuum_fnames, stronglines_fnames)
	
	@property
	def pseudo_continuum_contribution_dtype_list(self) -> list[tuple[str,Any],...]:
		if self._pseudo_continuum_contribution_dtype_list is None:
			self._pseudo_continuum_contribution_dtype_list =  (
				[
					('line_strength_sum', float),
					('strength_weighted_sum_E"', float),
				] 
				+ [(f'strength_weighted_{broad_param_name}', broad_param_dtype) for broad_param_name, broad_param_dtype in self.broad_dtype]
			)
		return self._pseudo_continuum_contribution_dtype_list
	
	@property
	def pseudo_continuum_contribution_dtype(self) -> np.dtype:
		if self._pseudo_continuum_contribution_dtype is None:
			self._pseudo_continuum_contribution_dtype = np.dtype(self.pseudo_continuum_contribution_dtype_list)
		return self._pseudo_continuum_contribution_dtype
	
	@property
	def pseudo_continuum_broadener_var_name_pairs(self) -> tuple[tuple[str,str],...]:
		return tuple((f'strength_weighted_{broad_param_name}', broad_param_name) for broad_param_name, broad_param_dtype in self.broad_dtype)
	
	@property
	def pseudo_continuum_var_name_pairs(self) -> tuple[tuple[str,str],...]:
		return (
			('strength_weighted_sum_E"', 'E"'),
			*self.pseudo_continuum_broadener_var_name_pairs
		)
	
	
	def iter_lines_and_continuum_at_temp(
			self,
			T : np.ndarray,
			continuum_bin_edges : np.ndarray,
			continuum_line_intensity_cutoff : float = 1E-24,
			chunk_size : int = 1_000_000,
			trans_files_slice : slice = slice(None),
	) -> Generator[tuple[np.ndarray, np.ndarray, tuple[np.ndarray], np.ndarray]]:
		
		n_temps = T.size
		
		Q_ratio =  self.partition_function_at(T_ref) / self.partition_function_at(T)
		
		assert np.all(continuum_bin_edges[:-1] < continuum_bin_edges[1:]), "`continuum_bin_edges` must be monotonically increasing"
		
		cont_n_bin_edges = continuum_bin_edges.size
		cont_n_bins = cont_n_bin_edges-1
		
		pseudo_continuum_contribution = np.zeros((T.size, cont_n_bins), dtype=self.pseudo_continuum_contribution_dtype)
		pseudo_continuum_var_name_pair_tuple = self.pseudo_continuum_var_name_pairs
		
		bin_indices = np.empty((T.size, chunk_size,), dtype=int)
		
		#wavenumber_gt_zero_mask = np.ones((chunk_size,), dtype=bool)
		
		stimulated_emission_ratio = np.empty((T.size, chunk_size,), dtype=float)
		boltz_pop_ratio = np.empty((T.size, chunk_size,), dtype=float)
		
		strong_line_mask = np.empty((T.size, chunk_size,), dtype=bool)
		weak_line_mask = np.empty((T.size, chunk_size,), dtype=bool)
		line_strengths_at_temp = np.empty((T.size, chunk_size,), dtype=float)
		
		n_strong_lines = np.zeros((T.size,), dtype=int)
		n_weak_lines = np.zeros((T.size,), dtype=int)
		n_weak_lines_in_continuum = np.zeros((T.size,), dtype=int)
		n_weak_lines_outside_continuum = np.zeros((T.size,), dtype=int)
	
		n_weak_indices = np.zeros((T.size,), dtype=int)
		
		# Build strutured array views for later
		pcc_struct_names = [x[0] for x in pseudo_continuum_var_name_pair_tuple]
		pcc_view = np.lib.recfunctions.structured_to_unstructured(
			pseudo_continuum_contribution[pcc_struct_names],
			dtype = pseudo_continuum_contribution.dtype.fields[pcc_struct_names[0]][0],
			copy = False
		)
		assert pcc_view.base is not None, "Must be able to build a view of pseudo_continuum_contribution"
		
		# get structured array view names for later
		ldc_struct_names = [x[1] for x in pseudo_continuum_var_name_pair_tuple]
		
		
		for line_data_chunk in self.iter_line_data(chunk_size=chunk_size, trans_files_slice=trans_files_slice):
			
			chunk_slice = slice(None, line_data_chunk.size)
			strong_line_mask_part = strong_line_mask[:, chunk_slice]
			
			stimulated_emission_ratio_part = stimulated_emission_ratio[:,chunk_slice]
			boltz_pop_ratio_part = boltz_pop_ratio[:,chunk_slice]
			line_strengths_at_temp_part = line_strengths_at_temp[:, chunk_slice]
			weak_line_mask_part = weak_line_mask[:, chunk_slice]
			bin_indices_part = bin_indices[:, chunk_slice]
			
			# Set all accumulators to zero
			n_weak_indices.fill(0)
			pseudo_continuum_contribution.fill(0.0)
			strong_line_mask.fill(False)
			stimulated_emission_ratio.fill(1.0)
			
			
			
			ldc_view = np.lib.recfunctions.structured_to_unstructured(
				line_data_chunk[ldc_struct_names],
				dtype = line_data_chunk.dtype.fields[ldc_struct_names[0]][0],
				copy = False
			)
			assert ldc_view.base is not None, "Must be able to build a view of `line_data_chunk`"
			"""
			
			# NOTE: We need to have any entries in `line_data_chunk` that have problematic values to have `spec_line_intensity` set to zero
			# by this point. That way erroneous values will not have any effect on the output.
			
			_lgr.info(f'{line_data_chunk.size=}')
			#print(f'{np.count_nonzero(np.isnan(line_data_chunk['spec_line_intensity']))=}')
			#print(f'{np.count_nonzero(line_data_chunk['wavenumber'] == 0)=}')
			
			# set continuum contribution for this chunk to zero
			
			
			#wavenumber_gt_zero_mask[chunk_slice] = line_data_chunk['wavenumber'] > 0
			
			
			#stimulated_emission_ratio[:,chunk_slice][:, wavenumber_gt_zero_mask[chunk_slice]] = (
			#	one_minus_exp_c2_nu(T_ref,line_data_chunk['wavenumber'][wavenumber_gt_zero_mask[chunk_slice]]) 
			#	/ one_minus_exp_c2_nu(T, line_data_chunk["spec_line_factor_one_minus_exp_wavenumber"][wavenumber_gt_zero_mask[chunk_slice]])
			#)
			
			"""
			spectral_data_source_helper.calc.numba.spec.stimulated_emission_v(
				line_data_chunk['wavenumber'],
				T,
				out = stimulated_emission_ratio_part	
			)
			spectral_data_source_helper.calc.numba.divide_2d_1d(
				stimulated_emission_ratio_part,
				line_data_chunk['spec_stim_emission'],
				out = stimulated_emission_ratio_part
			)
			
			spectral_data_source_helper.calc.numba.spec.boltzmann_population_v(
				line_data_chunk['E"'],
				T,
				out = boltz_pop_ratio_part	
			)
			spectral_data_source_helper.calc.numba.divide_2d_1d(
				boltz_pop_ratio_part,
				line_data_chunk['spec_boltz_pop'],
				out = boltz_pop_ratio_part
			)
			
			spectral_data_source_helper.calc.numba.spec.line_strength_from_temp_ratios(
				line_data_chunk['spec_line_intensity'],
				Q_ratio,
				stimulated_emission_ratio_part,
				boltz_pop_ratio_part,
				out = line_strengths_at_temp_part
			)
			
			spectral_data_source_helper.calc.numba.is_gt_2d_0d(
				line_strengths_at_temp_part,
				continuum_line_intensity_cutoff,
				out = strong_line_mask_part,
			)
			
			spectral_data_source_helper.calc.numba.logical_not_2d(
				strong_line_mask_part,
				out = weak_line_mask_part
			)
			
			spectral_data_source_helper.calc.numba.count_true_2d_to_1d(
				strong_line_mask_part,
				out_count=n_strong_lines,
			)
			
			#print(f'{np.count_nonzero(strong_line_mask_part, axis=1)=}')
			n_weak_lines = line_data_chunk.size - n_strong_lines
			
			#print(f'{np.count_nonzero(weak_line_mask_part)=}')
			
			spectral_data_source_helper.calc.numba.get_valid_bin_indices_of_sets(
				continuum_bin_edges,
				line_data_chunk['wavenumber'],
				weak_line_mask_part,
				out_indices = bin_indices_part,
				out_n_indices = n_weak_indices,
			)
			
			#print(f'{n_weak_indices=}')
			#print(f'{bin_indices_part=}')
			#print(f'{np.count_nonzero(weak_line_mask_part)=}')
			
			spectral_data_source_helper.calc.numba.count_true_2d_to_1d(
				weak_line_mask_part,
				out_count = n_weak_lines_in_continuum,
			)
			
			np.subtract(n_weak_lines, n_weak_lines_in_continuum, out=n_weak_lines_outside_continuum)
			
			_lgr.info(f'{n_weak_lines_in_continuum=} {n_weak_lines_outside_continuum=}')
			
			
			spectral_data_source_helper.calc.numba.spec.accumulate_pseudocontinuum(
				weak_line_mask_part,
				bin_indices_part,
				line_strengths_at_temp_part,
				pseudo_continuum_contribution['line_strength_sum'],
				ldc_view,
				pcc_view
			)
			
			
			
			yield (
				n_strong_lines, 
				n_weak_lines_in_continuum, 
				(line_data_chunk[strong_line_mask_part[j]] for j in range(n_temps)), 
				pseudo_continuum_contribution
			)
			_lgr.info('strong lines and continuum data outputted')
			
				
			
			
			
			
			
	
	