
import io
from pathlib import Path
from typing import Protocol, Callable


class DecompressorProtocol(Protocol):
	def __init__(self):
		self.needs_input : bool = True
		self.eof : bool = False
		self.unused_data : bytes = b''
	
	def decompress(data : bytes, max_length : int = -1):
		...


class PassthroughDecompressor(DecompressorProtocol):
	def __init__(self):
		self.needs_input : bool = True
		self.eof : bool = False
		self.unused_data : bytes = b''
		
		self.n : int = 0
		self.q : int = 0
		self.data : bytes = b''
	
	def decompress(self, data : bytes, max_length : int = -1):
		m = len(data)
		if m == 0 and self.needs_input is False:
			p = self.q
			self.q = min(p+max_length, self.n) if max_length >=0 else self.n
			self.needs_input = self.q >= self.n
			return self.data[p:self.q]
		
		self.n = m
		self.p = 0
		self.data = data
		p = 0
		self.q = min(p+max_length, self.n) if max_length >=0 else self.n
		self.needs_input = self.p >= self.n
		return self.data[p:self.q]
		

class BinaryReader:
	def __init__(
			self, 
			decompressor : DecompressorProtocol = None,
	):
		self.decompressor = decompressor
		self.binary_source = None # source of binary data.
		self.binary_source_read_into_method = None # Method to call on `self.binary_source`. Should have a signature like `readinto1(b : bytearray) -> None | int` method
		
		self.binary_source_requires_close = False
		
		#self.set_chunk_size(10*1024*1024)
		self.set_chunk_size(128)
		
		self._byte_gen = None
		self._n_bytes_output = 0
	
	def __del__(self):
		if self.binary_source_requires_close:
			self.binary_source.close()
	
	def set_source(self, x, reader_callable : None | Callable[[bytearray],None|int] = None):
		if isinstance(x, Path):
			x = open(x, 'rb')
			self.binary_source_requires_close = True
		
		self.binary_source = x
		if reader_callable is not None:
			self.binary_source_read_into_method = reader_callable
		else:
			if isinstance(x, io.RawIOBase):
				self.binary_source_read_into_method = self.binary_source.readinto
			elif isinstance(x, io.BufferedIOBase):
				self.binary_source_read_into_method = self.binary_source.readinto1
			else:
				raise RuntimeError(f'Could not work out reader for binary source {x}')
	
	def set_chunk_size(self, x : int):
		self.chunk_size = x
		
		self.n = -1 # last number of bytes read from `self.binary_source`
		
		self.b = bytearray(b'\0'*self.chunk_size)
		self.s = memoryview(self.b)
		
		self.i = 0 # position of read head in `self.r`
		self.m = 0 # Number of bytes ready in residual
		self.residual_size = self.chunk_size
		
		self.a = bytearray(b'\0'*self.residual_size) # this may need to resize
	
	def flush(self):
		pass
	
	def fileno(self):
		return self.binary_source.fileno()
	
	def tell(self):
		return self._n_bytes_output
	
	def at_eof(self):
		return self.n == 0
	
	def seek(self, pos, whence):
		raise OSError('Cannot seek on BinaryReader') 
	
	def iter_bytes_plain(self) -> tuple[int,bytes]:
		self.n = self.binary_source_read_into_method(self.s)
		while self.n > 0:
			self._n_bytes_output += self.n
			yield self.n, self.b[:self.n]
			self.n = self.binary_source_read_into_method(self.s)
			
		yield 0, b''
	
	def iter_bytes_compressed(self) -> tuple[int,bytes]:
		self.n = self.binary_source_read_into_method(self.s)
		
		while self.n > 0:
			#print(f'{self.n=}')
			#print(f'COMPRESSED: {self.b[:self.n]=}')
			#print(f'{self.chunk_size=}')
			nx = 0
			while self.decompressor.needs_input and nx==0:
				x = self.decompressor.decompress(self.b[:self.n], self.chunk_size)
				nx = len(x)
				#print(f'DECOMPRESSED: {x=}')
				self.n = self.binary_source_read_into_method(self.s)
			
					
			
			self._n_bytes_output += nx
			#print(f'{nx=} {self._n_bytes_output=}')
			
			#print('#########', flush=True)
			yield nx, x
			#print('-----------', flush=True)
			#print(f'XX: {self.b[:self.n]=}')
			
			while not self.decompressor.needs_input:
				x = self.decompressor.decompress(b'', self.chunk_size)
				nx = len(x)
				self._n_bytes_output += nx
				yield nx, x
			
			#print('============', flush=True)
	
	def iter_bytes(self) -> tuple[int,bytes]:
		#print('iter_bytes()', flush=True)
		if self.decompressor is None:
			yield from self.iter_bytes_plain()
		else:
			yield from self.iter_bytes_compressed()
			
	
	def grow_residual_to(self, n):
		if n < self.residual_size:
			return
		old = self.a
		while self.residual_size < n:
			self.residual_size *= 2
		self.a = bytearray(self.residual_size)
		self.a[:self.m] = old
		
	
	def append_to_residual(self, x : bytes):
		n = self.m + len(x)
		self.grow_residual_to(n)
		
		#print(f'{self.m=} {n=}')
		#print(f'{self.a[:n]=}')
		#print(f'{x=}')
		self.a[self.m:n] = x
		self.m = n
		#print(f'AFTER: {self.a[:n]=}')
	
	def set_residual(self, x : bytes):
		n = len(x)
		self.grow_residual_to(n)
		self.a[:n] = x
		self.m = n
	
	def read(self, max_length : int = -1) -> tuple[int, bytes]:
		#print(f'read() {self._byte_gen=} {max_length=}', flush=True)
		if self._byte_gen is None:
			self._byte_gen = self.iter_bytes()
		
		n = 1
		if max_length < 0: 
			# read until end
			while n > 0:
				n, x = next(self._byte_gen)
				self.append_to_residual(x)
		else:
			# read until specified number of bytes
			while (n > 0) and (self.m < max_length):
				n, x = next(self._byte_gen)
				self.append_to_residual(x)
				#print(f'LOOP: {n=} {self.m=}')
		
		n = self.m if max_length < 0 else min(self.m, max_length)
		#print(f'{n=}')
		result = bytes(self.a[:n])
		
		d = self.m - n
		self.a[:d] = self.a[n:self.m]
		self.m = d
		#print(f'{self.m=}')
		
		#print(f'{result=}')
		return result
	
	def iter_lines(self, line_max_size : int = -1) -> tuple[int, bytes]:
		#print(f'iter_lines() {self._byte_gen=}', flush=True)
		if self._byte_gen is None:
			self._byte_gen = self.iter_bytes()
		
		n = 1
		while n > 0:
			
			n, x = next(self._byte_gen)
			#print(f'iter_lines(): {n=} {len(x)=}')
			#print(f'{x=}')
			#print(f'A1 {self.m=}')
			self.append_to_residual(x)
			#print(f'A2 {self.m=}')
			#print(f'{self.a=}')
			lines = self.a[:self.m].split(b'\n')
			
			#print(f'{[len(line) for line in lines]=}')
			#print(f'{lines=}')
			
			if len(lines) > 1:
				yield from ((len(y), y) for y in lines[:-1])
			self.set_residual(lines[-1])
			#print(f'{last_line_len=} {self.m=}')
			#print(f'{self.a=}')
			
			if (line_max_size >= 0) and (self.m > line_max_size):
				raise RuntimeError(f'Line too long, larger than {line_max_size=}')
		
		yield self.m, self.a[:self.m]
		self.m = 0
		
