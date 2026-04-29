
from pathlib import Path
from typing import Generator, Callable, Iterable#, Any
import bz2

import numpy as np

from exomol_helper.cfg.log import progress_lgr
from exomol_helper.cfg.log import pkg_logger as _lgr
import exomol_helper.utils.dtype
import exomol_helper.utils.structured_array

from .module_var import ModuleVar
from ..progress_tracker.base import BaseProgressTracker
from ..progress_tracker.chunk import ChunkProgressTracker

#import logging

PROGRESS_INTERVAL = 100_000


module_progress_sink : ModuleVar = ModuleVar(
	lambda x: print(str(x), end='\r', flush=True)
	#lambda x: progress_lgr.info(str(x))
)





def iter_lines_fast(
		f, 
		chunk_size=10*1024*1024,
):
	i = 0
	m = 0
	n = 0
	b = bytearray(b'\0'*chunk_size)
	s = memoryview(b)
	
	n = f.readinto1(s[i:])
	m = i+n
	
	while n > 0:
		lines = b[:m].split(b'\n')
		yield from ((len(x),x) for x in lines[:-1])
		i = len(lines[-1])
		s[:i] = lines[-1]
		n = f.readinto1(s[i:])
		m = i+n
		
	return m, b[:m]


def iter_lines_fast_bz2(
		f, 
		chunk_size=10*1024*1024,
):
	half_chunk = chunk_size // 2
	i = 0
	m = 0
	n = 0
	b = bytearray(b'\0'*chunk_size)
	s = memoryview(b)
	
	a = bytearray(b'\0'*chunk_size)
	r = memoryview(a)
	
	decomp = bz2.BZ2Decompressor()
	
	n = f.readinto1(s)
	
	while n > 0:
		x = decomp.decompress(b[:n], max_length=half_chunk)
		m = i+len(x)
		r[i:m] = x
		lines = a[:m].split(b'\n')
		yield from ((len(x),x) for x in lines[:-1])
		i = len(lines[-1])
		r[:i] = lines[-1]
				
		while not decomp.needs_input and not decomp.eof:
			x = decomp.decompress(b'', max_length=half_chunk)
			m = i+len(x)
			r[i:m] = x
			lines = a[:m].split(b'\n')
			yield from ((len(x),x) for x in lines[:-1])
			i = len(lines[-1])
			r[:i] = lines[-1]
		
		n = f.readinto1(s)
	
	return


def iter_line_records(
		fpaths : str | Path | list[str | Path],
		encoding : None | str = 'utf8',
) -> Generator[tuple[int,str] | tuple[int,bytes]]:
	if isinstance(fpaths, (str, Path)):
		fpaths = (fpaths,)
	
	for fpath in fpaths:
		_lgr.info(f'Starting to read {fpath=}')
		
		if isinstance(fpath, str):
			fpath = Path(fpath)
		
		if encoding is None:
			decoder = lambda x: x
		else:
			decoder = lambda x: x.decode(encoding)
		
		if fpath.suffix == '.bz2':
			line_iterator = iter_lines_fast_bz2
		else:
			line_iterator = iter_lines_fast
		
		with open(fpath, 'rb') as f:
			for n_bytes, line in line_iterator(f):
				yield n_bytes, decoder(line)
		
		_lgr.info(f'Finished reading {fpath=}')



def iter_line_records_via_structured_array_chunk(
		fpaths : str | Path | list[str | Path], 
		dtype : np.dtype,
		widths : None | int | tuple[int,...] = None,
		delim : None | str = '',
		chunk_size : int = 1_000_000,
		shape_tail : tuple[int,...] = tuple(),
		mutator : None | Callable[[Iterable],Iterable] = None,
		line_mutator : None | Callable[[str], None|str] = None,
		progress_tracker : None | BaseProgressTracker = None,
) -> np.ndarray:
	if isinstance(fpaths, (str, Path)):
		fpaths = (fpaths,)

	if (widths is not None and delim!='') or (widths is None and delim==''):
		raise RuntimeError('Must specify exactly a single one of `widths` and `delim`')

	chunk = np.empty((chunk_size,*shape_tail), dtype=dtype)
	
	if delim != '':
		str_to_iterable_func = lambda x: x.split(delim)
	elif widths is not None:
		cwidths = tuple(sum(widths[:i]) for i in range(len(widths)))
		str_to_iterable_func = lambda x: (x[c:c+w] for c,w in zip(cwidths, widths))
	else:
		raise RuntimeError('Must specify exactly a single one of `widths` and `delim`')
	
	i=0
	nn = 0
	mm = chunk_size
	total_bytes = 0

	for n_bytes, x in iter_line_records(fpaths):
		total_bytes += n_bytes
		
		if len(x)==0:
			continue
		
		if line_mutator is not None:
			mutated_result = line_mutator(x)
			if mutated_result is not None:
				x = mutated_result
		
		ss = str_to_iterable_func(x)
		if len(ss)==0:
			continue
		
		if i >= mm:
			if progress_tracker is not None:
				progress_tracker.set(i, total_bytes)
			yield chunk
			nn+=chunk_size
			mm+=chunk_size
			
		
		if mutator is not None:
			ss = mutator(ss)
		
		try:
			chunk[i-nn] = exomol_helper.utils.dtype.structured_data_tuple_from(dtype, ss)
		except:
			_lgr.error(f'{i=} {x[:80]=}')
			raise
		i+=1
	
	if progress_tracker is not None:
		progress_tracker.set(i, total_bytes)
	yield chunk[:i-nn]


