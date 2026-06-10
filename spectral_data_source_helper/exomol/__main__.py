
import sys
import argparse as ap
from typing import Any, Literal
from pathlib import Path
import datetime as dt

import numpy as np

from spectral_data_source_helper.cfg.const import (
	CHUNK_SIZE,
	REPO_LOCAL,
	T_ref,
	P_ref,
)

from spectral_data_source_helper.datatypes import (
	ExomolDatasetInfo,
)

from spectral_data_source_helper.exomol_dataset_holder import ExomolDatasetHolder

from spectral_data_source_helper.exomol import (
	exomol_all_dataset_name_dict,
)

import spectral_data_source_helper.utils
import spectral_data_source_helper.utils.dtype
import spectral_data_source_helper.utils.structured_array

import spectral_data_source_helper.calc.pseudo_continuum
import spectral_data_source_helper.calc.spec

import logging
from spectral_data_source_helper.cfg.log import pkg_logger, progress_lgr


mol_iso_dataset_dict = exomol_all_dataset_name_dict()

all_molecules = tuple(sorted(mol_iso_dataset_dict.keys()))

all_isotopes = []
for mol, isos in mol_iso_dataset_dict.items():
	all_isotopes.extend(isos.keys())
all_isotopes = tuple(all_isotopes)

all_dataset_names = []
for mol, isos in mol_iso_dataset_dict.items():
	for ds_info in isos.values():
		all_dataset_names.extend(ds_info.dataset_names)
all_dataset_names = tuple(all_dataset_names)


def exomol_select_datasets(
		molecules : None | list[str], 
		isotopes : None | list[str], 
		dataset_names : None | list[str],
) -> tuple[Any]:
	
	dataset_selectors = []
	
	mols = sorted(molecules.pop(molecules.index(a_mol)) for a_mol in mol_iso_dataset_dict.keys() if a_mol in molecules)
	
	
	for mol in mols:
		#print(f'{mol=}')
		
		#print(f'{isotopes=}')
		# want the isotopes for this molecule only
		isos = sorted(isotopes.pop(isotopes.index(a_iso)) for a_iso in mol_iso_dataset_dict[mol].keys() if a_iso in isotopes)
			
		for iso in isos:
			# want the dataset names for this isotope only
			
			ds_names = sorted(dataset_names.pop(dataset_names.index(a_ds_name)) for a_ds_name in mol_iso_dataset_dict[mol][iso].dataset_names if a_ds_name in dataset_names)
			
			for dataset_name in ds_names:
				dataset_selectors.append(
					ExomolDatasetInfo(
						mol,
						iso,
						mol_iso_dataset_dict[mol][iso].iso_slug,
						dataset_name
					)
				)
	
	err_msg = []
	if len(molecules) > 0:
		err_msg.append(f'Specified unknown {molecules=}')
	
	if len(isotopes) > 0:
		err_msg.append(f'Specified unknown {isotopes=}')
	
	if len(dataset_names) > 0:
		err_msg.append(f'Specified unkown {dataset_names=}')
	
	if len(dataset_selectors) == 0:
		err_msg.append('No datasets were selected with passed molecules, isotopes, and dataset names.')
	
	if len(err_msg) > 0:
		raise RuntimeError(' '.join(err_msg))
	
	return sorted(dataset_selectors)


def exomol_download(
		dataset_holders : list[ExomolDatasetHolder],
		refresh : bool
):
	n_datasets = len(dataset_holders)
	
	for i, ds_holder in enumerate(dataset_holders):
		if ds_holder.is_external:
			print(f'Dataset [{i}/{n_datasets}] {ds_holder.d} is external, skipping...')
			continue
		
		print(f'Downloading dataset [{i}/{n_datasets}]...')
		ds_holder.cache_data()
		print(f'Dataset {i} downloaded.')


def exomol_list(
		dataset_holders : list[ExomolDatasetHolder],
):
	pkg_logger.setLevel(logging.WARN) # SET LOGGING SO WE HAVE CLEAR OUTPUT
	print(f'The following {len(dataset_holders)} datasets are selected:')
	for ds_holder in dataset_holders:
		print(f'  {ds_holder.short_info_str}')


