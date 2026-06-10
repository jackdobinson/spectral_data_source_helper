"""
Holds data types that read EXOMOL "exomol.all", "*.def.json", and other files associated with working out 
what data is actually held in the exomol databases.
"""

import dataclasses as dc
import functools
from typing import Any
import json
import urllib
import bz2

import numpy as np

import qn_set_manager
#import broad_file_manager
import spectral_data_source_helper.utils.fetch as fetch
import spectral_data_source_helper.utils.cfmt as cfmt
from spectral_data_source_helper.cfg.log import pkg_logger as _lgr
from spectral_data_source_helper.cfg.cont import (
	PKG_CACHE,
)
from .cfg.const import (
	EXOMOL_URL_PREFIX,
	EXOMOL_DATABASE_URL,
	EXOMOL_STATE_FILE_ENDINGS,
	EXOMOL_TRANSITION_FILE_ENDINGS,
	EXOMOL_API_URL_FMT,
	EXOMOL_API_INTERNAL_URL_START,
)



class ExomolIsotopeDefNotFoundError(Exception):
	pass



def mol_formula_to_api_mol(mol_formula):
	if mol_formula[-1] == '+':
		mol_formula = mol_formula.replace('+', '_p')
	if mol_formula[-1] == '-':
		mol_formula = mol_formula.replace('-', '_n')
	return mol_formula



def exomol_json_iso_info_linelist_filter(
		json_iso_info_linelist : dict[str,Any], 
		dataset_name : str
	) -> bool:
	if dataset_name == 'data type':
		return False
	
	for file_info in json_iso_info_linelist[dataset_name]['files']:
		if not file_info['url'].startswith(EXOMOL_API_INTERNAL_URL_START):
			return False
	return True


def iso_formula_to_iso_slug(iso_formula):
	return (iso_formula[1:] if iso_formula[0] == '(' else iso_formula).replace('(','-').replace(')','')


@dc.dataclass
class ExomolTransitionsInfo:
	number_of_transitions : int
	max_wavenumber : float
	number_of_transition_files : None | int = None

	def get_transition_url_wave_suffixes(self):
		if self.number_of_transition_files is not None:
			delta_wav = self.max_wavenumber/self.number_of_transition_files
			return tuple(f'{int(i*delta_wav):05d}-{int((i+1)*delta_wav):05d}' for i in range(self.number_of_transition_files))
		else:
			return None

@dc.dataclass
class ExomolStateField:
	name : str
	desc : str
	ffmt : str # fortran format
	cfmt : str # c format

@dc.dataclass
class ExomolStatesInfo:
	number_of_states : int
	num_quanta : int
	states_file_fields : tuple[ExomolStateField,...]
	max_energy : None | float = None
	uncertainty_description : None | str = None
	uncertainty_distribution : None | str = None
	uncertainties_available : bool = False
	lifetime_available : bool = False
	lande_g_available : bool = False
	hyperfine_resolved_dataset : bool = False
	quantum_case_label : None | str = None
	num_quantum_types : int = 0
	
	def __post_init__(self):
		self.states_file_fields = tuple(ExomolStateField(**x) for x in self.states_file_fields)
	
	def get_states_field_dtype(self) -> np.dtype:
		dtype = []
		for esf in self.states_file_fields:
			dtype.append(
				(
					esf.name,
					cfmt.str_to_type(esf.cfmt)
				)
			)
		_lgr.debug(f'{dtype=}')
		#print(f'{dtype=}')
		return np.dtype(dtype)
		
	def get_states_field_widths(self) -> list[int,...]:
		widths = []
		for esf in self.states_file_fields:
			widths.append((
				cfmt.str_to_width(esf.cfmt)
			))
		_lgr.debug(f'{widths=}')
		return widths
	
	def get_states_reader(self):
		return functools.partial(np.genfromtxt, dtype=self.get_states_field_dtype(), delimiter=self.get_states_field_widths())
	

@dc.dataclass
class ExomolIsotopologue:
	inchikey : str
	mass_in_Da : float
	point_group : str
	iso_formula : str
	iso_slug : str
	inchi : None | str = None
	cas_registry_number : None | str = None

@dc.dataclass
class ExomolAtoms:
	number_of_atoms : int
	element : dict[str,int] # Atom : proton number

