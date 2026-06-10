
from typing import Any
import argparse as ap


from ..datatypes import (
	ExomolDatasetInfo,
)

from ..exomol import (
	exomol_all_dataset_name_dict,
)


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



def select_datasets(
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
