

from .html import isotopologue
from .datatypes.hitran_isotope import HitranIsotope

from spectral_data_source_helper.cfg.log import pkg_logger as _lgr

from .hitran_dataset_holder import HitranDatasetHolder


def build_index():
	global HITRAN_INDEX
	
	_lgr.info('Building HITRAN index...')
	
	HITRAN_INDEX = dict()
	isotopologue.download_hitran_isotope_data()
	_lgr.info('    Isotopologue data loaded.')

	# Load HITRAN index
	for hitran_isotope in HitranIsotope.iter_from_file(isotopologue.HITRAN_ISO_TABLE):
		HITRAN_INDEX.setdefault(hitran_isotope.mol_formula.strip(), dict())[hitran_isotope.iso_formula.strip()] = HitranDatasetHolder(hitran_isotope)
	#print(f'{HITRAN_INDEX=}')
	_lgr.info('    HITRAN index built.')


def fetch_partition_function_data():
	_lgr.info('Fetching partition function data...')
	# Load partition function data for each isotopologue
	for mol_formula, isos in HITRAN_INDEX.items():
		for iso_formula, ds_holder in isos.items():
			_lgr.info(f'    Partition function data for {mol_formula} {iso_formula} [HITRAN_ID: {ds_holder.d.global_id}]')
			#ds_holder.pf_data
			ds_holder.pf_data_file
	_lgr.info('    Partition function data fetched.')

def fetch_line_data():
	_lgr.info('Fetching line data...')
	for mol_formula, isos in HITRAN_INDEX.items():
		for iso_formula, ds_holder in isos.items():
			_lgr.info(f'    Line data for {mol_formula} {iso_formula} [HITRAN_ID: {ds_holder.d.global_id}]')
			#ds_holder.linedata
			ds_holder.linedata_file
	_lgr.info('    Line data fetched.')

def fetch_broadening_data():
	_lgr.info('Fetching broadening data...')
	
	for mol_formula, isos in HITRAN_INDEX.items():
		for iso_formula, ds_holder in isos.items():
			_lgr.info(f'    Broadening data for {mol_formula} {iso_formula} [HITRAN_ID: {ds_holder.d.global_id}]')
			ds_holder.broadener_files
			#for chunk in ds_holder.iter_broadeners_chunk(chunk_size=1_000_000):
			#	print(chunk)
	_lgr.info('    Broadening data fetched.')


def fetch_all_data():
	_lgr.info('Fetching all data...')
	
	for mol_formula, isos in HITRAN_INDEX.items():
		for iso_formula, ds_holder in isos.items():
			_lgr.info(f'    Fetching all data for {mol_formula} {iso_formula} [HITRAN_ID: {ds_holder.d.global_id}]')
			ds_holder.cache_data()
	_lgr.info('    All data fetched.')

build_index()

#fetch_partition_function_data()

#fetch_line_data()

#fetch_broadening_data()

#fetch_all_data()






