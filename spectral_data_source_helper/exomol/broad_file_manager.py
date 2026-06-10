"""
Broadening files seem to be scattered all over EXOMOL without any nice way of finding them all
"""

import spectral_data_source_helper.utils.fetch as fetch
from spectral_data_source_helper.cfg.log import pkg_logger as _lgr

from spectral_data_source_helper.cfg.const import (
	PKG_CACHE,
)

from .cfg.const import (
	EXOMOL_URL_PREFIX,
)

from .datatypes import IsotopeInfo



# Each molecule seems to have a "main isotope", however it is not actually specified so
# just assume it is the first one encountered at this point.
main_isotope : dict[str,IsotopeInfo] = dict()

# Get all of the known broadener types and the known labels for them
broadener_type_map : dict[str,tuple[str,...]] = {
	'self' : ('self', 'self_a0'),
	'air' : ('air', 'air_a0'),
	'H20' : ('H20',),
	'H2' : ('H2',),
	'He' : ('He',),
	'CO2' : ('CO2',),
}

# broadener files for each molecule, isotope, broadener combination
broad_files : dict[str, dict[str, dict[str, str]]] = dict()

def search_broad_files_for(mol_formula : str, iso_slug : str):
	#global broad_files
	
	# check to see if we already have files
	if (result := broad_files.get(mol_formula, dict()).get(iso_slug, None) is not None):
		_lgr.debug(f'{iso_slug=} in `broad_files`')
		return result
	_lgr.debug(f'{iso_slug=} not in `broad_files`')
	
	# if not present, then see if main isotope is present
	main_iso_slug = main_isotope[mol_formula].slug
	if (result := broad_files.get(mol_formula, dict()).get(main_iso_slug, None) is None):
		_lgr.debug(f'{main_iso_slug=} not in `broad_files`')
		# if main isotope missing, get all files for main isotope
		
		for k, v in broadener_type_map.items():
			broadener_url_candidates = tuple(EXOMOL_URL_PREFIX + f'/{mol_formula}/{main_iso_slug}/{main_iso_slug}__{x}.broad' for x in v)
			broadener_url = None
			for url_candidate in broadener_url_candidates:
				broadener_fpath = fetch.file_from_cache(
					f'https://www.{url_candidate}',
					cache=PKG_CACHE,
					return_fpath=True,
					not_found_in_cache_action='return_none',
					error_code_action = {404 : 'ignore', 'timeout' : 'warning'},
				)
				
				if broadener_fpath is not None:
					broadener_url = url_candidate
					break
				
			if broadener_url is not None:
				broad_files.setdefault(mol_formula,dict()).setdefault(main_iso_slug, dict())[k] = broadener_url
	
	# if we are looking at the main isotope we are done
	if iso_slug == main_iso_slug:
		return broad_files[mol_formula][iso_slug]
	
	# should have main isotope by this point, so copy main isotope to this isotope
	
	# Copy to the current isotope
	broad_files.setdefault(mol_formula,dict()).setdefault(iso_slug, dict()).update(broad_files[mol_formula][main_iso_slug])
	
	# now try to find isotope specific values and overwrite the copied main isotope values
	for k, v in broadener_type_map.items():
		broadener_url_candidates = tuple(EXOMOL_URL_PREFIX + f'/{mol_formula}/{iso_slug}/{iso_slug}__{x}.broad' for x in v)
		broadener_url = None
		for url_candidate in broadener_url_candidates:
			try:
				fetch.file_from_cache(f'https://www.{url_candidate}',cache=PKG_CACHE,return_fpath=True)
			except:
				broadener_url = None
			else:
				broadener_url = url_candidate
				
			if broadener_url is not None:
				break
		
		if broadener_url is not None:
			broad_files[mol_formula][iso_slug][k] = broadener_url
	
	# return the isotope-specific data
	return broad_files[mol_formula][iso_slug]
	


