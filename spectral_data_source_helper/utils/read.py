


from pathlib import Path
from typing import Generator, Callable, Iterable#, Any
import bz2
import lzma
#import compression.zstd # Added in 3.14
#import subprocess


import numpy as np

from spectral_data_source_helper.cfg.log import progress_lgr
from spectral_data_source_helper.cfg.log import pkg_logger as _lgr
import spectral_data_source_helper.utils.dtype
import spectral_data_source_helper.utils.structured_array

from .module_var import ModuleVar
from .binary_reader import DecompressorProtocol, BinaryReader
from ..progress_tracker.base import BaseProgressTracker
from ..progress_tracker.chunk import ChunkProgressTracker

#import logging

PROGRESS_INTERVAL = 100_000


module_progress_sink : ModuleVar = ModuleVar(
	#lambda x: print(str(x), end='\r', flush=True)
	lambda x: progress_lgr.info(str(x), stacklevel=4)
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

def iter_lines_fast_compressed(
		f, 
		decomp : DecompressorProtocol,
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

def iter_lines_fast_bz2(
		f, 
		chunk_size=10*1024*1024,
):
	yield from iter_lines_fast_compressed(f, bz2.BZ2Decompressor(), chunk_size=chunk_size)

def iter_lines_fast_xz(
		f, 
		chunk_size=10*1024*1024,
):
	print('LZMA compression')
	yield from iter_lines_fast_compressed(f, lzma.LZMADecompressor(), chunk_size=chunk_size)

"""
# Added in 3.14
def iter_lines_fast_zst(
		f, 
		chunk_size=10*1024*1024,
):
	yield from iter_lines_fast_compressed(f, compression.zstd.ZstdDecompressor(), chunk_size=chunk_size)
"""

def iter_line_records(
		fpaths : str | Path | list[str | Path],
		encoding : None | str = 'utf8',
) -> Generator[tuple[int,str] | tuple[int,bytes]]:
	if isinstance(fpaths, (str, Path)):
		fpaths = (fpaths,)
	
	for fpath in fpaths:
		#_lgr.info(f'Starting to read {fpath=}')
		print(f'Starting to read {fpath=}')
		
		if isinstance(fpath, str):
			fpath = Path(fpath)
		
		if encoding is None:
			decoder = lambda x: x
		else:
			decoder = lambda x: x.decode(encoding)
			
		if fpath.suffix in ('.bz2',):
			decomp = bz2.BZ2Decompressor()
		elif fpath.suffix in ('.xz', '.lzma'):
			decomp = lzma.LZMADecompressor()
		else:
			decomp = None
		
		b_reader = BinaryReader(decompressor = decomp)
		with open(fpath, 'rb') as f:
			b_reader.set_source(f)
			for n_bytes, line in b_reader.iter_lines():
				yield n_bytes, decoder(line)
		
		
		"""
		if fpath.suffix in ('.bz2',):
			line_iterator = iter_lines_fast_bz2
		elif fpath.suffix in ('.xz', '.lzma'):
			line_iterator = iter_lines_fast_xz
		#elif fpath.suffix in ('.zst',): # added in 3.14
		#	line_iterator = iter_lines_fast_zst
		else:
			line_iterator = iter_lines_fast
		
		
		with open(fpath, 'rb') as f:
			for n_bytes, line in line_iterator(f):
				#print(f'{n_bytes=}')
				yield n_bytes, decoder(line)
		"""
		
		_lgr.info(f'Finished reading {fpath=}')



def iter_line_records_via_structured_array_chunk_simple(
		fpaths : str | Path | list[str | Path], 
		dtype : np.dtype,
		widths : None | int | tuple[int,...] = None,
		delim : None | str = '',
		chunk_size : int = 1_000_000,
		progress_tracker : None | BaseProgressTracker = None,
) -> np.ndarray:
	if isinstance(fpaths, (str, Path)):
		fpaths = (fpaths,)

	if (widths is not None and delim!='') or (widths is None and delim==''):
		raise RuntimeError('Must specify exactly a single one of `widths` and `delim`')

	chunk = np.empty((chunk_size,), dtype=dtype)
	
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
	
	bytes_in_chunk = 0

	for n_bytes, x in iter_line_records(fpaths):
		bytes_in_chunk += n_bytes
		
		if len(x)==0:
			continue
		
		ss = str_to_iterable_func(x)
		if len(ss)==0:
			continue
		
		if i >= mm:
			if progress_tracker is not None:
				progress_tracker.set(chunk_size, bytes_in_chunk)
			yield chunk
			nn+=chunk_size
			mm+=chunk_size
			bytes_in_chunk = 0
		
		try:
			chunk[i-nn] = spectral_data_source_helper.utils.dtype.structured_data_tuple_from(dtype, ss)
		except:
			_lgr.error(f'{i=} {x[:80]=}')
			raise
		i+=1
	
	if progress_tracker is not None:
		progress_tracker.set(i-nn, bytes_in_chunk)
	yield chunk[:i-nn]


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
	
	bytes_in_chunk = 0

	for n_bytes, x in iter_line_records(fpaths):
		bytes_in_chunk += n_bytes
		
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
				progress_tracker.set(chunk_size, bytes_in_chunk)
			yield chunk
			nn+=chunk_size
			mm+=chunk_size
			bytes_in_chunk = 0
			
		
		if mutator is not None:
			ss = mutator(ss)
		
		try:
			chunk[i-nn] = spectral_data_source_helper.utils.dtype.structured_data_tuple_from(dtype, ss)
		except:
			_lgr.error(f'{i=} {x[:80]=}')
			raise
		i+=1
	
	if progress_tracker is not None:
		progress_tracker.set(i-nn, bytes_in_chunk)
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



def bin_file_dtype(
	fpath : Path,
):
	if fpath.suffix in ('.bz2',):
		reader = BinaryReader(decompressor=bz2.BZ2Decompressor())
	elif fpath.suffix in ('.xz',):
		reader = BinaryReader(decompressor=lzma.LZMADecompressor())
	else:
		reader = None
	with spectral_data_source_helper.utils.structured_array.StructuredArrayFile(fpath, 'rb',reader=reader) as f:
		return f.read_dtype()


def bin_file_into_structured_array_chunks(
	fpath : Path,
	chunk_size : int = 1_000_000,
	dtype : None | np.dtype = None,
	progress_tracker : None | BaseProgressTracker = None
	
) -> Generator[np.ndarray]:

	if fpath.suffix in ('.bz2',):
		reader = BinaryReader(decompressor=bz2.BZ2Decompressor())
	elif fpath.suffix in ('.xz',):
		reader = BinaryReader(decompressor=lzma.LZMADecompressor())
	else:
		reader = None

	n_bytes_read = 0
	prev_n_bytes_read = 0
	f = spectral_data_source_helper.utils.structured_array.StructuredArrayFile(fpath, 'rb',reader=reader)
	result = f.read(count = chunk_size)
	
	mutate_result = False
	if dtype is not None and dtype != result.dtype:
		mutate_result = True
		chunk = np.zeros((chunk_size,), dtype=dtype)
	
	
	while result.size > 0:
		if mutate_result:
			for name in result.dtype.names:
				chunk[name][*(slice(s) for s in result.shape)] = result[name]
			result = chunk
		
		n_bytes_read = f.tell()
		if progress_tracker is not None:
			progress_tracker.set(result.size, n_bytes_read - prev_n_bytes_read)
		prev_n_bytes_read = n_bytes_read
		
		yield result
		result = f.read(count = chunk_size)

def files_via_structured_array_chunk(
		fpaths : str | Path | list[str | Path], 
		dtype : np.dtype,
		widths : None | int | tuple[int,...] = None,
		delim : None | str = '',
		chunk_size : int = 1_000_000,
		shape_tail : tuple[int,...] = tuple(),
		mutator : None | Callable[[Iterable],Iterable] = None,
		line_mutator : None | Callable[[str], None|str] = None,
		progress_tracker : None | BaseProgressTracker = None,
		yield_fpath : bool = False,
):
	_lgr.info('files_via_structured_array_chunk(...)')
	
	if progress_tracker is None:
		progress_tracker = ChunkProgressTracker(
			module_progress_sink.get(), 
			rate_limit_timeout = 0.5, 
			chunk_element_name='Record'
		)

	if isinstance(fpaths, (str, Path)):
		fpaths = (fpaths,)
	
	for fpath in fpaths:
		progress_tracker.source_name = fpath.name
		_lgr.debug(f'{fpath=}')
		
		ftype = fpath.suffix
		
		if ftype in ('.bz2','.xz'):
			xpath = fpath.with_suffix('')
			ftype = xpath.suffix
			
			if False and xpath.exists():
				# If the extracted file is alredy present, use it
				fpath = xpath
			"""
			elif xpath.exists() or xpath.suffix in ('.bin', '.bin32'):
				# Handle these ones by using python's internal bzip implementation
				pass
			else:
				# Handle these ones by unzipping into a temporary location first using operating system 
				xpath_already_existed = xpath.exists()
				
				finished_process = subprocess.run(
					#f"bzip2 -kd {fpath}",
					f"lbzip2 -kd {fpath}",
					shell=True
				)
				
				if finished_process.returncode != 0:
					print(finished_process.args)
					print(finished_process.stdout)
					print(finished_process.stderr)
					raise RuntimeError('Unzipping failed')
				
				if not xpath.exists():
					raise RuntimeError('Unzipping did not put data into correct file')
				
				
				try:
					yield from files_via_structured_array_chunk(
						xpath,
						dtype,
						widths = widths,
						delim = delim,
						chunk_size = chunk_size,
						shape_tail = shape_tail,
						mutator = mutator,
						line_mutator = line_mutator,
						progress_tracker = progress_tracker,
						yield_fpath = yield_fpath,
					)
				finally:
					if not xpath_already_existed:
						xpath.unlink() # remove unzipped file if it did not already exist
					
				return
			"""
		
		if ftype in ('.trans'):
			gen = iter_line_records_via_structured_array_chunk_simple(
				fpath,
				dtype,
				widths,
				delim,
				chunk_size,
				progress_tracker=progress_tracker,
			)
			if yield_fpath:
				for chunk in gen:
					yield fpath, chunk
			else:
				yield from gen
		elif ftype in ('.bin','.bin32'):
			
			gen = bin_file_into_structured_array_chunks(
				fpath,
				chunk_size=chunk_size,
				dtype=dtype,
				progress_tracker=progress_tracker
			)
			if yield_fpath:
				for chunk in gen:
					yield fpath, chunk
			else:
				yield from gen
				
				
		elif ftype in ('.npy',):
			array = np.load(fpath)
			
			i = 0
			n = chunk_size
			while n < array.size:
				progress_tracker.set(chunk_size, array.nbytes*(chunk_size/array.shape[0]))
				if yield_fpath:
					yield fpath, array[i:n]
				else:
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
				progress_tracker.set(n - m, b*((m-n)/s))
				if yield_fpath:
					yield fpath, tuple(a[_i : _n] if _n < _s else a[0:0] for a, _i, _n, _s in zip(arrays, i, n, s))
				else:
					yield tuple(a[_i : _n] if _n < _s else a[0:0] for a, _i, _n, _s in zip(arrays, i, n, s))
				m[...] = n
				i += chunk_size
				n += chunk_size
				
			
			
			
		else:
			raise RuntimeError(f'Unknown format to read "{ftype}"')


			
	
	
	
	







