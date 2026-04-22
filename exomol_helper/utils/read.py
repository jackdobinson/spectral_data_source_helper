
from pathlib import Path
from typing import Generator, Callable, Iterable#, Any
import bz2

import numpy as np

from exomol_helper.cfg.log import progress_lgr
from exomol_helper.cfg.log import pkg_logger as _lgr
import exomol_helper.utils.dtype

PROGRESS_INTERVAL = 100_000

def iter_line_records(
		fpaths : str | Path | list[str | Path],
) -> Generator[str]:
	if isinstance(fpaths, (str, Path)):
		fpaths = (fpaths,)
		
	for fpath in fpaths:
		if isinstance(fpath, str):
			fpath = Path(fpath)
		
		if fpath.suffix == '.bz2':
			with bz2.open(fpath, 'rb') as f:
				while f:
					yield f.readline().decode('ascii')
		else:
			with open(fpath, 'r') as f:
				while f:
					yield f.readline()


def load_line_records_into_structured_array(
		fpaths : str | Path | list[str | Path],
		dtype : np.dtype,
		shape : None | int | tuple[int,...] = None,
		widths : None | int | tuple[int,...] = None,
		delim : None | str = '',
		mutator : None | Callable[[Iterable],Iterable] = None,
		line_mutator : None | Callable[[str], None|str] = None
) -> np.ndarray:
	if isinstance(fpaths, (str, Path)):
		fpaths = (fpaths,)
		
	if (widths is not None and delim!='') or (widths is None and delim==''):
		raise RuntimeError('Must specify exactly a single one of `widths` and `delim`')

	if shape is None:
		return load_line_records_into_structured_array_by_chunks(fpaths, dtype, widths=widths, delim=delim)
	
	if isinstance(shape, int):
		shape = (shape,)
	
	ndim_larger_than_one = len(shape) > 1
	
	result = np.empty((np.prod(shape),), dtype=dtype)
	
	i=0
	
	if delim != '':
		for v in iter_line_records(fpaths):
		
			if line_mutator is not None:
				mutated_result = line_mutator(v)
				if mutated_result is not None:
					v = mutated_result
		
			ss = v.split(delim)
			if len(ss) == 0 or len(v)==0:
				break
			
			if i%PROGRESS_INTERVAL == 0:
				progress_lgr.info(f'{i=} ##{v}')
			
			if mutator is not None:
				ss = mutator(ss)
				
			#result[i] = tuple(dtype[j][1](x) if not isinstance(dtype[j][1],str) else x for j,x in enumerate(ss))
			try:
				result[i] = exomol_helper.utils.dtype.structured_data_tuple_from(dtype, ss)
			except Exception as e:
				_lgr.error(f'{i=} {v[:80]=}')
				raise e
			i+=1
	
	elif widths is not None:
		cwidths = tuple(sum(widths[:i]) for i in range(len(widths)))
		for x in iter_line_records(fpaths):
			if len(x) ==0:
				break
			
			if line_mutator is not None:
				mutated_result = line_mutator(x)
				if mutated_result is not None:
					x = mutated_result
			
			if i%PROGRESS_INTERVAL == 0:
				progress_lgr.info(f'{i=} ##{x}')
			
			ss = (x[c:c+w] for c,w in zip(cwidths, widths))
			if mutator is not None:
				ss = mutator(ss)
			
			try:
				#result[i] = tuple(dtype[j][1](x[c:c+w]) if not isinstance(dtype[j][1],str) else x[c:c+w] for j,c,w in enumerate(zip(cwidths, widths)))
				result[i] = exomol_helper.utils.dtype.structured_data_tuple_from(dtype, ss)
			except Exception as e:
				_lgr.error(f'{i=} {x[:80]=}')
				raise e
			i+=1
	
	else:
		raise RuntimeError('Must specify exactly a single one of `widths` and `delim`')
	
	_lgr.info(f'{shape=}')
	if ndim_larger_than_one:
		return result.reshape(shape)
	else:
		return result