@dc.dataclass
class ExomolDataset:
	name : str
	version : int
	doi : str
	max_temperature : float
	num_pressure_broadeners : int
	states : ExomolStatesInfo
	transitions : ExomolTransitionsInfo
	continuum : None | Any = None
	predis : None | Any = None
	n_L_default : None | float = None
	nxsec_files : int = 0
	nkcoeff_files : int = 0
	dipole_available : bool = False
	cooling_function_available : bool = False
	specific_heat_available : bool = False
	
	def __post_init__(self):
		self.states = ExomolStatesInfo(**self.states)
		self.transitions = ExomolTransitionsInfo(**self.transitions)
	

@dc.dataclass
class ExomolQuantumNumberSet:
	code : str
	num_lines : int
	num_quantum_numbers : int
	quantum_numbers : tuple[str,...]
	
	def __post_init__(self):
		self.quantum_numbers = tuple(self.quantum_numbers)
		
		qn_set_manager.add(self.code, self.quantum_numbers)

@dc.dataclass
class ExomolBroadener:
	broad_gas_name : str
	filename : str
	max_J : int
	lorentzian_half_width : float = dc.field(default=dc.MISSING, metadata={'json_name' : 'Lorentzian_half_width'})
	temperature_exponent : float
	num_quantum_number_sets : int
	quantum_number_sets : tuple[ExomolQuantumNumberSet,...]
	
	def __init__(self, **kwargs):
		for field in dc.fields(self):
			#print(f'{field.name=}')
			if(field.metadata is not None) and ((json_name := field.metadata.get('json_name', None)) is not None):
				setattr(self, field.name, kwargs.pop(json_name))
			elif field.name in kwargs:
				setattr(self, field.name, kwargs.pop(field.name))
		
		self.quantum_number_sets = tuple(ExomolQuantumNumberSet(**x) for x in self.quantum_number_sets)
	

@dc.dataclass
class ExomolBroadInfo:
	default_lorentzian_half_width : float = dc.field(default=dc.MISSING, metadata={'json_name' : 'default_Lorentzian_half-width'})
	default_temperature_exponent : float
	broadeners : tuple[ExomolBroadener]
	
	def __init__(self, **kwargs):
		for field in dc.fields(self):
			#print(f'{field.name=}')
			if(field.metadata is not None) and ((json_name := field.metadata.get('json_name', None)) is not None):
				setattr(self, field.name, kwargs.pop(json_name))
			elif field.name in kwargs:
				setattr(self, field.name, kwargs.pop(field.name))
		#print(f'{kwargs=}')
		self.broadeners = tuple(ExomolBroadener(broad_gas_name=k,**v) for k,v in kwargs.items())
			

@dc.dataclass
class ExomolPartitionFunctionInfo:
	max_partition_function_temperature : float
	partition_function_step_size : float

@dc.dataclass
class ExomolIsotopeDef:
	mol_formula : str
	isotopologue : ExomolIsotopologue
	atoms : ExomolAtoms
	irreducible_representations : dict[str,Any]
	dataset : ExomolDataset
	partition_function : ExomolPartitionFunctionInfo
	broad : ExomolBroadInfo
	
	def __post_init__(self):
		self.isotopologue = ExomolIsotopologue(**self.isotopologue)
		self.atoms = ExomolAtoms(**self.atoms)
		self.dataset = ExomolDataset(**self.dataset)
		self.broad = ExomolBroadInfo(**self.broad)
		self.partition_function = ExomolPartitionFunctionInfo(**self.partition_function)
	
	def datafile_prefix(self):
		return f'{self.isotopologue.iso_slug}__{self.dataset.name}'
	
	def get_transition_urls(self):
		trans_url_suffixes = self.dataset.transitions.get_transition_url_wave_suffixes()
		if trans_url_suffixes is not None:
			return tuple(EXOMOL_URL_PREFIX + f'/{self.mol_formula}/{self.isotopologue.iso_slug}/{self.dataset.name}/{self.datafile_prefix()}__{x}.trans.bz2' for x in trans_url_suffixes)
		else:
			return (
				EXOMOL_URL_PREFIX + f'/{self.mol_formula}/{self.isotopologue.iso_slug}/{self.dataset.name}/{self.datafile_prefix()}.trans.bz2',
			)

	def get_states_urls(self):
		return (
			EXOMOL_URL_PREFIX + f'/{self.mol_formula}/{self.isotopologue.iso_slug}/{self.dataset.name}/{self.datafile_prefix()}.states.bz2',
		)



