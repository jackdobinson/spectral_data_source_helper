


from pathlib import Path
from typing import NamedTuple, Annotated, get_args

import numpy as np


import exomol_helper.utils.dtype 

MAX_STR_LEN = 32

class PartitionFunctionEntry(NamedTuple):
	temp : Annotated[int, ('K', "Temperature")]
	q : Annotated[float, "partition function at temperature"]
	
	@classmethod
	def structured_array_from(
			cls, 
			fpath : Path, 
			chunk_size : int = 1_000,
		):
		result_list = []
		
		dtype = np.dtype([(name, get_args(anno)[0] if get_args(anno)[0] is not str else f'U{MAX_STR_LEN}') for name, anno in cls.__annotations__.items()])
		arr = np.empty((chunk_size,), dtype=dtype)
		
		i = 0
		n_chunks = 0
		with open(fpath, 'r') as f:
			for aline in f:
				
				if i >= (n_chunks+1)*chunk_size:
					result_list.append(arr)
					arr = np.empty((chunk_size,), dtype=dtype)
					n_chunks += 1
				
				
				x = aline.strip().split()
				#print(f'{x=} {n_chunks=}')
				if len(x) == 0:
					continue
				arr[i - (chunk_size * n_chunks)] = exomol_helper.utils.dtype.structured_data_from(dtype, x)
				
				i += 1
		
		result_list.append(arr[:i])
		
		return np.concatenate(result_list)