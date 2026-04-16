"""
Holds very simple types that can be thought of as nicely arranged data.
"""


from typing import NamedTuple


class IsotopeInfo(NamedTuple):
	formula : str
	slug : str

class IsoDatasetsList(NamedTuple):
	iso_slug : str
	dataset_names : list[str]

class ExomolDatasetInfo(NamedTuple):
	mol_formula : str
	iso_formula : str
	iso_slug : str
	dataset_name : str