@dc.dataclass
class ExomolLineList:
	mol_formula : str
	inchikey : str
	iso_slug : str
	iso_formula : str
	dataset_name : str
	version : int
	hr_available : bool = False
	file_urls : list[str] = dc.field(default_factory=list)
	
	isotope_def : None | ExomolIsotopeDef = None
	
	state_file_urls : None | tuple[str,...] = None
	transition_file_urls : None | tuple[str,...] = None
	
	def __post_init__(self):
		self.classify_file_urls()
		
		if self.isotope_def is None:
			def_file = f'{self.mol_formula}/{self.iso_slug}/{self.dataset_name}/{self.iso_slug}__{self.dataset_name}.def'
			json_def_file = f'{def_file}.json'
			def_url = EXOMOL_DATABASE_URL + f'/{def_file}'
			json_def_url = EXOMOL_DATABASE_URL + f'/{json_def_file}'
			#print(f'Getting file {json_def_url}')
			
			try:
				self.isotope_def = ExomolIsotopeDef(mol_formula=self.mol_formula, **json.loads(fetch.file_from_cache(json_def_url, cache=PKG_CACHE)))
			except urllib.error.HTTPError as e:
				print(f'Could not get "{json_def_url}". Error: {e}')
				print('Attempting to get text version.')
				try:
					fetch.file_from_cache(def_url, cache=PKG_CACHE)
				except urllib.error.HTTPError as e1:
					print(f'Could not get text definition file "{def_url}". Error: {e1}')
				else:
					print('TEXT VERSION EXISTS. HANDLE THIS CASE')
	
	def get_data_dir(self):
		return f'{self.mol_formula}/{self.iso_slug}/{self.dataset_name}'
	
	def classify_file_urls(self):
		self.state_file_urls = tuple(x for x in self.file_urls if any(x.endswith(y) for y in EXOMOL_STATE_FILE_ENDINGS))
		self.transition_file_urls = tuple(x for x in self.file_urls if any(x.endswith(y) for y in EXOMOL_TRANSITION_FILE_ENDINGS))
	
	def download_data(self, refresh : bool = False):
		_lgr.info(f'Downloading data for "{self.get_data_dir()}"')
		n_urls = len(self.file_urls)
		for i, url in enumerate(self.file_urls):
			_lgr.info(f'Fetching file {i}/{n_urls} "{url}"')
			fpath = fetch.file_from_cache(
				f'https://www.{url}',
				cache = PKG_CACHE,
				return_fpath = True,
				refresh=refresh,
				check_web_first=True
			)
			_lgr.info(f'file fetched into "{fpath}"')
	
	def iter_states(self):
		for state_file_url in self.state_file_urls:
			fpath = fetch.file_from_cache(
				f'https://www.{state_file_url}',
				cache=PKG_CACHE,
				return_fpath = True,
				check_web_first=True
			)
			
			if fpath.suffix == '.bz2':
				with bz2.open(fpath, 'rb') as f:
					while f:
						yield f.readline().decode('ascii')
			else:
				with open(fpath, 'r') as f:
					while f:
						yield f.readline()
		
		return
	
	def load_states(self) -> np.ndarray:
		dtype = self.isotope_def.dataset.states.get_states_field_dtype()
		states = np.empty(
			(self.isotope_def.dataset.states.number_of_states,),
			dtype = dtype
		)
		
		for i, s in enumerate(self.iter_states()):
			ss = s.strip()
			if len(ss) == 0:
				break
				
			if i%100000==0:
				print(f'{i=} ##{s}')
			states[i] = tuple(dtype[j][1](x) if not isinstance(dtype[j][1],str) else x for j,x in enumerate(ss.split()))
			if i%100000==0:
				print(f'{states[i]=}')
		return states
	
	def load_states_by_chunks(self) -> np.ndarray:
		
		chunk_size = 1_000_000
		
		state_list = []
		dtype = self.isotope_def.dataset.states.get_states_field_dtype()
		state_list.append(np.empty(
			(chunk_size,),
			dtype = dtype
		))
		widths = tuple(w if w>3 else 3 for w in self.isotope_def.dataset.states.get_states_field_widths())
		cwidths = tuple(-1*sum(widths[-(i+1):])-(i+1) for i in range(len(widths)))[::-1]
		
		print(f'{widths=}')
		print(f'{cwidths=}')
		
		n = len(state_list)
		nn = 0
		mm = chunk_size
		for i, s in enumerate(self.iter_states()):
			ss = s.strip()
			if len(ss) == 0:
				state_list[-1] = state_list[-1][:i-nn]
				break
		
			if i >= mm:
				state_list.append(np.empty(
					(chunk_size,),
					dtype = dtype
				))
				n+=1
				nn += chunk_size
				mm += chunk_size

			if i%100000==0:
				print(f'{i=} ##{s}')
			state_list[-1][i-nn] = tuple(dtype[j][1](x) if not isinstance(dtype[j][1],str) else x for j,x in enumerate(ss.split()))
			if i%100000==0:
				print(f'{state_list[-1][i-nn]=}')
		return np.concatenate(state_list)
	
	
	def iter_transitions(self):
		for trans_file_url in self.transition_file_urls:
			fpath = fetch.file_from_cache(
				f'https://www.{trans_file_url}',
				cache=PKG_CACHE,
				return_fpath = True,
				check_web_first=True
			)
			
			if fpath.suffix == '.bz2':
				with bz2.open(fpath, 'rb') as f:
					while f:
						yield f.readline().decode('ascii')
			else:
				with open(fpath, 'r') as f:
					while f:
						yield f.readline()
		
		return
	