def exomol_tree(
		dataset_holders : list[ExomolDatasetHolder],
		indent_0 : str = ' |  ',
		indent_1 : str = ' |- ',
):
	mols = tuple(x.d.mol_formula for x in dataset_holders)
	
	tree = dict()
	for mol in mols:
		tree[mol] = dict()
		for iso_of_mol in (x.d.iso_formula for x in dataset_holders if x.d.mol_formula == mol):
			tree[mol][iso_of_mol] = []
			for dataset_of_iso in (x.d.dataset_name+(' [EXTERNAL]' if x.is_external else '') for x in dataset_holders if x.d.iso_formula == iso_of_mol):
				tree[mol][iso_of_mol].append(dataset_of_iso)
	
	# Print the tree
	print('#= EXOMOL INDEX TREE=======================#')
	print('        [EXTERNAL] - denotes external dataset')
	print('[EXOMOL]')
	for mol, isos in tree.items():
		print(f'{indent_1}{mol}')
		for i, (iso, dsets) in enumerate(isos.items()):
			print(f'{indent_0}{indent_1}{iso}')
			for j, dset in enumerate(dsets):
					print(f'{indent_0}{indent_0}{indent_1}{dset}')
	print('#------------------------------------------#')


def exomol_states(
		dataset_holders : list[ExomolDatasetHolder],
		start : int = 0,
		stop : int = 10,
		step : int = 1,
):
	pkg_logger.setLevel(logging.WARN) # SET LOGGING SO WE HAVE CLEAR OUTPUT
	slice_to_print = slice(start, None if stop == 0 else (stop+1), step)
	for ds_holder in dataset_holders:
		print(f'States for dataset {ds_holder.short_info_str}')
		
		n_states = ds_holder.states_shape
		print(f'    number: {n_states}')
		
		print(f'    Minimum ID: {np.min(ds_holder.states['StateID'])} Maximum ID: {np.max(ds_holder.states['StateID'])}')
		
		states_dtype = ds_holder.states_dtype
		
		#states_names = ' '.join(x[0] for x in states_dtype)
		states_names = ' '.join(ds_holder.states_short_names)
		print(f'    names: {states_names}')
		
		states_types = ' '.join(spectral_data_source_helper.utils.dtype.field_type_strings(states_dtype))
		print(f'    types: {states_types}')
		
		print(f'    Printing states in slice {slice_to_print}:')
		
		for state in ds_holder.states[slice_to_print]:
			print(f'        {state}')


def exomol_trans(
		dataset_holders : list[ExomolDatasetHolder],
		n_to_print : int = 10,
		chunk_size : int = CHUNK_SIZE,
):
	import spectral_data_source_helper.cfg.log # for later
	
	pkg_logger.setLevel(logging.WARN) # SET LOGGING SO WE HAVE CLEAR OUTPUT
	
	for ds_holder in dataset_holders:
		print(f'Transitions for dataset {ds_holder.short_info_str}')
		
		dtype = ds_holder.trans_dtype
		
		names = ' '.join(x for x in dtype.names)
		print(f'    names: {names}')
		
		types = ' '.join(f'{x[0].type}' for x in dtype.fields.values())
		print(f'    types: {types}')
		
		n_files = len(ds_holder.api_transition_urls)
		
		print(f'    Transition files ({n_files} in total):')
		for afile in ds_holder.api_transition_urls:
			print(f'        {afile}')
		
		print('    Transition reading speed check:')
		spectral_data_source_helper.cfg.log.progress_stream_hdlr.terminator='\n'
		
		n_seconds = 30
		dt_start = dt.datetime.now()
		for j, transition_chunk in enumerate(ds_holder.iter_transitions(chunk_size=chunk_size)):
			dt_split = dt.datetime.now()
			if (dt_split - dt_start).total_seconds() >= n_seconds:
				break
		
		spectral_data_source_helper.cfg.log.progress_stream_hdlr.terminator='\r'
		
		print(f'    First {n_to_print} transitions ({ds_holder.n_transitions} in total):')
		do_stop = False
		for j, transition_chunk in enumerate(ds_holder.iter_transitions(chunk_size=chunk_size)):
			for i, transition in enumerate(transition_chunk):
				print(f'        {transition}')
				if (j*chunk_size + i) >= (n_to_print-1):
					do_stop=True
					break
			
			if do_stop:
				break
		
		print(f'    Transition states columns {" ".join((x for x in ds_holder.transition_states_dtype.names))}')
		print(f'    First {n_to_print} transition states information:')
		do_stop = False
		chunk_size = CHUNK_SIZE
		for j, trans_states_chunk in enumerate(ds_holder.iter_transition_states(chunk_size=chunk_size)):
			for i, trans_states in enumerate(trans_states_chunk):
				print(f'        {trans_states}')
				if (j*chunk_size + i) >= (n_to_print-1):
					do_stop=True
					break
			
			if do_stop:
				break
		
		print(f'    Line data columns: {" ".join([x for x in ds_holder.line_data_dtype.names])}')
		print(f'    First {n_to_print} line data:')
		do_stop = False
		chunk_size = CHUNK_SIZE
		for j, line_data_chunk in enumerate(ds_holder.iter_line_data(chunk_size=chunk_size)):
			for i, line_data in enumerate(line_data_chunk):
				print(f'        {line_data}')
				if (j*chunk_size + i) >= (n_to_print-1):
					do_stop=True
					break
			
			if do_stop:
				break