def load_line_records_into_structured_array_by_chunks(
		fpaths : str | Path | list[str | Path],
		dtype : np.dtype,
		widths : None | int | tuple[int,...] = None,
		delim : None | str = '',
		chunk_size : int = 1_000_000,
		mutator : None | Callable[[Iterable],Iterable] = None,
		line_mutator : None | Callable[[str], None|str] = None
) -> np.ndarray:
	if isinstance(fpaths, (str, Path)):
		fpaths = (fpaths,)
		
	if (widths is not None and delim!='') or (widths is None and delim==''):
		raise RuntimeError('Must specify exactly a single one of `widths` and `delim`')

	results = []
	chunk = np.empty((chunk_size,), dtype=dtype)
	
	i=0
	nn = 0
	mm = chunk_size

	if delim != '':
		for v in iter_line_records(fpaths):
			
			if line_mutator is not None:
				mutated_result = line_mutator(v)
				if mutated_result is not None:
					v = mutated_result
			
			ss = v.split(delim)
			if len(ss) == 0 or len(v)==0:
				break
			
			if i >= mm:
				results.append(chunk)
				chunk = np.empty((chunk_size,), dtype=dtype)
				nn+=chunk_size
				mm+=chunk_size
				
			#if i%PROGRESS_INTERVAL == 0:
			if progress_lgr.is_ready():
				progress_lgr.info(f'{i=} ##{v}')
			
			if mutator is not None:
				ss = mutator(ss)
			try:
				#chunk[i-nn] = tuple(dtype[j][1](x) if not isinstance(dtype[j][1],str) else x for j,x in enumerate(ss))
				#chunk[i-nn] = tuple(dtype[j].type(x) for j,x in enumerate(ss))
				chunk[i-nn] = exomol_helper.utils.dtype.structured_data_tuple_from(dtype, ss)
			except Exception as e:
				_lgr.error(f'{i=} {v[:80]=}')
				raise e
			i+=1
	
	elif widths is not None:
		cwidths = tuple(sum(widths[:i]) for i in range(len(widths)))
		for x in iter_line_records(fpaths):
			if len(x) ==0:
				break
			
			if line_mutator is not None:
				mutated_result = line_mutator(x)
				if mutated_result is not None:
					x = mutated_result
			
			if i >= mm:
				results.append(chunk)
				chunk = np.empty((chunk_size,), dtype=dtype)
				nn+=chunk_size
				mm+=chunk_size
				
			#if i%PROGRESS_INTERVAL == 0:
			if progress_lgr.is_ready():
				progress_lgr.info(f'{i=} ##{x}')
			
			ss = (x[c:c+w] for c,w in zip(cwidths, widths))
			if mutator is not None:
				ss = mutator(ss)
			try:
				#chunk[i-nn] = tuple(dtype[j][1](x[c:c+w]) if not isinstance(dtype[j][1],str) else x[c:c+w] for j,c,w in enumerate(zip(cwidths, widths)))
				#chunk[i-nn] = tuple(dtype[j].type(x[c:c+w]) for j,c,w in enumerate(zip(cwidths, widths)))
				chunk[i-nn] = exomol_helper.utils.dtype.structured_data_tuple_from(dtype, ss)
			except Exception as e:
				_lgr.error(f'{i=} {x[:80]=}')
				raise e
			i+=1
	
	else:
		raise RuntimeError('Must specify exactly a single one of `widths` and `delim`')
	
	results.append(chunk[:i-nn])
	
	return np.concatenate(results)


def iter_line_records_via_structured_array_chunk(
		fpaths : str | Path | list[str | Path], 
		dtype : np.dtype,
		widths : None | int | tuple[int,...] = None,
		delim : None | str = '',
		chunk_size : int = 1_000_000,
		mutator : None | Callable[[Iterable],Iterable] = None,
		line_mutator : None | Callable[[str], None|str] = None
) -> np.ndarray:
	if isinstance(fpaths, (str, Path)):
		fpaths = (fpaths,)

	if (widths is not None and delim!='') or (widths is None and delim==''):
		raise RuntimeError('Must specify exactly a single one of `widths` and `delim`')

	chunk = np.empty((chunk_size,), dtype=dtype)
	
	i=0
	nn = 0
	mm = chunk_size

	if delim != '':
		for v in iter_line_records(fpaths):
			
			if line_mutator is not None:
				mutated_result = line_mutator(v)
				if mutated_result is not None:
					v = mutated_result
			
			ss = v.split(delim)
			if len(ss)==0 or len(v)==0:
				break
			if i >= mm:
				yield chunk
				nn+=chunk_size
				mm+=chunk_size
				
			#if i%PROGRESS_INTERVAL == 0:
			if progress_lgr.is_ready():
				progress_lgr.info(f'{i=} ##{v}')
			
			if mutator is not None:
				ss = mutator(ss)
			
			try:
				#chunk[i-nn] = tuple(dtype[j][1](x) if not isinstance(dtype[j][1],str) else x for j,x in enumerate(ss))
				#chunk[i-nn] = tuple(dtype[j].type(x) for j,x in enumerate(ss))
				chunk[i-nn] = exomol_helper.utils.dtype.structured_data_tuple_from(dtype, ss)
			except Exception as e:
				_lgr.error(f'{i=} {v[:80]=}')
				raise e
			i+=1
	
	elif widths is not None:
		cwidths = tuple(sum(widths[:i]) for i in range(len(widths)))
		for x in iter_line_records(fpaths):
			
			if line_mutator is not None:
				mutated_result = line_mutator(x)
				if mutated_result is not None:
					x = mutated_result
			
			if len(x) == 0:
				break
			if i >= mm:
				yield chunk
				nn+=chunk_size
				mm+=chunk_size
				
			#if i%PROGRESS_INTERVAL == 0:
			if progress_lgr.is_ready():
				progress_lgr.info(f'{i=} ##{x}')
			
			ss = (x[c:c+w] for c,w in zip(cwidths, widths))
			if mutator is not None:
				ss = mutator(ss)
			
			try:
				#chunk[i-nn] = tuple(dtype[j][1](x[c:c+w]) if not isinstance(dtype[j][1],str) else x[c:c+w] for j,c,w in enumerate(zip(cwidths, widths)))
				#chunk[i-nn] = tuple(dtype[j].type(x[c:c+w]) for j,c,w in enumerate(zip(cwidths, widths)))
				chunk[i-nn] = exomol_helper.utils.dtype.structured_data_tuple_from(dtype, ss)
			except Exception as e:
				_lgr.error(f'{i=} {x[:80]=}')
				raise e
			i+=1
	
	else:
		raise RuntimeError('Must specify exactly a single one of `widths` and `delim`')
	
	yield chunk[:i-nn]