def load_line_records_into_structured_array(
		fpaths : str | Path | list[str | Path],
		dtype : np.dtype,
		shape : None | int | tuple[int,...] = None,
		widths : None | int | tuple[int,...] = None,
		delim : None | str = '',
		mutator : None | Callable[[Iterable],Iterable] = None,
		line_mutator : None | Callable[[str], None|str] = None,
		progress_tracker : None | BaseProgressTracker = None,
) -> np.ndarray:
	
	if shape is None:
		return load_line_records_into_structured_array_by_chunks(fpaths, dtype, widths, delim, mutator=mutator, line_mutator=line_mutator, progress_tracker=progress_tracker)
	else:
		if isinstance(shape, int):
			shape = (shape,)
		return next(iter_line_records_via_structured_array_chunk(fpaths, dtype, widths, delim, shape[0], shape[1:], mutator, line_mutator, progress_tracker=progress_tracker))


def load_line_records_into_structured_array_by_chunks(
		fpaths : str | Path | list[str | Path],
		dtype : np.dtype,
		widths : None | int | tuple[int,...] = None,
		delim : None | str = '',
		chunk_size : int = 1_000_000,
		shape_tail : tuple[int,...] = tuple(),
		mutator : None | Callable[[Iterable],Iterable] = None,
		line_mutator : None | Callable[[str], None|str] = None,
		progress_tracker : None | BaseProgressTracker = None,
) -> np.ndarray:
	
	results = []
	
	for chunk in iter_line_records_via_structured_array_chunk(fpaths, dtype, widths, delim, chunk_size, shape_tail, mutator, line_mutator, progress_tracker=progress_tracker):
		results.append(np.array(chunk))
	
	return np.concatenate(results)





def files_via_structured_array_chunk(
		fpaths : str | Path | list[str | Path], 
		dtype : np.dtype,
		widths : None | int | tuple[int,...] = None,
		delim : None | str = '',
		chunk_size : int = 1_000_000,
		shape_tail : tuple[int,...] = tuple(),
		mutator : None | Callable[[Iterable],Iterable] = None,
		line_mutator : None | Callable[[str], None|str] = None
):
	_lgr.info('files_via_structured_array_chunk(...)')
	
	read_progress_tracker = ChunkProgressTracker(
		module_progress_sink.get(), 
		rate_limit_timeout = 0.5, 
		chunk_element_name='Record'
	)

	if isinstance(fpaths, (str, Path)):
		fpaths = (fpaths,)
	
	for fpath in fpaths:
		_lgr.debug(f'{fpath=}')
		
		ftype = fpath.suffix
		
		if ftype in ('.bz2',):
			ftype = fpath.with_suffix('').suffix
		
		if ftype in ('.trans'):
			yield from iter_line_records_via_structured_array_chunk(
				fpath,
				dtype,
				widths,
				delim,
				chunk_size,
				shape_tail,
				mutator,
				line_mutator,
				progress_tracker=read_progress_tracker,
			)
		elif ftype in ('.bin',):
			
			chunk_number = 0
			
			f = exomol_helper.utils.structured_array.StructuredArrayFile(fpath, 'rb')
			result = f.read(count = chunk_size)
			
			while result.size > 0:
				chunk_number += 1
				read_progress_tracker.set(f.n_records_read, f.tell())
				
				yield result
				result = f.read(count = chunk_size)
				
				
				
		elif ftype in ('.npy',):
			array = np.load(fpath)
			
			i = 0
			n = chunk_size
			n_records_read = 0
			while n < array.size:
				n_records_read =+ n
				read_progress_tracker.set(n_records_read, array.nbytes)
				yield array[i:n]
				i += chunk_size
				n += chunk_size
		
		elif ftype in ('.npz',):
			npz_file = np.load(fpath)
			
			arrays = tuple(npz_file.values())
			
			i = np.zeros(len(arrays), dtype=int)
			n = np.ones(len(arrays), dtype=int) * chunk_size
			s = np.array([a.shape[0] for a in arrays], dtype=int)
			
			m = np.zeros(len(arrays), dtype=int)
			b = np.array([a.nbytes for a in arrays], dtype=int)
			
			while np.any(n < s):
				m += (n<s) * chunk_size
				read_progress_tracker.set(m, b)
				
				yield tuple(a[_i : _n] if _n < _s else a[0:0] for a, _i, _n, _s in zip(arrays, i, n, s))
				i += chunk_size
				n += chunk_size
			
			
			
		else:
			raise RuntimeError(f'Unknown format to read "{ftype}"')


			
	
	
	
	







