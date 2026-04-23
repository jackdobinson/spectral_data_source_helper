
from typing import Literal
from pathlib import Path
import bz2

import numpy as np

import exomol_helper.utils.dtype

HDR_FIND_FIRST_BRACE_WITHIN = 32
HDR_MAX_SIZE = 1024 * 1024
BRACE_BYTE =  b'{'[0]




class StructuredArrayFile:
	
	def __init__(self, fpath, mode : None | Literal['wb', 'rb'] = None):
		self.fpath = fpath
		self.mode = None
		self.fhdl = None
		
		if mode is not None:
			self.open(mode)
	
	def __enter__(self):
		return self
	
	def __exit__(self, type, value, traceback):
		self.close()
	
	def __del__(self):
		self.close()
	
	def open(self, mode : Literal['wb', 'rb']):
		assert mode in ('wb', 'rb'), "`mode` must be one of ('wb', 'rb')"
		
		if self.fhdl is not None:
			assert self.mode == mode, "Cannot reopen file with a different mode before closing it"
			return self
		
		self.mode = mode
		
		if self.fpath.suffix == '.bz2':
			self.fhdl = bz2.open(self.fpath, self.mode)
		else:
			self.fhdl = open(self.fpath, self.mode)
		
		self.header_written = False
		self.arr_dtype = None
		
		return self
	
	def close(self):
		if self.fhdl is not None:
			self.fhdl.close()
	
	def write_header(self, arr : np.ndarray | np.dtype):
		if isinstance(arr, np.dtype):
			self.fhdl.write(exomol_helper.utils.dtype.to_string(arr).encode('ascii'))
		else:
			self.fhdl.write(exomol_helper.utils.dtype.to_string(arr.dtype).encode('ascii'))
		
		self.header_written = True
		
	def write(self, arr : np.ndarray):
		assert self.mode == 'wb', "Must have `mode` == 'wb' to write"
		
		if not self.header_written:
			self.write_header(arr)
		
		arr.tofile(self.fhdl)
	
	def read_dtype(self):
		hdr_part = b''
		
		found_first_brace = False
		while len(hdr_part) < HDR_FIND_FIRST_BRACE_WITHIN:
			hdr_part += self.fhdl.read(1)
			if hdr_part[-1] == BRACE_BYTE:
				found_first_brace = True
				break
		
		if not found_first_brace:
			raise RuntimeError(f'Could not find first "{{" within {HDR_FIND_FIRST_BRACE_WITHIN} bytes. Got "{hdr_part}"')
		
		# Probably an inefficient way of reading this but need to take it byte by byte
		while len(hdr_part) < HDR_MAX_SIZE and (hdr_part.count(b'{') !=hdr_part.count(b'}')) :
			hdr_part += self.fhdl.read(1)

		if (hdr_part.count(b'{') == hdr_part.count(b'}')):
			self.arr_dtype = exomol_helper.utils.dtype.from_string(hdr_part.decode('ascii'))
		else:
			raise RuntimeError(f'Could not read header. Got "{hdr_part}"')
	
	def read(self, count : int = -1):
		if self.arr_dtype is None:
			self.read_dtype()
		return np.fromfile(self.fhdl, dtype=self.arr_dtype, count=count)
	
	def tell(self):
		return self.fhdl.tell()
	
	
	


def tofile(fpath : Path, arr : np.ndarray):
	with StructuredArrayFile(fpath, 'wb') as f:
		f.write(arr)


def fromfile(fpath : Path):
	with StructuredArrayFile(fpath, 'rb') as f:
		return f.read()

