"""
Holds very simple types that can be thought of as nicely arranged data.
"""


from typing import NamedTuple
from enum import IntEnum


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

class BroadeningSourceCode(IntEnum):
	UNKNOWN            = 0
	BROAD_FILE         = 1
	GAS_DEFAULT        = -1
	ISO_DEFAULT        = -2
	EMERGENCY_FALLBACK = -3