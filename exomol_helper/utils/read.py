
from pathlib import Path
from typing import Generator, Callable, Iterable#, Any
import bz2
import datetime as dt

import numpy as np

from exomol_helper.cfg.log import progress_lgr
from exomol_helper.cfg.log import pkg_logger as _lgr
import exomol_helper.utils.dtype
import exomol_helper.utils.structured_array

import logging

PROGRESS_INTERVAL = 100_000

def iter_line_records(
		fpaths : str | Path | list[str | Path],
		return_total_bytes_read = False,
) -> Generator[str | tuple[int,str]]:
	if isinstance(fpaths, (str, Path)):
		fpaths = (fpaths,)
	
	total_bytes_read = 0
	
	for fpath in fpaths:
		_lgr.info(f'Starting to read {fpath=}')
		
		if isinstance(fpath, str):
			fpath = Path(fpath)
		
		if fpath.suffix == '.bz2':
			opener = lambda x: bz2.open(x, 'rb')
			decoder = lambda x: x.decode('ascii')
		else:
			opener = lambda x: open(x, 'r')
			decoder = lambda x: x
		
		if return_total_bytes_read:
			with opener(fpath) as f:
				for line in f:
					total_bytes_read += len(line)# technically this may not give exact values due to differences in encoding
					yield total_bytes_read, decoder(line)
		else:
			with opener(fpath) as f:
				for line in f:
					yield decoder(line)
		
		_lgr.info(f'Finished reading {fpath=}')


def load_line_records_into_structured_array(
		fpaths : str | Path | list[str | Path],
		dtype : np.dtype,
		shape : None | int | tuple[int,...] = None,
		widths : None | int | tuple[int,...] = None,
		delim : None | str = '',
		mutator : None | Callable[[Iterable],Iterable] = None,
		line_mutator : None | Callable[[str], None|str] = None
) -> np.ndarray:
	
	if shape is None:
		return load_line_records_into_structured_array_by_chunks(fpaths, dtype, widths, delim, mutator=mutator, line_mutator=line_mutator)
	else:
		if isinstance(shape, int):
			shape = (shape,)
		return next(iter_line_records_via_structured_array_chunk(fpaths, dtype, widths, delim, shape[0], shape[1:], mutator, line_mutator))
	




def load_line_records_into_structured_array_by_chunks(
		fpaths : str | Path | list[str | Path],
		dtype : np.dtype,
		widths : None | int | tuple[int,...] = None,
		delim : None | str = '',
		chunk_size : int = 1_000_000,
		shape_tail : tuple[int,...] = tuple(),
		mutator : None | Callable[[Iterable],Iterable] = None,
		line_mutator : None | Callable[[str], None|str] = None
) -> np.ndarray:
	
	results = []
	
	for chunk in iter_line_records_via_structured_array_chunk(fpaths, dtype, widths, delim, chunk_size, shape_tail, mutator, line_mutator):
		results.append(np.array(chunk))
	
	return np.concatenate(results)