@dc.dataclass
class ExomolMolecule:
	mol_formula : str
	num_molecule_names : int
	molecule_names : tuple[str]
	num_isotopologues : int
	linelist : list[ExomolLineList,...]
	
	def __post_init__(self):
		self.linelist = [ExomolLineList(mol_formula=self.mol_formula, **item) for item in self.linelist]


@dc.dataclass
class ExomolRoot:
	ID : str
	version : int
	num_molecules : int
	num_isotopologues : int
	num_datasets : int
	molecules : dict[str,ExomolMolecule]

	def __post_init__(self):
		self.molecules = dict(
			(mol_formula, ExomolMolecule(mol_formula, **mol_info)) for mol_formula, mol_info in self.molecules.items()
		)
		
		for mol_formula, exomol_molecule in self.molecules.items():
			print(f'{mol_formula=}')
			exomol_api_iso_json = json.loads(fetch.file_from_cache(EXOMOL_API_URL_FMT.format(mol_formula_to_api_mol(mol_formula)), cache=PKG_CACHE))
			
			for iso_formula, json_iso_info in exomol_api_iso_json.items():
				json_iso_linelists_dataset_names = tuple(x for x in json_iso_info['linelist'].keys() if exomol_json_iso_info_linelist_filter(json_iso_info['linelist'], x))
				
				for dataset_name in json_iso_linelists_dataset_names:
					is_present_already = False
					iso_slug = None
					for a_linelist in self.molecules[json_iso_info['molecule']].linelist:
						if a_linelist.iso_formula == iso_formula:
							iso_slug = a_linelist.iso_slug
							if a_linelist.dataset_name == dataset_name:
								is_present_already = True
								
								a_linelist.file_urls = [x['url'] for x in json_iso_info['linelist'][dataset_name]['files']]
								a_linelist.classify_file_urls()
								
								
								break
					
					if iso_slug is None:
						iso_slug = iso_formula_to_iso_slug(iso_formula)
					
					
					def_file = f'{mol_formula}/{iso_slug}/{dataset_name}/{iso_slug}__{dataset_name}.def'
					json_def_file = f'{def_file}.json'
					def_url = EXOMOL_DATABASE_URL + f'/{def_file}'
					json_def_url = EXOMOL_DATABASE_URL + f'/{json_def_file}'
					
					#print(f'{json_def_url=}')
					
					if not is_present_already:
						print(f'Adding ExomolLineList for "{json_def_file}" as it is not already present')
						# Add ExomolLineList instances from DEF file
						try:
							isotope_def = ExomolIsotopeDef(mol_formula=mol_formula, **json.loads(fetch.file_from_cache(json_def_url, cache=PKG_CACHE)))
						except urllib.error.HTTPError as e:
							print(f'Could not get "{json_def_url}". Error: {e}')
							print('Attempting to get text version.')
							try:
								fetch.file_from_cache(def_url, cache=PKG_CACHE)
							except urllib.error.HTTPError as e1:
								print(f'Could not get text definition file "{def_url}". Error: {e1}')
							else:
								print('TEXT VERSION EXISTS. HANDLE THIS CASE')
						else:
							self.molecules[json_iso_info['molecule']].linelist.append(
								ExomolLineList(
									mol_formula=mol_formula,
									inchikey=isotope_def.isotopologue.inchikey,
									iso_slug = isotope_def.isotopologue.iso_slug,
									iso_formula = isotope_def.isotopologue.iso_formula,
									dataset_name = isotope_def.dataset.name,
									version = isotope_def.dataset.version,
									hr_available=False,
									file_urls = list(isotope_def.get_transition_urls()) + list(isotope_def.get_states_urls()),
									isotope_def = isotope_def
								)
							)
					
				self.molecules[json_iso_info['molecule']].num_isotopologues = len(set(ll.iso_formula for ll in self.molecules[json_iso_info['molecule']].linelist))

