
import sys
import argparse as ap
from typing import Any

import numpy as np

from exomol_helper.cfg.const import (
	REPO_LOCAL,
)

from exomol_helper.datatypes import (
	ExomolDatasetInfo,
)

from exomol_helper.exomol_dataset_holder import ExomolDatasetHolder

from exomol_helper.exomol import (
	exomol_all_dataset_name_dict,
)

import exomol_helper.utils
import exomol_helper.utils.dtype


import logging
from exomol_helper.cfg.log import pkg_logger


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
		
		states_dtype = ds_holder.states_dtype
		
		#states_names = ' '.join(x[0] for x in states_dtype)
		states_names = ' '.join(ds_holder.states_short_names)
		print(f'    names: {states_names}')
		
		states_types = ' '.join(str(x[1])[8:-2] if isinstance(x[1],type) else str(x[1]) for x in states_dtype)
		print(f'    types: {states_types}')
		
		states = ds_holder.states
		print(f'    Printing states in slice {slice_to_print}:')
		
		for state in states[slice_to_print]:
			print(f'        {state}')


def exomol_trans(
		dataset_holders : list[ExomolDatasetHolder],
		n_to_print : int = 10
):
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
		
		print(f'    First {n_to_print} transitions ({ds_holder.n_transitions} in total):')
		do_stop = False
		chunk_size = 10
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
		chunk_size = 1_000_000
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
		chunk_size = 1_000_000
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
			f.write(exomol_helper.utils.dtype.to_string(ds_holder.line_data_dtype).encode('ascii'))
			
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
				use_dtype = exomol_helper.utils.dtype.from_string(hdr_part.decode('ascii'))
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
	trans_parser.add_argument('-n', '--n_to_print', type=int, help='number of lines of data to print', default=10)
	
	calc_line_data_parser = subparsers.add_parser('calc_line_data', help='calculate line data')
	calc_line_data_parser.set_defaults(func = exomol_calc_line_data)
	calc_line_data_parser.add_argument('-c', '--chunk_size', type=int, help='Chunk size to use during calculations', default=1_000_000)
	
	read_line_data_parser = subparsers.add_parser('read_line_data', help='read saved line data files')
	read_line_data_parser.set_defaults(func = exomol_read_line_data)
	read_line_data_parser.add_argument('-n', '--start', type=int, help='start of slice to print', default=0)
	read_line_data_parser.add_argument('-m', '--stop', type=int, help='stop of slice to print (0 is "past the end", so selects all until end) endpoint is inclusive', default=10)
	read_line_data_parser.add_argument('-l', '--step', type=int, help='step of slice to print', default=1)
	
	#download_selection_group = download_parser.add_mutually_exclusive_group(required=True)

	args = parser.parse_args(sys.argv[1:])
	arg_dict = vars(args)
	
	
	dataset_selectors = arg_dict.pop('dataset_selector')
	#print(f'{dataset_selectors=}')
	dataset_holders = []
	for dss_mol, dss_iso, dss_name in (dataset_selectors if dataset_selectors is not None else DatasetSelector('*')):
		#print(f'{dss_mol=} {dss_iso=} {dss_name=}')
		dataset_holders.extend([ExomolDatasetHolder(x) for x in exomol_select_datasets([dss_mol], [dss_iso], [dss_name])])
		
	
	
	
	
	
	arg_dict.pop('func')(dataset_holders, **arg_dict)



