
from pathlib import Path
from typing import NamedTuple, Annotated, get_args

import numpy as np


import exomol_helper.utils.dtype 
import exomol_helper.utils.read

MAX_STR_LEN = 32

class HitranIsotope(NamedTuple):
	mol_id : Annotated[int, "HITRAN molecular id"]
	global_id : Annotated[int, "HITRAN global isotopologue id"]
	iso_id : Annotated[int, "HITRAN local isotopologue id"]
	mol_mass : Annotated[float, ("g mol^{-1}", "Molar mass of isotope")]
	abundance : Annotated[float, ("NUMBER", "Terrestrial abundance of isotope")]
	q_ref : Annotated[float, ("NUMBER", "Partition function at 296 Kelvin")]
	mol_formula : Annotated[str, "Molecular formula"]
	iso_formula : Annotated[str, "Isotopologue formula"]
	
	@classmethod
	def record_array_from(
			cls, 
			fpath : Path, 
			chunk_size : int = 1_000,
		):
		return np.rec.array(cls.structured_array_from(fpath, chunk_size=chunk_size))
		
	@classmethod
	def structured_array_from(
			cls, 
			fpath : Path, 
			chunk_size : int = 1_000,
		):
		dtype = np.dtype([(name, get_args(anno)[0] if get_args(anno)[0] is not str else f'U{MAX_STR_LEN}') for name, anno in cls.__annotations__.items()])
		
		return exomol_helper.utils.read.load_line_records_into_structured_array_by_chunks(
			fpath,
			dtype,
			delim=None
		)