def exomol_calc_line_data(
		dataset_holders : list[ExomolDatasetHolder],
		chunk_size : int = 1_000_000,
):
	pkg_logger.setLevel(logging.INFO) # SET LOGGING SO WE HAVE CLEAR OUTPUT
	
	for ds_holder in dataset_holders:
		with open(REPO_LOCAL / f'{ds_holder.datafile_prefix}.lines', 'wb') as f:
			# Write dtype header
			f.write(spectral_data_source_helper.utils.dtype.to_string(ds_holder.line_data_dtype).encode('ascii'))
			
			# Write line data
			for line_data_chunk in ds_holder.iter_line_data(chunk_size=chunk_size):
				line_data_chunk.tofile(f)


def exomol_read_line_data(
		dataset_holders : list[ExomolDatasetHolder],
		start : int = 0,
		stop : int = 10,
		step : int = 1,
):

	line_data_slice = slice(start, None if stop==0 else stop+1, step)
	
	for ds_holder in dataset_holders:
		print(f'Reading saved line data for {ds_holder.short_info_str}')
	
		line_data_fpath = REPO_LOCAL / f'{ds_holder.datafile_prefix}.lines'
		
		line_data = None
		use_dtype = None
		
		print('    Found the following files:')
		if line_data_fpath.exists():
			print(f'        line data : {line_data_fpath}')
		else:
			pkg_logger.error('Could not find line data file, exiting...')
			return
		
		
		with open(line_data_fpath, 'rb') as f:
			
			print('    Reading header for line data.')
			# read until balanced curly brackets, this is prob. inefficient but only happens once per file
			hdr_fail_size = 32
			hdr_part = f.read(1)
			while len(hdr_part) < hdr_fail_size or (hdr_part.count(b'{') !=hdr_part.count(b'}')) :
				hdr_part += f.read(1)
			
			if (hdr_part.count(b'{') == hdr_part.count(b'}')):
				use_dtype = spectral_data_source_helper.utils.dtype.from_string(hdr_part.decode('ascii'))
			else:
				raise RuntimeError(f'Could not read header. Got "{hdr_part}"')
			
			print('    Reading line data.')
			line_data = np.fromfile(f, dtype=use_dtype)
		
		
		if line_data is None:
			pkg_logger.error(f'Something went wrong when reading {line_data_fpath}. Exiting...')
			return
		print('    Line data has the following columns:')
		print(f'        {" | ".join(use_dtype.names)}')
		print(f'    Printing line data slice {line_data_slice} of {line_data.size} rows.')
		for line_data_record in line_data[line_data_slice]:
			print(f'        {line_data_record}')




