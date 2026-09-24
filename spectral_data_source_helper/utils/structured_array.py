
from typing import Literal, Self
from pathlib import Path

import numpy as np

import spectral_data_source_helper.utils.dtype

from .module_var import ModuleVar
from .binary_reader import BinaryReader

HDR_MAX_SIZE = 1024 * 1024
NULL_BYTE =  b'\0'[0]


module_progress_sink : ModuleVar = ModuleVar(
	lambda x: print(str(x), end='\r', flush=True)
	#lambda x: progress_lgr.info(str(x))
)



class StructuredArrayFile:
	class_writable_modes : tuple[str,...] = ('wb', 'rb+', 'ab')
	class_readable_modes : tuple[str,...] = ('rb', 'rb+')
	class_updateable_modes : tuple[str,...] = ('ab', 'rb+')
	
	def __init__(
			self, 
			fpath, mode : None | Literal['wb', 'rb', 'ab', 'rb+'] = None,
			reader : None | BinaryReader = None,
	):
		self.fpath = fpath
		self.reader = reader
		
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
	
	def open(self, mode : Literal['wb', 'rb', 'ab', 'rb+']) -> Self:
		
		assert mode in ('wb', 'rb', 'ab', 'rb+'), "`mode` must be one of ('wb', 'rb', 'ab', 'rb+')"
		
		if self.fhdl is not None:
			assert self.mode == mode, "Cannot reopen file with a different mode before closing it"
			return self
		
		self.mode = mode

		self.fhdl = open(self.fpath, self.mode)
		
		if self.mode in self.class_readable_modes:
			self.n_records_read = 0
			if self.reader is not None:
				self.reader.set_source(self.fhdl)
		
		if self.mode in self.class_writable_modes:
			self.n_records_written = 0
		
		self.header_byte_end = 0
		self.header_written = False
		self.arr_dtype = None
		
		if self.mode in self.class_updateable_modes:
			if self.mode == 'rb+':
				self.arr_dtype = self.read_dtype()
				if self.arr_dtype is not None:
					self.header_written = True
			else:
				self.header_written = True # assume header is written
		
		return self
	
	def close(self):
		if self.fhdl is not None:
			self.fhdl.close()
		self.header_written = None
	
	def write_header(self, arr : np.ndarray | np.dtype, encoding : str = 'ascii'):
		if isinstance(arr, np.dtype):
			dtype_bytes = spectral_data_source_helper.utils.dtype.to_string(arr).encode(encoding)
		else:
			dtype_bytes = spectral_data_source_helper.utils.dtype.to_string(arr.dtype).encode(encoding)
		
		# align to 32 bit boundary, always end with atleast one null byte
		dtype_bytes += b'\0'*(4 - (len(dtype_bytes) % 4))
		
		
		self.header_byte_end = len(dtype_bytes)+1
		self.fhdl.write(dtype_bytes)
		self.header_written = True
		
	def write(self, arr : np.ndarray):
		assert self.mode in self.class_writable_modes, f"Must have `mode` in {self.class_writable_modes} to write"
		
		if not self.header_written:
			self.write_header(arr)
		
		arr.tofile(self.fhdl)
		self.n_records_written += arr.size
		
		return
	
	def read_bytes(self, n : int = -1):
		if self.reader is None:
			return self.fhdl.read(n if n >=0 else -1)
		else:
			return self.reader.read(n if n >=0 else -1)
	
	def read_header(self, encoding : str = 'ascii'):
		#print(f'reading dtype {self.fhdl.name=}', flush=True)
		# Read 4 bytes at a time until string ends with null character
		hdr_part = self.read_bytes(4)
		if len(hdr_part) == 0:
			self.header_byte_end = 0
			return None
		
		while hdr_part[-1] != NULL_BYTE and len(hdr_part) <= HDR_MAX_SIZE:
			hdr_part += self.read_bytes(4)
		
		if len(hdr_part) > HDR_MAX_SIZE:
			raise RuntimeError(f'Header exceeded maximum size ({HDR_MAX_SIZE} bytes). First 128 bytes: {hdr_part[:128]}')
		
		#print(f'{hdr_part=}')
		
		self.header_byte_end = len(hdr_part)+1
		return hdr_part.decode(encoding)
	
	def read_dtype(self, encoding : str = 'ascii'):
		hdr = self.read_header(encoding=encoding)
		return spectral_data_source_helper.utils.dtype.from_string(hdr) if hdr is not None else None
	
	def read(self, count : int = -1) -> np.ndarray:	
		if self.arr_dtype is None:
			self.arr_dtype = self.read_dtype()

		#print(f'{self.arr_dtype=}')

		result = np.frombuffer(
			self.read_bytes(count*self.arr_dtype.itemsize), 
			dtype=self.arr_dtype, 
			count=-1
		)

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

