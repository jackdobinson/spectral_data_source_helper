from pathlib import Path
from typing import NamedTuple, Annotated, get_args, get_origin, Union, Generator

import numpy as np

import spectral_data_source_helper.utils.read

from ..cfg.const import HITRAN_ISO_ID_FROM_SINGLE_CHAR_MAP

Hitran160Layout = (2,1,12,10,10,5,5,10,4,8,15,15,15,15,(1,1,1,1,1,1),(2,2,2,2,2,2),1,7,7)

class Hitran160Record(NamedTuple):
	"""
	Fixed width format can be specified like a table with the following columns:

	attribute name                     : type                           = width (in ascii characters)
	"""
	mol_id                             : Annotated[int, "molecular id", 2]
	iso_id                             : Annotated[int, 'isotopologue id', 1]
	line_wavenumber                    : Annotated[float, "", 12]
	line_strength                      : Annotated[float, "", 10]
	einstein_a_coeff                   : Annotated[float, "", 10]
	gamma_amb                          : Annotated[float, "", 5]
	gamma_self                         : Annotated[float, "", 5]
	e_lower                            : Annotated[float, "", 10 ]
	n_amb                              : Annotated[float, "", 4]
	delta_amb                          : Annotated[float, "", 8]
	global_upper_quanta                : Annotated[str, "", 15]
	global_lower_quanta                : Annotated[str, "", 15]
	local_upper_quanta                 : Annotated[str, "", 15]
	local_lower_quanta                 : Annotated[str, "", 15]
	#ierr                               : Annotated[tuple[int,int,int,int,int,int], "", (1,1,1,1,1,1)]
	ierr                               : Annotated[str, "", 6]
	#iref                               : Annotated[tuple[int,int,int,int,int,int], "", (2,2,2,2,2,2)]
	iref                               : Annotated[str, "", 12]
	line_mixing_flag                   : Annotated[str, "", 1]
	gp                                 : Annotated[float, "", 7]
	gpp                                : Annotated[float, "", 7]

	@classmethod
	def dtype(cls) -> np.dtype:
		def get_dtype(t, use_var_strings=False, max_str_len=32):
		
			ot = get_origin(t)
			if ot is None:
				if t == str:
					return np.dtype('T') if use_var_strings else np.dtype(f'U{max_str_len}')
				else:
					return np.dtype(t)
			if ot == Union:
				t = get_args(t)[0]
				if t == str:
					return np.dtype('T') if use_var_strings else np.dtype(f'U{max_str_len}')
				else:
					return np.dtype(t)
			else:
				tt = get_args(t)
				if all (x == tt[0] for x in tt):
					t= get_dtype(tt[0])
					return np.dtype((t.type,(len(tt),*t.shape)))
				else:
					ts = []
					for xt in tt:
						t = get_dtype(xt)
						ts.append(
							('', t)
						)
					return np.dtype(ts)
		names = []
		types = []
		descriptions = []
		widths = []
		dtypes = []
		for nn,anno in cls.__annotations__.items():
			(tt,dd,ww) = get_args(anno)
			names.append(nn)
			types.append(tt)
			descriptions.append(dd)
			widths.append(ww)
			dtypes.append(get_dtype(tt, use_var_strings=False, max_str_len=ww))
		
		return np.dtype({"names":names, "formats":dtypes})
	
	@classmethod
	def widths(cls):
		return dict((nn,get_args(anno)[2]) for nn,anno in cls.__annotations__.items())

	@classmethod
	def structured_array_from(
			cls, 
			fpath : Path, 
			chunk_size : int = 1_000,
	):
		
		# Account for `iso_id` values greater than 9 when only have a single digit to use
		mutator = lambda it: (x if i!=1 else HITRAN_ISO_ID_FROM_SINGLE_CHAR_MAP.get(x,x) for i,x in enumerate(it))
		
		return spectral_data_source_helper.utils.read.load_line_records_into_structured_array_by_chunks(
			fpath,
			cls.dtype(),
			widths=tuple(cls.widths().values()),
			mutator=mutator
		)
	
	@classmethod
	def iter_structured_array_from(
			cls, 
			fpath : Path, 
			chunk_size : int = 1_000,
	) -> Generator[np.ndarray]:
		
		# Account for `iso_id` values greater than 9 when only have a single digit to use
		mutator = lambda it: (x if i!=1 else HITRAN_ISO_ID_FROM_SINGLE_CHAR_MAP.get(x,x) for i,x in enumerate(it))
		
		yield from spectral_data_source_helper.utils.read.iter_line_records_via_structured_array_chunk(
			fpath,
			cls.dtype(),
			widths=tuple(cls.widths().values()),
			mutator=mutator
		)