import sys
from pathlib import Path

import numpy as np

assert len(sys.argv) == 2, "Require a single positional argument"

fpath = Path(sys.argv[1])


BIN32_HEADER_3_COLS = b"STRUCTURED{;upper_id;0;TYPE{;<u4;};lower_id;4;TYPE{;<u4;};einstein_A;8;TYPE{;<f4;};}"
BIN32_HEADER_4_COLS = b"STRUCTURED{;upper_id;0;TYPE{;<u4;};lower_id;4;TYPE{;<u4;};einstein_A;8;TYPE{;<f4;};wavenumber;8;TYPE{;<f4;};}"

TRANS_STR_FLOAT32_FACTOR=1E-20

dtype_3col = np.dtype([('upper_id','<u4'), ('lower_id', '<u4'), ('einstein_A', '<f4')])
format_3col = '{} {} {:.3e}'
dtype_4col = np.dtype([('upper_id','<u4'), ('lower_id', '<u4'), ('einstein_A', '<f4'), ('wavenumber', '<f4')])
format_4col = '{} {} {:.3e} {:.3e}'

def read_file_as_arr(fpath) -> np.ndarray:
	with open(fpath, 'rb') as f:
		# read 4 bytes at a time until last one is null
		i = 0
		h = f.read(4)
		i+= 1
		while h[-1] != 0:
			h += f.read(4)
			i += 4
		
		use_dtype = None
		if h.rstrip(b'\0') == BIN32_HEADER_3_COLS:
			use_dtype = dtype_3col
			formatter = format_3col
		elif h.rstrip(b'\0') == BIN32_HEADER_4_COLS:
			use_dtype = dtype_4col
			formatter = format_4col
		else:
			raise RuntimeError(f"File {fpath} does not have a recognized header, got {h}")
		
		result = np.fromfile(f, dtype=use_dtype) 
		result['einstein_A'] *= TRANS_STR_FLOAT32_FACTOR
		return result, formatter


a, formatter = read_file_as_arr(fpath)

for item in a:
	print(formatter.format(*item))
