
#from pathlib import Path
from typing import NamedTuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from spectral_data_source_helper.cfg.const import (
	PKG_CACHE,
)
from spectral_data_source_helper.utils import fetch

from .readers import html_to_molecular_formula, html_to_isotopologue_formula, parse_html_float


from spectral_data_source_helper.datatypes.molecule import Molecule
from spectral_data_source_helper.datatypes.isotopologue import Isotopologue

HITRAN_ISO_LIST_URL = "https://hitran.org/docs/iso-meta/"
HITRAN_ISO_TABLE = PKG_CACHE / 'hitran.org' / 'isotopologues.tbl'


# https://hitran.org/lbl/api?iso_ids_list=13&numin=6300&numax=6400&head=False&fixwidth=0&sep=[comma]&request_params=par_line,n_self,delta_self
HITRAN_API_URL_FMT = "https://hitran.org/lbl/api?iso_ids_list={global_id}&head=False&fixwidth=0&sep=[comma]&request_params={par_list}"

hitran_pars = (
	"molec_id",
	"local_iso_id",
	"nu",
	"sw",
	"a",
	"elower",
	"gamma_self",
	"n_self",
	"delta_self"
)

hitran_broadeners = (
	'self',
	'air',
	'H2',
	'CO2',
	'H2O',
	'He',
)

hitran_broadener_pars = (
	"gamma_",
	"n_",
	"delta_"
)

def get_hitran_broadener_par_list(broadener):
	return tuple(['nu'] + [x+broadener for x in hitran_broadener_pars])


mol_ids = dict()
mols = dict()
isos = dict()


field_match = {
	'global_id' : 'global id',
	'iso_id' : 'local id',
	'isotopologue' : 'formula',
	'AFGL' : 'afgl code',
	'terrestrial_abundance' : 'abundance',
	'mol_mass' : 'molar mass',
	'q_ref': 'q(296',
	'q_file' : 'q (full',
	'gi' : 'gi'
}

field_match_rev = dict((v,k) for k,v in field_match.items())


field_readers = {
	'global_id' : lambda x: int(x.text),
	'iso_id' : lambda x: int(x.text) if int(x.text) != 0 else 10, # There is an error where one of the iso_id values is 0 instead of 10
	'isotopologue' : lambda x: Isotopologue.from_str(html_to_isotopologue_formula(x.contents)),
	'AFGL' : lambda x: int(x.text),
	'terrestrial_abundance' : lambda x: parse_html_float(x.contents),
	'mol_mass' : lambda x: parse_html_float(x.contents),
	'q_ref': lambda x: parse_html_float(x.contents),
	'q_file' : lambda x: urljoin(HITRAN_ISO_LIST_URL,x.a["href"]),
	'gi' : lambda x: int(x.text)
}

class IsoInfo(NamedTuple):
	global_id : int
	iso_id : int
	isotopologue : Isotopologue
	AFGL : int
	terrestrial_abundance : float
	mol_mass : float
	q_ref : float
	q_file : str
	gi : int

	def __repr__(self):
		return ' '.join((
			f'{self.global_id: 8d}', 
			f'{self.iso_id: 8d}', 
			f'{self.mol_mass: 12.6E}', 
			f'{self.terrestrial_abundance: 12.6E}', 
			f'{self.q_ref: 12.6E}', 
			f'"{self.isotopologue.Molecule!r}"', 
			f'"{self.isotopologue!r}"', 
		))

def read_mol(h4):
	#print('MOL', h4)
	#print(f'{h4.contents=}')
	id_and_mol_formula_start, mol_formula_parts = h4.contents[0], h4.contents[1:]
	mol_id, mol_formula_start = id_and_mol_formula_start.split(':')
	mol_formula_start = mol_formula_start.lstrip()
	
	mol_formula = [mol_formula_start, *mol_formula_parts]
	
	return int(mol_id), Molecule.from_str(html_to_molecular_formula(mol_formula))
	

def read_iso_table(table):
	#print('## ISO ##')
	
	field_idx_to_name = dict()
	i=0
	for tag in table.thead.tr.children:
		if tag.name != "th":
			continue
		#print(f'{tag.text=}')
		for k in field_match_rev.keys():
			if tag.text.lower()[:len(k)] == k:
				#print(f'{k=} {tag.text.lower()[:len(k)]=}')
				field_idx_to_name[i] = field_match_rev[k]
				i+= 1
				break
			
	
	#print(field_idx_to_name)
	
	for tr in table.tbody.children:
		if tr.name != "tr":
			continue
		fields = dict()
		i=0
		for tag in tr.children:
			if tag.name != 'td':
				continue
			#print(f'{i=} {field_idx_to_name[i]=} {tag=}')
			fields[field_idx_to_name[i]] = field_readers[field_idx_to_name[i]](tag)
			i+=1
		
		iso_info = IsoInfo(**fields)
		isos.setdefault(iso_info.isotopologue.Molecule,[]).append(iso_info)



def download_hitran_isotope_data(refresh : bool = False):
	
	try:
		iso_list_html = fetch.file_from_cache(HITRAN_ISO_LIST_URL, cache=PKG_CACHE)
	except Exception as e:
		if not refresh and HITRAN_ISO_TABLE.exists():
			return
		else:
			raise e
	
	soup = BeautifulSoup(iso_list_html, 'html.parser')
	mols_div = soup.find_all(class_='www_content')[0]
	
	for tag in mols_div.children:
		if tag.name == 'h4':
			mol_id, molecule = read_mol(tag)
			mols[molecule] = mol_id
			mol_ids[mol_id] = molecule
		elif tag.name == 'table':
			read_iso_table(tag)
	
	assert len(mols) == len(mol_ids), "Should have a 1:1 relation between molecules and molecule ids"
	
	HITRAN_ISO_TABLE.parent.mkdir(parents=True, exist_ok=True)
	
	with open(HITRAN_ISO_TABLE, 'w') as f:
		for mol, iso_data_list in isos.items():
			for iso_data in iso_data_list:
				f.write(f'{mols[mol]: 8d} {iso_data!r}\n')
		
		f.write('\n')
	