def exomol_calc_continuum(
		dataset_holders : list[ExomolDatasetHolder],
		temperature : list[float] = (T_ref,),
		continuum_line_intensity_cutoff : float = 1E-24,
		continuum_wavenumber_min : float = 0.00001,
		continuum_wavenumber_max : float = 100_000,
		continuum_n_bins : int = 1_000,
		continuum_bin_spacing : Literal['lin', 'log'] = 'lin',
		chunk_size : int = CHUNK_SIZE,
):
	pkg_logger.setLevel(logging.WARN) # SET LOGGING SO WE HAVE CLEAR OUTPUT
	progress_lgr.setLevel(logging.INFO) # SET LOGGING SO WE HAVE CLEAR OUTPUT
	
	temperature_arr = np.array(temperature, dtype=float)
	
	if continuum_bin_spacing == 'lin':
		continuum_bin_edges = np.linspace(continuum_wavenumber_min, continuum_wavenumber_max, continuum_n_bins+1, endpoint=True)
	elif continuum_bin_spacing == 'log':
		continuum_bin_edges = np.geomspace(continuum_wavenumber_min, continuum_wavenumber_max, continuum_n_bins+1, endpoint=True)
	else:
		raise RuntimeError(f'Unknown value for {continuum_bin_spacing=}')
	
	
	
	for ds_holder in dataset_holders:
	
		# Create a continuum for each temperature
		pseudo_continuums = np.zeros((*temperature_arr.shape, continuum_n_bins,), dtype=ds_holder.pseudo_continuum_contribution_dtype)
		total_strong_lines = np.zeros(temperature_arr.shape, dtype=int)
		total_weak_lines_in_continuum = np.zeros(temperature_arr.shape, dtype=int)
	
	
		contbins_fpaths, continuum_fpaths, stronglines_fpaths = (tuple(REPO_LOCAL / fname for fname in fnames) for fnames in ds_holder.get_line_and_continuum_fnames_at_temp(temperature_arr))
	
		dt_start = dt.datetime.now()
		dt_split_2 = dt_start
	
		# Write the continuum bins to their files
		for contbins_fpath in contbins_fpaths:
			with open(contbins_fpath, 'wb') as f:
				continuum_bin_edges.tofile(f)
			print(f'Written continum bin edge data to "{str(contbins_fpath)}"')
		
		try:
			continuum_fhdls = tuple(spectral_data_source_helper.utils.structured_array.StructuredArrayFile(fpath,'wb') for fpath in continuum_fpaths)
			stronglines_fhdls = tuple(spectral_data_source_helper.utils.structured_array.StructuredArrayFile(fpath,'wb') for fpath in stronglines_fpaths)
		
			for n_strong_lines, n_weak_lines_in_continuum, strong_lines_chunks, pseudo_continuum_contributions in ds_holder.iter_lines_and_continuum_at_temp(
				T = temperature_arr, 
				continuum_bin_edges = continuum_bin_edges,
				continuum_line_intensity_cutoff=continuum_line_intensity_cutoff,
				chunk_size=chunk_size,
				trans_files_slice=slice(None),
				#trans_files_slice=slice(None,3),
			):
				
				total_strong_lines += n_strong_lines
				total_weak_lines_in_continuum += n_weak_lines_in_continuum
				
				dt_start_write = dt.datetime.now()
				
				for slc, fhdl in zip(strong_lines_chunks, stronglines_fhdls):
					fhdl.write(slc)
				
				# Have to do summation field-by-field as numpy does not know how to do it for structured arrays
				for field_name in pseudo_continuums.dtype.fields:
					pseudo_continuums[field_name] += pseudo_continuum_contributions[field_name]
				
				# Write out continuum data-so-far to file
				for i, (pc_part, fhdl) in enumerate(zip(pseudo_continuums, continuum_fhdls)):
					fhdl.write(pseudo_continuums[i])
					fhdl.seek(0,0)
				
				dt_split = dt.datetime.now()
				dt_elapsed_delta = dt_split - dt_start
				dt_elapsed_str = f'{dt_elapsed_delta.days}D {dt_elapsed_delta.seconds//3600}H {(dt_elapsed_delta.seconds %3600)//60}M {dt_elapsed_delta.seconds%60}s'
				
				if (dt_split - dt_split_2).total_seconds() > 1:
					dt_split_2 = dt.datetime.now()
					print(f'Writing data to files took {1000*(dt_split - dt_start_write).total_seconds()} ms.')
					
					print('     Temperature | num. strong lines | num. weak lines | total strong lines | total weak lines')
					for temp, n_sl, n_wl, t_sl, t_wl in zip(temperature_arr, n_strong_lines, n_weak_lines_in_continuum, total_strong_lines, total_weak_lines_in_continuum):
						print(f'     {temp:11.2f} | {n_sl:17d} | {n_wl:16d} | {t_sl:18d} | {t_wl:16d}')
					
					print(f'Elapsed time: {dt_elapsed_str}')
				
				
		
		finally:
			for fhdl in continuum_fhdls:
				fhdl.close()
			for fhdl in stronglines_fhdls:
				fhdl.close()



