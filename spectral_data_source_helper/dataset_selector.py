
from typing import NamedTuple

from spectral_data_source_helper.datatypes.molecule import Molecule
from spectral_data_source_helper.datatypes.isotopologue import Isotopologue


class SingleDatasetSelector(NamedTuple):
	mol_selector : None | str
	iso_selector : None | str
	dataset_selector : None | str
	
	def __call__(self, mol : str, iso : str, dataset_name : str) -> bool:
		return (
			self._match_selector(self.mol_selector, str(Molecule.from_str(mol))) 
			and self._match_selector(self.iso_selector, str(Isotopologue.from_str(iso)))
			and self._match_selector(self.dataset_selector, dataset_name)
		)
	
	@staticmethod
	def _match_selector(selector : str, value : str) -> bool:
		if selector is None:
			return True
		else:
			return str(selector) == value

class DatasetSelector(NamedTuple):
	dataset_selectors : tuple[SingleDatasetSelector,...]
	
	def __call__(self, mol : str, iso : str, dataset_name : str) -> bool:
		return any(ds_selector(mol, iso, dataset_name) for ds_selector in self.dataset_selectors)

def dataset_selector_factory(
		dss : str,
		multi = True,
) -> DatasetSelector:
	"""
	Specifies a dataset or collection of datasets to operate upon. The string format is 
	"<mol>/<iso>[|<iso>|...]/<dataset_name>[|<dataset_name>|...] [<mol>/<iso>[|<iso>|...]/<dataset_name>[|<dataset_name>|...]]". 
	
	The wild card "*" can be used to select all of a given category. For example, "H2O/*/line_list" 
	would select the line list dataset for all isotopologues of H2O, while "*/(16O2)/*" would select 
	all datasets for the (16O)2 isotopologue.
	
	Example:
		'H2O/(16O)(1H)2/MM30' would select the MM30 dataset for the (16O)(1H)2 isotopologue of H2O.
		'H2O/*/ZZ20_QQ' would select the ZZ20_QQ dataset for all isotopologues of H2O.
		'*/(16O)(1H)2/*' would select all datasets for the (16O)(1H)2 isotopologue of all molecules.
		'*/(16O)(1H)2/MM30|ZZ20_QQ' would select the MM30 and ZZ20_QQ datasets for the (16O)(1H)2 isotopologue of all molecules.
		'H2O/(16O)(1H)2/* CH4/(12C)(1H)4|(13C)(1H)4/*' would select all datasets for the (16O)(1H)2 isotopologue of H2O and all datasets for the (12C)(1H)4 and (13C)(1H)4 isotopologues of CH4.
	"""
	if len(dss) == 0:
		dss = '*'
	
	dss_parts = dss.split()
	
	results = []
	if multi:
		for dss_part in dss_parts:
			results.extend(dataset_selector_factory(dss_part, multi=False))
		return DatasetSelector(tuple(results))
	
	if dss[0] == '/':
		dss = '*' + dss
	
	if (n_slash := dss.count('/')) < 2:
		dss += '/*'*(2-n_slash)
		
	mol, iso_str, dataset_name_str = dss.split('/')
	isos = iso_str.split('|')
	dataset_names = dataset_name_str.split('|')
	
	for iso in isos:
		for dataset_name in dataset_names:
			results.append(SingleDatasetSelector(
				Molecule.from_str(mol) if mol!='*' else None, 
				Isotopologue.from_str(iso) if iso!='*' else None, 
				dataset_name if dataset_name != '*' else None
			)
		)
	
	return results


ALL_DATASET_SELECTOR = dataset_selector_factory('*/*/*')


