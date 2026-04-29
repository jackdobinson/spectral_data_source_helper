
from typing import Literal, Self
from pathlib import Path
import bz2

import numpy as np

import exomol_helper.utils.dtype

from .module_var import ModuleVar

HDR_FIND_FIRST_BRACE_WITHIN = 32
HDR_MAX_SIZE = 1024 * 1024
BRACE_BYTE =  b'{'[0]


module_progress_sink : ModuleVar = ModuleVar(
	lambda x: print(str(x), end='\r', flush=True)
	#lambda x: progress_lgr.info(str(x))
)



class StructuredArrayFile:
	class_writable_modes : tuple[str,...] = ('wb', 'rb+', 'ab')
	class_readable_modes : tuple[str,...] = ('rb', 'rb+')
	
	def __init__(
			self, 
			fpath, mode : None | Literal['wb', 'rb'] = None,
			
	):
		self.fpath = fpath
		self.mode = None
		self.fhdl = None
		self.header_written = None
		self.n_records_read = 0
		self.n_records_written = 0
		
		if mode is not None:
			self.open(mode)
	
	def __enter__(self) -> Self:
		return self
	
	def __exit__(self, type, value, traceback):
		self.close()
	
	def __del__(self):
		self.close()
	
	def open(self, mode : Literal['wb', 'rb']) -> Self:
		assert mode in ('wb', 'rb'), "`mode` must be one of ('wb', 'rb')"
		
		if self.fhdl is not None:
			assert self.mode == mode, "Cannot reopen file with a different mode before closing it"
			return self
		
		self.mode = mode
		
		if self.mode in self.class_readable_modes:
			self.n_records_read = 0
		
		if self.mode in self.class_writable_modes:
			self.n_records_written = 0
		
		if self.fpath.suffix == '.bz2':
			self.fhdl = bz2.open(self.fpath, self.mode)
		else:
			self.fhdl = open(self.fpath, self.mode)
		
		self.header_byte_end = 0
		self.header_written = False
		self.arr_dtype = None
		
		return self
	
	def close(self):
		if self.fhdl is not None:
			self.fhdl.close()
		self.header_written = None
	
	def write_header(self, arr : np.ndarray | np.dtype, encoding : str = 'ascii'):
		if isinstance(arr, np.dtype):
			self.fhdl.write(exomol_helper.utils.dtype.to_string(arr).encode(encoding))
		else:
			self.fhdl.write(exomol_helper.utils.dtype.to_string(arr.dtype).encode(encoding))
		
		self.header_written = True
		self.header_byte_end = self.tell()
		
	def write(self, arr : np.ndarray):
		assert self.mode in self.class_writable_modes, f"Must have `mode` in {self.class_writable_modes} to write"
		
		if not self.header_written:
			self.write_header(arr)
		
		arr.tofile(self.fhdl)
		self.n_records_written += arr.size
		
		return
	
	
	def read_header(self, encoding : str = 'ascii'):
		#print('reading dtype', flush=True)
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
			return hdr_part.decode(encoding)
		else:
			raise RuntimeError(f'Could not read header. Got "{hdr_part}"')
	
	
	def read(self, count : int = -1) -> np.ndarray:	
		if self.arr_dtype is None:
			self.arr_dtype = exomol_helper.utils.dtype.from_string(self.read_header())
		
		result = np.fromfile(self.fhdl, dtype=self.arr_dtype, count=count)
		self.n_records_read += result.size
		
		return result
	
	def tell(self) -> int:
		return self.fhdl.tell()
	
	def seek(self, offset : int, whence : int):
		result = self.fhdl.seek(offset, whence)
		
		if self.header_written:
			if self.tell() < self.header_byte_end:
				self.header_written = False
				self.header_byte_end = 0
				self.seek(0,0)
		
		return result
	
	
	
	
	


def tofile(fpath : Path, arr : np.ndarray):
	with StructuredArrayFile(fpath, 'wb') as f:
		f.write(arr)


def fromfile(fpath : Path):
	with StructuredArrayFile(fpath, 'rb') as f:
		return f.read()