def iter_line_records_via_structured_array_chunk(
		fpaths : str | Path | list[str | Path], 
		dtype : np.dtype,
		widths : None | int | tuple[int,...] = None,
		delim : None | str = '',
		chunk_size : int = 1_000_000,
		shape_tail : tuple[int,...] = tuple(),
		mutator : None | Callable[[Iterable],Iterable] = None,
		line_mutator : None | Callable[[str], None|str] = None
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

	last_total_bytes_read = 0
	delta_bytes_read = 0
	
	dt_start = dt.datetime.now()
	dt_last_split = dt_start

	for total_bytes_read, x in iter_line_records(fpaths, return_total_bytes_read=True):
		#print(f'{x=}')
		
		
		
		
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
			yield chunk
			nn+=chunk_size
			mm+=chunk_size
			
		#if i%PROGRESS_INTERVAL == 0:
		if progress_lgr.is_ready():
			delta_bytes_read = total_bytes_read - last_total_bytes_read
			
			dt_split = dt.datetime.now()
			dt_elapsed_delta = dt_split - dt_start
			dt_elapsed_str = f'{dt_elapsed_delta.days}D {dt_elapsed_delta.seconds//3600}H {(dt_elapsed_delta.seconds %3600)//60}M {dt_elapsed_delta.seconds%60}s'
			dt_elapsed_sec = dt_elapsed_delta.total_seconds()
			
			dt_rolling_sec = (dt_split - dt_last_split).total_seconds()
			
			total_bytes_per_sec = total_bytes_read / dt_elapsed_sec
			rolling_bytes_per_sec = delta_bytes_read / dt_rolling_sec
			
			byte_amounts_and_unit = ((1,'kb'), (1000,'kb'), (1_000_000, 'Mb'), (1_000_000_000, 'Gb'))
			
			byte_unit_info = [byte_amounts_and_unit[0],byte_amounts_and_unit[0]]
			for byte_amount, byte_unit in byte_amounts_and_unit:
				if total_bytes_per_sec > byte_amount:
					byte_unit_info[0] = (byte_amount, byte_unit)
				if rolling_bytes_per_sec > byte_amount:
					byte_unit_info[1] = (byte_amount, byte_unit)
				
			if progress_lgr.level == logging.INFO:
				print(f'line_no : {i}')
				print(f'Elapsed Time: {dt_elapsed_str}')
				print(f'Total bytes per second: {total_bytes_per_sec/byte_unit_info[0][0]:8.3f} {byte_unit_info[0][1]}/s')
				print(f'Rolling bytes per second: {rolling_bytes_per_sec/byte_unit_info[1][0]:8.3f} {byte_unit_info[1][1]}/s')
				progress_lgr.info(f'####:{x}')
			
			dt_last_split = dt_split
			last_total_bytes_read = total_bytes_read
			
		
		if mutator is not None:
			ss = mutator(ss)
		
		try:
			#chunk[i-nn] = tuple(dtype[j][1](x) if not isinstance(dtype[j][1],str) else x for j,x in enumerate(ss))
			#chunk[i-nn] = tuple(dtype[j].type(x) for j,x in enumerate(ss))
			chunk[i-nn] = exomol_helper.utils.dtype.structured_data_tuple_from(dtype, ss)
		except:
			_lgr.error(f'{i=} {x[:80]=}')
			raise
		i+=1
	
	yield chunk[:i-nn]




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
	if isinstance(fpaths, (str, Path)):
		fpaths = (fpaths,)
	
	dt_start = dt.datetime.now()
	dt_last_split = dt_start
	
	for fpath in fpaths:
		print(f'{fpath=}')
		
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
				line_mutator
			)
		elif ftype in ('.bin',):
			
			last_total_bytes_read = 0
			
			chunk_number = 0
			f = exomol_helper.utils.structured_array.StructuredArrayFile(fpath, 'rb')
			result = f.read(count = chunk_size)
			
			
			
			while result.size > 0:
				chunk_number += 1
				print(f'{result.size=}')
				
				
				
				if True or progress_lgr.is_ready():
					total_bytes_read = f.tell()
					delta_bytes_read = total_bytes_read - last_total_bytes_read
					
					dt_split = dt.datetime.now()
					dt_elapsed_delta = dt_split - dt_start
					dt_elapsed_str = f'{dt_elapsed_delta.days}D {dt_elapsed_delta.seconds//3600}H {(dt_elapsed_delta.seconds %3600)//60}M {dt_elapsed_delta.seconds%60}s'
					dt_elapsed_sec = dt_elapsed_delta.total_seconds()
					
					dt_rolling_sec = (dt_split - dt_last_split).total_seconds()
					
					total_bytes_per_sec = total_bytes_read / dt_elapsed_sec
					rolling_bytes_per_sec = delta_bytes_read / dt_rolling_sec
					
					byte_amounts_and_unit = ((1,'kb'), (1000,'kb'), (1_000_000, 'Mb'), (1_000_000_000, 'Gb'))
					
					byte_unit_info = [byte_amounts_and_unit[0],byte_amounts_and_unit[0],byte_amounts_and_unit[0]]
					for byte_amount, byte_unit in byte_amounts_and_unit:
						if total_bytes_per_sec > byte_amount:
							byte_unit_info[0] = (byte_amount, byte_unit)
						if rolling_bytes_per_sec > byte_amount:
							byte_unit_info[1] = (byte_amount, byte_unit)
						if total_bytes_read > byte_amount:
							byte_unit_info[2] = (byte_amount, byte_unit)
						
					if progress_lgr.level == logging.INFO:
						print(f'chunk_number : {chunk_number}')
						print(f'Elapsed Time: {dt_elapsed_str}')
						print(f'Total bytes per second: {total_bytes_per_sec/byte_unit_info[0][0]:8.3f} {byte_unit_info[0][1]}/s')
						print(f'Rolling bytes per second: {rolling_bytes_per_sec/byte_unit_info[1][0]:8.3f} {byte_unit_info[1][1]}/s')
						print(f'Total bytes {total_bytes_read/byte_unit_info[2][0]:8.3f} {byte_unit_info[2][1]}')
					
					dt_last_split = dt_split
					last_total_bytes_read = total_bytes_read
				
				
				
				yield result
				result = f.read(count = chunk_size)
		elif ftype in ('.npy',):
			array = np.load(fpath)
			
			i = 0
			n = chunk_size
			while n < array.size:
				yield array[i:n]
				i+= chunk_size
				n += chunk_size
		else:
			raise RuntimeError(f'Unknown format to read "{ftype}"')


			
	
	
	
	