def exomol_read_continuum_data(
		dataset_holders : list[ExomolDatasetHolder],
		fname : None | str = None,
		start : int = 0,
		stop : int = 10,
		step : int = 1,
		temp : None | float = None,
		eps : None | float = None,
		extra_plots : int = 0,
):
	assert fname is not None, "Must have name of files to work with"
		
	pkg_logger.setLevel(logging.INFO)
	progress_lgr.setLevel(logging.INFO)

	line_data_slice = slice(start, None if stop==0 else stop+1, step)
	
	for ds_holder in dataset_holders:
		print(f'Reading saved continuum data for {ds_holder.short_info_str}')
		fpath = Path(fname)
		print(f'{fpath.name=}')
		
		endings = ('.stronglines', '.continuum', '.contbins')
		fpath_name = fpath.name
		
		for ending in endings:
			if fpath_name.endswith(ending):
				fpath_name = fpath_name[:len(ending)]
				break
		
		if fpath_name[-1] == '.':
			fpath_name = fpath_name[:-1]
		
	
		line_data_fpath = fpath.parent / f'{fpath_name}.stronglines'
		continuum_data_fpath = fpath.parent / f'{fpath_name}.continuum'
		continuum_bin_fpath = fpath.parent / f'{fpath_name}.contbins'
		
		line_data = None
		
		print('    Found the following files:')
		if line_data_fpath.exists():
			print(f'        line data : {line_data_fpath}')
		else:
			pkg_logger.error('Could not find line data file, exiting...')
			return
		if continuum_data_fpath.exists():
			print(f'        continuum data : {continuum_data_fpath}')
		else:
			pkg_logger.error('Could not find continuum data file, exiting...')
			return
		if continuum_bin_fpath.exists():
			print(f'        continuum bins : {continuum_bin_fpath}')
		else:
			pkg_logger.error('Could not find continuum bin file, exiting...')
			return
		
		# Get temperature from file name
		print('    Getting creation temperature from file name...')
		temp_cont = float(line_data_fpath.name.rsplit('T',1)[1].rsplit('.',1)[0])
		print(f'    Found creation temperature {temp_cont}')
		
		if temp is None:
			print('    No calculation temperature set, using creation temperature')
			temp = temp_cont
		else:
			print(f'    Calculation temperature is {temp}')
		
		with spectral_data_source_helper.utils.structured_array.StructuredArrayFile(line_data_fpath,'rb') as f:
			line_data = f.read()
		
		if line_data is None:
			pkg_logger.error(f'Something went wrong when reading {line_data_fpath}. Exiting...')
			return
		print('    Line data has the following columns:')
		print(f'        {" | ".join(line_data.dtype.names)}')
		print(f'    Printing line data slice {line_data_slice} of {line_data.size} rows.')
		for line_data_record in line_data[line_data_slice]:
			print(f'        {line_data_record}')
		
		continuum_bin_edges = None
		with open(continuum_bin_fpath, 'rb') as f:
			print('    Reading continuum bins.')
			continuum_bin_edges = np.fromfile(f, dtype=float)
		print(f'{continuum_bin_edges.shape=}')
		
		continuum_data = None
		with spectral_data_source_helper.utils.structured_array.StructuredArrayFile(continuum_data_fpath, 'rb') as f:
			print('    Reading continuum data.')
			continuum_data = f.read()
		
		print(f'{continuum_data.shape=}')
		print('    Continuum data columns:')
		print(f'        {" | ".join(continuum_data.dtype.names)}')
			
		print('    Continuum data:')
		cont_bin_print_dots_flag = True
		for i in range(continuum_data.size):
			
			if (2 <= i) and (i < (continuum_data.size-2)):
				if cont_bin_print_dots_flag:
					print(f'        bin edge    {continuum_bin_edges[i]}')
					print('        ...')
					cont_bin_print_dots_flag = False
			else:
				print(f'        bin edge    {continuum_bin_edges[i]}')
				print(f'        value           {continuum_data[i]}')
				cont_bin_print_dots_flag = True
			
			
		print(f'        bin edge    {continuum_bin_edges[-1]}')
		
		continuum_data_means = np.zeros_like(continuum_data)
		
		
		
		continuum_data_means['line_strength_sum'] = continuum_data['line_strength_sum']
		if eps is not None: # Account for zeros (or very small negative numbers)
			min_line_str_sum = np.min(continuum_data_means['line_strength_sum'])
			if min_line_str_sum < (-1*eps):
				raise RuntimeError(f'Minimum line strength sum is less than defined limit ({-1*eps}). Cannot have -ve values for line strength sums')
			elif min_line_str_sum <= 0: 
				pkg_logger.warn(f'Minimum line strength sum is less than zero, but larger than defined limit ({-1*eps}), setting to a small value...')
				continuum_data_means['line_strength_sum'][continuum_data_means['line_strength_sum'] <= 0] = eps
		else:
			if np.count_nonzero(continuum_data_means['line_strength_sum'] < 0) > 0:
				raise RuntimeError('Some line strength sums are less than zero. Cannot have -ve values for line strength sums')
		
		# Calculate line strength weighted means
		for field_name in (x for x in continuum_data_means.dtype.names if x != 'line_strength_sum'):
			continuum_data_means[field_name] = continuum_data[field_name] / continuum_data_means['line_strength_sum']
		
		if len(continuum_data_means) == 0:
			print('    No data to plot!')
		else:
		
			import matplotlib.pyplot as plt
			from .plotters.continuum_plotter import ContinuumPlotter
			
			print('    Plotting data...', flush=True)
			
			broad_foreign_gasses = tuple(
				gas_name for gas_name in ds_holder.broad_gas_names if gas_name != 'self'
			)
			print(f'    {broad_foreign_gasses=}', flush=True)
			broad_gas_amb_fracs = tuple(0.5 for _ in broad_foreign_gasses)
			print(f'    {broad_gas_amb_fracs=}', flush=True)
			
			chosen_gas_idx = 0
			chosen_gas = broad_foreign_gasses[chosen_gas_idx]
			chosen_gas_amb_frac = broad_gas_amb_fracs[chosen_gas_idx]
			print(f'    {chosen_gas_idx=} {chosen_gas=} {chosen_gas_amb_frac=}', flush=True)
			
			continuum_bin_mids = 0.5*(continuum_bin_edges[:-1] + continuum_bin_edges[1:])
			
			if extra_plots >= 1:
				for field_name in continuum_data_means.dtype.names:
					plt.figure()
					plt.title(f'{field_name}\n[num < 0: {np.count_nonzero(continuum_data_means[field_name] < 0)}] [num == 0: {np.count_nonzero(continuum_data_means[field_name] == 0)}] [num nan: {np.count_nonzero(np.isnan(continuum_data_means[field_name]))}]')
					plt.plot(continuum_bin_mids, continuum_data_means[field_name])
				plt.show()
			
			pseudo_continuum_data = spectral_data_source_helper.calc.pseudo_continuum.pseudo_continuum(
				1,
				temp,
				ds_holder.partition_function_at(temp),
				continuum_bin_mids,
				np.diff(continuum_bin_edges),
				continuum_data_means['line_strength_sum'],
				continuum_data_means['strength_weighted_sum_E"'],
				continuum_data_means['strength_weighted_gamma_self'],
				continuum_data_means['strength_weighted_n_self'],
				continuum_data_means[f'strength_weighted_gamma_{chosen_gas}'],
				continuum_data_means[f'strength_weighted_n_{chosen_gas}'],
				ds_holder.iso_mass_cgs,
				chosen_gas_amb_frac,
				ds_holder.partition_function_at(temp_cont),
				T_cont = temp_cont,
				P_cont = P_ref,
				n_neighbour_bins = 3,
			)
			
			pltr = ContinuumPlotter().plot(pseudo_continuum_data, continuum_bin_edges)
			pltr.ylog()
			
			
			cont_edge_diff = np.diff(continuum_bin_edges)
			if all(cont_edge_diff[:-1] < cont_edge_diff[1:]):
				pltr.xlog()
			
			pltr.ax.plot(
				line_data['wavenumber'], 
				spectral_data_source_helper.calc.spec.line_strengths(line_data, np.array([temp]), ds_holder.partition_function, T_ref, squeeze=True),
				'.',
				markersize=1,
				alpha=0.1,
				ls='none',
				zorder=-1,
				label = 'strong lines',
			)
			
			pltr.ax.set_title('Absorption coefficient of pseudo-continuum and strong lines')
			pltr.fig.legend()
			
			plt.show()
			print('    Data plotted', flush=True)
		

