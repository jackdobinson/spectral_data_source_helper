
#import os
#from pathlib import Path
import json
import datetime as dt

from spectral_data_source_helper.utils import fetch
from spectral_data_source_helper.cfg.log import pkg_logger as _lgr
from spectral_data_source_helper.cfg.const import (
	PKG_CACHE,
)

from .cfg.const import (
	EXOMOL_JSON_DATABASE_ROOT_URL,
	EXOMOL_API_URL_FMT,
)

#from . import qn_set_manager
from . import broad_file_manager

from .datatypes import (
	IsotopeInfo,
	ExomolDatasetInfo,
	IsoDatasetsList,
)

from .exomol_index_types import (
	mol_formula_to_api_mol,
	iso_formula_to_iso_slug,
)

from .exomol_dataset_holder import ExomolDatasetHolder


def exomol_all_mol_formulas() -> tuple[str,...]:
	root_json = json.loads(fetch.file_from_cache(EXOMOL_JSON_DATABASE_ROOT_URL, cache=PKG_CACHE))
	return tuple(root_json['molecules'].keys())


def exomol_all_isotopes() -> dict[str,set[IsotopeInfo]]:
	iso_info = dict()
	root_json = json.loads(fetch.file_from_cache(EXOMOL_JSON_DATABASE_ROOT_URL, cache=PKG_CACHE))
	
	for mol_formula, root_info in root_json['molecules'].items():
		iso_info_set = set()
		for linelist in root_info.get('linelists',[]):
			iso_info_set.add(IsotopeInfo(linelist['iso_formula'],linelist['iso_slug']))
		
		
		exomol_api_iso_json = json.loads(fetch.file_from_cache(EXOMOL_API_URL_FMT.format(mol_formula_to_api_mol(mol_formula)), cache=PKG_CACHE))
		new_iso_formulas = tuple(x for x in exomol_api_iso_json.keys() if x not in iso_info_set)
		
		for new_iso_formula in new_iso_formulas:
			iso_info_set.add(IsotopeInfo(new_iso_formula, iso_formula_to_iso_slug(new_iso_formula)))
		
		iso_info[mol_formula] = iso_info_set
	return iso_info





def exomol_all_dataset_name_dict() -> dict[str,dict[str, tuple[str,set[str]]]]:
	dt_start = dt.datetime.now()
	_lgr.info(f'Loading EXOMOL dataset Index at {dt_start} ...')
	result_dict = dict()
	root_json = json.loads(fetch.file_from_cache(EXOMOL_JSON_DATABASE_ROOT_URL, cache=PKG_CACHE))
	
	for mol_formula, root_info in root_json['molecules'].items():
		result_dict.setdefault(mol_formula, dict())
		
		for linelist in root_info.get('linelists',list()):
			
			if mol_formula not in broad_file_manager.main_isotope:
				broad_file_manager.main_isotope[mol_formula] = IsotopeInfo(linelist['iso_formula'],linelist['iso_slug'])
			
			result_dict[mol_formula].setdefault(linelist['iso_formula'], IsoDatasetsList(linelist['iso_slug'], set())).dataset_names.add(linelist['dataset_name'])
		
		exomol_api_iso_json = json.loads(fetch.file_from_cache(EXOMOL_API_URL_FMT.format(mol_formula_to_api_mol(mol_formula)), cache=PKG_CACHE))
		for iso_formula, api_info in exomol_api_iso_json.items():
			
			for linelist in api_info['linelist'].keys():
				if linelist == 'data type':
					continue
				
				if mol_formula not in broad_file_manager.main_isotope:
					broad_file_manager.main_isotope[mol_formula] = IsotopeInfo(iso_formula,iso_formula_to_iso_slug(iso_formula))
				
				result_dict[mol_formula].setdefault(iso_formula, IsoDatasetsList(iso_formula_to_iso_slug(iso_formula), set())).dataset_names.add(linelist)
	
	dt_end = dt.datetime.now()
	_lgr.info(f'Finished loading EXOMOL dataset index at {dt_end}. Took {(dt_end-dt_start).total_seconds()} s.')
	
	_lgr.debug(f'{result_dict=}')
	
	return result_dict


def exomol_all_datasets() -> tuple[ExomolDatasetHolder,...]:
	root_json = json.loads(fetch.file_from_cache(EXOMOL_JSON_DATABASE_ROOT_URL, cache=PKG_CACHE))
	
	datasets_set = set()
	
	for mol_formula, root_info in root_json['molecules'].items():
		for linelist in root_info.get('linelist',[]):
			datasets_set.add(ExomolDatasetInfo(mol_formula, linelist['iso_formula'], linelist['iso_slug'], linelist['dataset_name']))
	
		exomol_api_iso_json = json.loads(fetch.file_from_cache(EXOMOL_API_URL_FMT.format(mol_formula_to_api_mol(mol_formula)), cache=PKG_CACHE))
		for iso_formula, api_info in exomol_api_iso_json.items():
			for linelist in api_info['linelist'].keys():
				if linelist == 'data type':
					continue
				datasets_set.add(ExomolDatasetInfo(ExomolDatasetInfo(mol_formula, iso_formula, iso_formula_to_iso_slug(iso_formula), linelist)))
				
	return tuple(ExomolDatasetHolder(d) for d in datasets_set)


	
	
	




