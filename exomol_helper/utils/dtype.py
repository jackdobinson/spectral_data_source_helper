"""
Routines to help with numpy dtype objects
"""


import numpy as np
from typing import Iterable, Self


def is_structured(dtype):
	return dtype.names is not None # recommended way to check if a dtype is a structured dtype

def field_names(dtype):
	x = dtype.names
	if x is None:
		raise RuntimeError(f'{dtype=} is not a structured dtype and therefore has no field names')
	return x

def field_dtypes(dtype):
	x = dtype.fields
	if x is None:
		raise RuntimeError(f'{dtype} is not a structured dtype and therefore has no fields')
	return tuple(y[0] for y in x.values())

def field_offsets(dtype):
	x = dtype.fields
	if x is None:
		raise RuntimeError(f'{dtype} is not a structured dtype and therefore has no fields')
	return tuple(y[1] for y in x.values())

def field_types(dtype):
	return tuple(x.type for x in field_dtypes(dtype))

def structured_data_tuple_from(dtype, an_iterable : Iterable):
	#return tuple(t(x) for t,x in zip(field_types(dtype), an_iterable))
	return tuple(d.type(x) if not is_structured(d) else structured_data_tuple_from(d, x) for d,x in zip(field_dtypes(dtype), an_iterable))

def structured_data_from(dtype, an_iterable : Iterable):
	return np.void(structured_data_tuple_from(dtype, an_iterable), dtype=dtype)

def to_string(dtype):
	s = []
	if is_structured(dtype):
		s.append('STRUCTURED{')
		for field_name, (field_dtype, field_offset) in dtype.fields.items():
			s.append(f'{field_name}')
			s.append(f'{field_offset}')
			s.append(to_string(field_dtype))
		s.append('}')
	else:
		if (x := dtype.subdtype )is not None:
			s.append('ARRAY{')
			s.append(f'{x[1]}') # shape
			s.append(to_string(x[0])) # subdtype
			s.append('}')
		else:
			s.append(f'TYPE{{;{dtype.str};}}')
	return ';'.join(s)


class StringParser:
	def __init__(self):
		self.TOK_SEP = ';'
		self.TOK_EOF = 'END_OF_FILE'
		
		self.reset()
		
	
	def reset(self, s : str | None = None) -> Self:
		self.pos = 0
		self.end = len(s) if s is not None else None
		self.current_token = None
		self.exhausted = False
		return self
		
	def next_token(self, s):
		idx = s.find(self.TOK_SEP, self.pos, self.end)
		
		if idx > 0:
			self.current_token = s[self.pos:idx]
			self.pos = idx + len(self.TOK_SEP)
		else:
			if not self.exhausted:
				self.pos = len(s)
				self.current_token = '}'
				self.exhausted = True
			else:
				self.current_token = self.TOK_EOF
		
		return self.current_token
	
	def is_exhausted(self, s):
		return self.exhausted
	
	def parse_structured(self, s):
		fnames = []
		foffsets = []
		fdtypes = []
		
		while (tok := self.next_token(s)) != '}':
			#print(f'110 :: {tok}')
			fnames.append(tok)
			
			tok = self.next_token(s)
			#print(f'120 :: {tok}')
			foffsets.append(int(tok))
			
			fdtype = self.parse(s)
			fdtypes.append(fdtype)
		
		result = np.dtype({'names':fnames, 'formats' : fdtypes, 'offsets':foffsets})
		
		#print(f'130 :: {self.current_token}')
		assert self.current_token == '}', f'Expected token "}}", but got token "{tok}"'
		return result
	
	def parse_array(self, s):
		
		tok = self.next_token(s)
		#print(f'210 :: {tok}')
		shape = tuple(int(x.strip()) for x in tok[1:-1].split(','))
		
		fdtype = self.parse(s)
		
		result = np.dtype((fdtype,shape))
		
		tok = self.next_token(s)
		#print(f'220 :: {tok}')
		assert tok == '}', f'Expected token "}}", but got token "{tok}"'
		return result
	
	def parse_type(self, s):
		tok = self.next_token(s)
		#print(f'310 :: {tok}')
		result = np.dtype(tok)
		
		tok = self.next_token(s)
		#print(f'320 :: {tok}')
		assert tok == '}', f'Expected token "}}", but got token "{tok}"'
		return result
	
	def parse(self, s):
		tok = self.next_token(s)
		
		result = None
		
		if tok == 'STRUCTURED{':
			#print(f'100 :: {tok}')
			result = self.parse_structured(s)
		elif tok == 'ARRAY{':
			#print(f'200 :: {tok}')
			result = self.parse_array(s)
		elif tok == 'TYPE{':
			#print(f'300 :: {tok}')
			result = self.parse_type(s)
		elif tok == '}':
			raise RuntimeError('Unexpected end of section')
		elif tok == self.TOK_EOF:
			raise RuntimeError('Unexpected end of input')
		else:
			raise RuntimeError(f'Unknown Token "{tok}"')
		
		return result


_string_parser = StringParser()

def from_string(string : str) -> np.dtype:
	return _string_parser.reset().parse(string)


	
	