def exomol_convert_trans(
		dataset_holders : list[ExomolDatasetHolder],
		fmt : str,
		chunk_size : int = CHUNK_SIZE,
		n_files : None | int = None,
):

	for ds_holder in dataset_holders:
		ds_holder.convert_transition_files_to_fmt(
			fmt=fmt,
			chunk_size=chunk_size,
			trans_files_slice=slice(None,n_files),
		)

if __name__=='__main__':
	
	def DatasetSelector(dss : str):
		#print(f'{dss=}')
		result = []
		
		if (n_slash := dss.count('/')) < 2:
			dss += '/*'*(2-n_slash)
		dss_mol, dss_iso, dss_name = dss.split('/')[:3]
		
		if dss_mol == '*':
			mols = list(all_molecules)
		else:
			mols = dss_mol.split(',')
			valid = tuple(mol_iso_dataset_dict.keys())
			invalid = [x for x in mols if x not in valid]
			if len(invalid) > 0:
				raise ap.ArgumentTypeError(f'Invalid molecules {invalid}. Valid choices are {valid}')
		
		for mol in mols:
			if dss_iso == '*':
				isos = list(mol_iso_dataset_dict[mol].keys())
			else:
				isos = dss_iso.split(',')
				valid = tuple(mol_iso_dataset_dict[mol].keys())
				invalid = [x for x in isos if x not in valid]
				if len(invalid) > 0:
					raise ap.ArgumentTypeError(f'Invalid isotopes {invalid} for molecule {mol}. Valid choices are {valid}')
				#isos = [iso for iso in isos if iso in tuple(mol_iso_dataset_dict[mol].keys())]
			
			for iso in isos:
			
				if dss_name == '*':
					names = list(mol_iso_dataset_dict[mol][iso].dataset_names)
				else:
					names = dss_name.split(',')
					valid = tuple(mol_iso_dataset_dict[mol][iso].dataset_names)
					invalid = [x for x in names if x not in valid]
					if len(invalid) > 0:
						raise ap.ArgumentTypeError(f'Invalid dataset names {invalid} for isotope {iso} and molecule {mol}. Valid choices are {valid}')
					#names = [name for name in names if name in mol_iso_dataset_dict[mol][iso].dataset_names]
				
				for name in names:
					result.append((mol, iso, name))
		
		return result



	parser = ap.ArgumentParser()
	
	parser.add_argument('-d', '--dataset_selector', action='extend', type=DatasetSelector, metavar='<Dataset Selector>', help='String that selects dataset to operate upon. Format: "<mol>/<iso>/<dataset_name>", "*" can be used as a wild card', default=None)
	
	
	subparsers = parser.add_subparsers(required=True)
	
	download_parser = subparsers.add_parser('download', help='Download the passed molecule and isotopes')
	download_parser.set_defaults(func = exomol_download)
	download_parser.add_argument('--refresh', action='store_true', help='If present, will redownload all specified data.')
	
	list_parser = subparsers.add_parser('tree', help='Show molecules, isotopes, and datasets selected by the passed arguments in a tree format')
	list_parser.set_defaults(func = exomol_tree)
	
	list_parser = subparsers.add_parser('list', help='List set of molecules, isotopes, and datasets that are selected by the passed arguments')
	list_parser.set_defaults(func = exomol_list)
	
	states_parser = subparsers.add_parser('states', help='Show information about states of specified data')
	states_parser.set_defaults(func = exomol_states)
	states_parser.add_argument('-n', '--start', type=int, help='start of slice to print', default=0)
	states_parser.add_argument('-m', '--stop', type=int, help='stop of slice to print (0 is "past the end", so selects all until end) endpoint is inclusive', default=10)
	states_parser.add_argument('-l', '--step', type=int, help='step of slice to print', default=1)
	
	trans_parser = subparsers.add_parser('trans', help='Show information about transitions of specified data')
	trans_parser.set_defaults(func = exomol_trans)
	trans_parser.add_argument('-c', '--chunk_size', type=int, help='Chunk size to use during calculations', default=CHUNK_SIZE)
	trans_parser.add_argument('-n', '--n_to_print', type=int, help='number of lines of data to print', default=10)
	
	calc_line_data_parser = subparsers.add_parser('calc_line_data', help='calculate line data')
	calc_line_data_parser.set_defaults(func = exomol_calc_line_data)
	calc_line_data_parser.add_argument('-c', '--chunk_size', type=int, help='Chunk size to use during calculations', default=CHUNK_SIZE)
	
	read_line_data_parser = subparsers.add_parser('read_line_data', help='read saved line data files')
	read_line_data_parser.set_defaults(func = exomol_read_line_data)
	read_line_data_parser.add_argument('-n', '--start', type=int, help='start of slice to print', default=0)
	read_line_data_parser.add_argument('-m', '--stop', type=int, help='stop of slice to print (0 is "past the end", so selects all until end) endpoint is inclusive', default=10)
	read_line_data_parser.add_argument('-l', '--step', type=int, help='step of slice to print', default=1)
	
	calc_continuum_parser = subparsers.add_parser('calc_continuum', help='read saved line data files')
	calc_continuum_parser.set_defaults(func = exomol_calc_continuum)
	calc_continuum_parser.add_argument('-T', '--temperature', type=float, action='extend', nargs='+', help='Temperatures to calculate continuum at', default=None)
	calc_continuum_parser.add_argument('-x', '--continuum_line_intensity_cutoff', type=float, help='Below this value a line is considered "weak" and is added to the continuum', default=1E-24)
	calc_continuum_parser.add_argument('-a', '--continuum_wavenumber_min', type=float, help='Minimum wavenumber of continuum', default=0.00001)
	calc_continuum_parser.add_argument('-b', '--continuum_wavenumber_max', type=float, help='Maximum wavenumber of continuum', default=100_000)
	calc_continuum_parser.add_argument('-n', '--continuum_n_bins', type=int, help='Number of bins in the continuum', default=1_000)
	calc_continuum_parser.add_argument('-s', '--continuum_bin_spacing', type=str, choices=('lin', 'log'), help='Spacing of continuum bins', default='lin')
	calc_continuum_parser.add_argument('-c', '--chunk_size', type=int, help='Chunk size to use during calculations', default=CHUNK_SIZE)
	
	read_continuum_data_parser = subparsers.add_parser('read_continuum_data', help='read saved line data files')
	read_continuum_data_parser.set_defaults(func = exomol_read_continuum_data)
	read_continuum_data_parser.add_argument('fname', type=str, help='Name of the files to use (will add ".continuum", ".contbins", ".stronglines" if name does not end with one of them otherwise will replace extension to get the other required files)')
	read_continuum_data_parser.add_argument('-n', '--start', type=int, help='start of slice to print', default=0)
	read_continuum_data_parser.add_argument('-m', '--stop', type=int, help='stop of slice to print (0 is "past the end", so selects all until end) endpoint is inclusive', default=10)
	read_continuum_data_parser.add_argument('-l', '--step', type=int, help='step of slice to print', default=1)
	read_continuum_data_parser.add_argument('-t', '--temp', type=float, help='Temperature to calculate pseudo-continuum at', default=None)
	read_continuum_data_parser.add_argument('-e', '--eps', type=float, help='If present, line strength sums with a magnitude smaller than this are treated as a truncation error, and -ve values with a larger magnitude are treated as a problem. Otherwise any -ve line strength sums are treated as errors.', default=None)
	read_continuum_data_parser.add_argument('-p', '--extra_plots', action='count', help='Will show extra plots depending upon the number of times passed', default=0)
	
	
	convert_trans_parser = subparsers.add_parser('convert_trans', help='Convert transition data to new format')
	convert_trans_parser.set_defaults(func = exomol_convert_trans)
	convert_trans_parser.add_argument('-f', '--fmt', type=str, help='Format to convert transition files to', default='.bin')
	convert_trans_parser.add_argument('-c', '--chunk_size', type=int, help='Chunk size to use during calculations', default=CHUNK_SIZE)
	convert_trans_parser.add_argument('-n', '--n_files', type=int, help='Number of files to convert (starting from the first available, default is to convert all)', default=None)
	
	#download_selection_group = download_parser.add_mutually_exclusive_group(required=True)

	args = parser.parse_args(sys.argv[1:])
	arg_dict = vars(args)
	
	
	dataset_selectors = arg_dict.pop('dataset_selector')
	#print(f'{dataset_selectors=}')
	dataset_holders = []
	for dss_mol, dss_iso, dss_name in (dataset_selectors if dataset_selectors is not None else DatasetSelector('*')):
		#print(f'{dss_mol=} {dss_iso=} {dss_name=}')
		dataset_holders.extend([ExomolDatasetHolder(x) for x in exomol_select_datasets([dss_mol], [dss_iso], [dss_name])])
		
	# Deal with any arguments that should have default values but
	# are not playing nice.
	arg_not_present_sentinel = 'NOT_PRESENT'
	arg_defaults = {
		'temperature' : [T_ref],
	}
	
	
	for k,v in arg_defaults.items():
		if arg_dict.get(k, arg_not_present_sentinel) is None:
			arg_dict[k] = v
	
	func = arg_dict.pop('func')
	
	pkg_logger.info('## ARGUMENTS ##')
	for k,v in arg_dict.items():
		pkg_logger.info(f'    {k} : {v}')
	pkg_logger.info('##-----------##')
	
	
	func(dataset_holders, **arg_dict)



