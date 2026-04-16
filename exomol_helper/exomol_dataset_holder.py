

import json
import dataclasses as dc
from typing import Any, Generator
import datetime as dt

import numpy as np

from .utils import fetch
from .utils import read

from .cfg.const import (
	EXOMOL_API_URL_FMT,
	EXOMOL_URL_PREFIX,
	EXOMOL_CACHE,
	EXOMOL_STATE_FILE_ENDINGS,
	EXOMOL_TRANSITION_FILE_ENDINGS,
	EXOMOL_API_INTERNAL_URL_START,
	T_ref,
)

from exomol_helper.calc.spec_line_intensity import spec_line_intensity_lte

import exomol_helper.qn_set_manager
import exomol_helper.broad_file_manager

from exomol_helper.cfg.log import progress_lgr
from exomol_helper.cfg.log import pkg_logger as _lgr

from exomol_helper.datatypes import (
	ExomolDatasetInfo,
)

from exomol_helper.exomol_index_types import (
	mol_formula_to_api_mol,
	ExomolIsotopeDef,
)




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
	_default_broad_vals : None | dict[str,tuple[float,float]] = None
	_fallback_broad_vals : None | tuple[float,float] = None
	emergency_broad_vals : tuple[float,float] = (0.07, 0.5) # (gamma, n) to use when no other values are present (taken from PyExoCross)
	_partition_function : None | np.ndarray = None
	_broad_map : None | dict[str,dict[str,dict[tuple[Any,...],tuple[float,float]]]] = None
	_possible_qn_sets : None | dict[str,list[str]] = None
	
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
					self._isotope_def = ExomolIsotopeDef(mol_formula=self.d.mol_formula, **json.loads(fetch.file_from_cache(isotope_def_url, cache=EXOMOL_CACHE)))
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
		api_json = json.loads(fetch.file_from_cache(EXOMOL_API_URL_FMT.format(mol_formula_to_api_mol(self.d.mol_formula)), cache=EXOMOL_CACHE))
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
			self._api_broad_urls = exomol_helper.broad_file_manager.search_broad_files_for(self.d.mol_formula, self.d.iso_slug)
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
	def states_dtype(self) -> list[tuple[str,Any],...]:
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
		return [x[0].split(':')[-1] for x in self.states_dtype]
	
	@property
	def states(self) -> np.ndarray:
		if self._states is None:
			dt_start = dt.datetime.now()
			_lgr.info(f'Starting to load states at {dt_start}')
			#self._states = read.load_line_records_into_structured_array(
			#	[fetch.file_from_cache(f'https://www.{x}',cache=EXOMOL_CACHE,return_fpath=True) for x in self.api_states_urls],
			#	dtype=self.states_dtype,
			#	shape=self.states_shape,
			#	delim=None
			#)
			states_url = self.api_states_urls[0]
			if states_url.endswith('.bz2'):
				states_numpy_fpath = (EXOMOL_CACHE / f'{self.api_states_urls[0]}').with_suffix('.npz')
			else:
				states_numpy_fpath = (EXOMOL_CACHE / f'{self.api_states_urls[0]}.npz')
			
			if states_numpy_fpath.exists():
				self._states = np.load(states_numpy_fpath)['states']
			else:
				# load from web/cache
				self._states = np.loadtxt(
					fetch.file_from_cache(f'https://www.{self.api_states_urls[0]}',cache=EXOMOL_CACHE,return_fpath=True), 
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
			for aline in read.iter_line_records([fetch.file_from_cache(f'https://www.{self.api_transition_urls[0]}',cache=EXOMOL_CACHE,return_fpath=True)]):
				self._trans_n_cols = len(aline.split())
				break
		return self._trans_n_cols
	
	@property
	def trans_dtype(self) -> list[tuple[str,Any]]:
		if self._trans_dtype is None:
			self._trans_dtype = [('upper_id',int),('lower_id',int), ('einstein_A', float), ('wavenumber',float)][:self.trans_n_cols]
		return self._trans_dtype
	
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
	def broad_gas_names(self) -> tuple[str,...]:
		if self._broad_gas_names is None:
			self._broad_gas_names = tuple(self.api_broad_urls.keys())
		return self._broad_gas_names
	
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
		
		lower_state_dtype = tuple((x, y[1]) for x,y in zip(self.lower_state_names, states_dtype))
		upper_state_dtype = tuple((x, y[1]) for x,y in zip(self.upper_state_names, states_dtype))
		
		dtype = [
			('einstein_A', float),
			('wavenumber', float),
			*lower_state_dtype,
			*upper_state_dtype,
		]
		return dtype
	
	@property
	def line_data_non_broadening_dtype(self) -> list[tuple[str,Any]]:
		return [
			('spec_line_intensity', float), # Spectral line intensity (calculated from other properties)
			('wavenumber', float), # wavenumber of line center
			('einstein_A', float), # einstein A coefficient
			('E"', float), # lower state energy (in cm^{-1})
			('E\'', float), # upper state energy (in cm^{-1})
			('g_tot"', int), # lower state degeneracy
			('g_tot\'', int), # upper state degeneracy
		]
	
	@property
	def line_data_dtype(self) -> list[tuple[str,Any]]:
	
		dtype = [
			*self.line_data_non_broadening_dtype,
			*tuple((f'gamma_{bg_name}', float) for bg_name in self.broad_gas_names),
			*tuple((f'n_{bg_name}', float) for bg_name in self.broad_gas_names),
		]
		
		return dtype
	
	@property
	def possible_qn_sets(self) -> dict[str, list[str]]:
		if self._possible_qn_sets is None:
			transition_state_names = self.transition_state_names
			self._possible_qn_sets = dict((k,['J"',*v]) for k,v in exomol_helper.qn_set_manager.qn_set.items() if all(x in transition_state_names for x in v))
			#_lgr.debug(f'{self._possible_qn_sets=}')
		return self._possible_qn_sets
	
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
			
			
			
			# Build `broad_map` for this dataset.
			for bg_name, broad_url in self._api_broad_urls.items():
				fpath = fetch.file_from_cache(broad_url, cache=EXOMOL_CACHE, return_fpath=True)
				
				with open(fpath, 'r') as f:
					self._broad_map.setdefault(bg_name, dict())
					for aline in f:
						split_line = aline.split()
						code, gamma, temp_exp, Jpp = split_line[:4]
						quantum_number_strings = split_line[4:]
						Jpp = int(Jpp)
					
						ts_dtype_dict = dict(self.transition_states_dtype)
						quantum_numbers = []
						for (name, value_string) in zip(self.possible_qn_sets[code][1:], quantum_number_strings):
							type_converter = ts_dtype_dict[name]
							quantum_numbers.append(type_converter(value_string) if not isinstance(type_converter, str) else value_string)
						
						qn_values = (Jpp,*quantum_numbers)
						dtype = [('J"', int)] + [(name,ts_dtype_dict[name]) for name in self.possible_qn_sets[code][1:]]
						self._broad_map[bg_name].setdefault(code, dict())[qn_values] = (
							np.array(qn_values, dtype=dtype),
							(gamma, temp_exp)
						)
		return self._broad_map
	
	@property
	def partition_function_dtype(self) -> list[tuple[str,Any]]:
		return [('T',float), ('Q',float)]
		
	@property
	def partition_function(self) -> np.ndarray:
		if self._partition_function is None:
			self._partition_function = read.load_line_records_into_structured_array(
				tuple(
					fetch.file_from_cache(
						f'https://www.{x}',
						EXOMOL_CACHE,
						return_fpath=True
					) for x in self.api_partition_function_urls
				),
				self.partition_function_dtype,
				delim = None
			)
		return self._partition_function
	
	
	def cache_data(
			self, 
			cache=EXOMOL_CACHE, 
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
	
	
	def iter_transitions(
			self,
			chunk_size : int = 1_000_000,
			trans_files_slice : slice = slice(None),
	) -> Generator[np.ndarray]:
		
		dt_start = dt.datetime.now()
		_lgr.debug(f'Starting reading transitions at {dt_start}')		
		_lgr.debug(f'Transition files have {self.trans_n_cols} columns.')
		
		trans_urls = (fetch.file_from_cache(f'https://www.{x}',cache=EXOMOL_CACHE,return_fpath=True) for x in self.api_transition_urls[trans_files_slice])
		yield from read.iter_line_records_via_structured_array_chunk(
				trans_urls,
				dtype=self.trans_dtype,
				delim=None,
				chunk_size=chunk_size,
		)
		
		dt_end = dt.datetime.now()
		_lgr.debug(f'Finished reading transitions at {dt_end}. Took {(dt_end-dt_start).total_seconds()} s.')
	
	
	def iter_transition_states(
			self,
			chunk_size : int = 1_000_000,
			trans_files_slice : slice = slice(None),
	) -> Generator[np.ndarray]:
		dt_start = dt.datetime.now()
		_lgr.info(f'Starting to get transition state information at {dt_start}')
		
		trans_states_chunk = np.empty((chunk_size,), dtype=self.transition_states_dtype)
		lower_state_indices = np.zeros((chunk_size,), dtype=int)
		upper_state_indices = np.zeros((chunk_size,), dtype=int)
		#lower_state_mask = np.zeros((self.states.size,), dtype=bool)
		#upper_state_mask = np.zeros((self.states.size,), dtype=bool)
		
		_lgr.info(f'Transition states are: {" ".join([x[0] for x in self.transition_states_dtype])}')
		states = self.states # local handle for faster access hopefully
		calc_wavenumber_flag = self.trans_n_cols < 4
		
		n_transitions_processed = 0
		
		for i, trans_chunk in enumerate(self.iter_transitions(chunk_size=chunk_size, trans_files_slice=trans_files_slice)):
			chunk_slice = slice(None, trans_chunk.size)
			#print(f'{trans_chunk.size=} {chunk_slice=} {chunk_size=} {lower_state_indices.shape=}')
			
			# NOTE: self.state['StateID'] is always one more than the index. Therefore can
			# quickly select indices based upon the state ID numbers in `trans_chunk`
			lower_state_indices[chunk_slice] = trans_chunk['lower_id'] - 1
			upper_state_indices[chunk_slice] = trans_chunk['upper_id'] - 1
			
			trans_states_chunk[self.lower_state_names][chunk_slice] = states[lower_state_indices[chunk_slice]]
			trans_states_chunk[self.upper_state_names][chunk_slice] = states[upper_state_indices[chunk_slice]]
			
			trans_states_chunk['einstein_A'][chunk_slice] = trans_chunk['einstein_A'][chunk_slice]
			
			if calc_wavenumber_flag:
				trans_states_chunk['wavenumber'] = (trans_states_chunk['E\''] - trans_states_chunk['E"']) # Energy is in cm^{-1} so can just subtract
			else:
				trans_states_chunk['wavenumber'][chunk_slice] = trans_chunk['wavenumber']
			
			n_transitions_processed += trans_chunk.size
			
			if progress_lgr.is_ready():
				dt_split = dt.datetime.now()
				dt_split_delta = (dt_split - dt_start).total_seconds()
				trans_per_sec = n_transitions_processed / dt_split_delta
				trans_remaining = (self.n_transitions - n_transitions_processed)
				frac_complete = n_transitions_processed / self.n_transitions
				est_time_remaining = dt.timedelta(seconds=trans_remaining / trans_per_sec)
				est_time_remaining_str = f'{est_time_remaining.days}D {est_time_remaining.seconds//3600}H {(est_time_remaining.seconds %3600)//60}M {est_time_remaining.seconds%60}s'
				est_completion_dt = dt_start + est_time_remaining
				
				progress_lgr.info(f'{i=} Processed {n_transitions_processed}/{self.n_transitions} transitions [{100*frac_complete: 8.4f} %] in {dt_split_delta} s [{trans_per_sec: 8.2E} trans/s]  Est. time remaining {est_time_remaining_str}. Est. completion at {est_completion_dt}')
		
			yield trans_states_chunk[chunk_slice]
		
		dt_end = dt.datetime.now()
		_lgr.info(f'Finished getting transition state information at {dt_end}. Took {(dt_end-dt_start).total_seconds()} s.')
	
	
	def iter_line_data(
			self,
			chunk_size : int = 1_000_000,
			trans_files_slice : slice = slice(None),
	):
		_lgr.info(f'{chunk_size=}')
		
		line_data_chunk = np.empty((chunk_size,), dtype=self.line_data_dtype)
		qn_acc_code_mask = np.zeros((chunk_size,), dtype=bool)
		qn_code_mask = np.zeros((chunk_size,), dtype=bool)
		
		
		Q_ref = self.partition_function_at(T_ref)
		
		non_broad_names = tuple(x[0] for x in self.line_data_non_broadening_dtype)
		trans_states_col_names = tuple(x[0] for x in self.transition_states_dtype)
		cols_from_trans_states = [x for x in non_broad_names if x in trans_states_col_names]
		
		broad_var_names_list = [[f'gamma_{bg_name}', f'n_{bg_name}'] for bg_name in self.broad_gas_names] # broadening coefficent names in order of broadeing gas names
		
		for trans_states_chunk in self.iter_transition_states(chunk_size=chunk_size, trans_files_slice=trans_files_slice):
			chunk_slice = slice(None,len(trans_states_chunk))
			
			# Some line data is a straight copy from `trans_states_chunk`
			line_data_chunk[cols_from_trans_states][chunk_slice] = trans_states_chunk[cols_from_trans_states][chunk_slice]
			
			# Some line data is calculated
			spec_line_intensity_lte(
				T_ref,
				Q_ref,
				line_data_chunk['E"'][chunk_slice],
				line_data_chunk['g_tot\''][chunk_slice],
				line_data_chunk['einstein_A'][chunk_slice],
				line_data_chunk['wavenumber'][chunk_slice],
				out = line_data_chunk['spec_line_intensity'][chunk_slice],
			)
			
			# Broadening coefficients must be matched to valid combinations of quantum numbers
			for bg_name, broad_var_names in zip(self.broad_gas_names, broad_var_names_list):
				qn_acc_code_mask[...] = False # reset accumulator for each broadening gas
				
				for qn_code, qn_value_to_broad_map in self.broad_map[bg_name].items():
					qn_code_var_names = self.possible_qn_sets[qn_code]
					
					for qn_vals, (qn_comparator, broad_var_vals) in qn_value_to_broad_map.items():
						#_lgr.debug(f'{qn_vals=}')
						#_lgr.debug(f'{trans_states_chunk[qn_code_var_names]=}')
						#_lgr.debug(f'{qn_comparator=}')
						
						# select all lines that could potentially be valid for the current `qn_code` and `qn_vals`
						qn_code_mask[chunk_slice] = trans_states_chunk[qn_code_var_names] == qn_comparator
						
						# de-select all lines that have already been assigned broadening coefficients
						# as earlier entries take precidence over later entries.
						# This gives us the actually valid lines
						qn_code_mask[chunk_slice] &= (~qn_acc_code_mask[chunk_slice])
						
						# update the accumulator to include the actually valid lines we just worked out
						qn_acc_code_mask[chunk_slice] |= qn_code_mask[chunk_slice]
						
						#_lgr.debug(f'{qn_code_mask[chunk_slice].size=}')
						#_lgr.debug(f'{np.count_nonzero(qn_code_mask[chunk_slice])=}')
						#_lgr.debug(f'{np.count_nonzero(qn_acc_code_mask[chunk_slice])=}')
						
						line_data_chunk[broad_var_names][chunk_slice][qn_code_mask[chunk_slice]] = broad_var_vals
				
				# lines that were not selected by `qn_code` and `qn_vals` in `broad_map` should use default values
				# for their broadening coefficients. 
				
				# Get default broadening coefficients for the current broadening gas, if we have defaults for the gas
				# use them, otherwise use defaults for the dataset, if no defaults for the dataaset exist then use the
				# emergency values
				default_broad_vals = self.default_broad_vals.get(bg_name, None)
				if default_broad_vals is not None:
					line_data_chunk[broad_var_names][chunk_slice][~(qn_acc_code_mask[chunk_slice])] = default_broad_vals
				elif len(self.fallback_broad_vals) == 2:
					line_data_chunk[broad_var_names][chunk_slice][~(qn_acc_code_mask[chunk_slice])] = self.fallback_broad_vals
				else:
					line_data_chunk[broad_var_names][chunk_slice][~(qn_acc_code_mask[chunk_slice])] = self.emergency_broad_vals
			
			
			yield line_data_chunk[chunk_slice]

	
	def partition_function_at(
			self, 
			T : float | np.ndarray
	) -> np.ndarray:
		return np.interp(T, self.partition_function['T'], self.partition_function['Q'])
	
	
	
	