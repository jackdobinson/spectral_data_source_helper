import sys
from pathlib import Path

import numpy as np

assert len(sys.argv) == 3, "Require two positional arguments, the files to diff"

fpath_1 = Path(sys.argv[1])
fpath_2 = Path(sys.argv[2])


BIN32_HEADER_3_COLS = b"STRUCTURED{;upper_id;0;TYPE{;<u4;};lower_id;4;TYPE{;<u4;};einstein_A;8;TYPE{;<f4;};}"
BIN32_HEADER_4_COLS = b"STRUCTURED{;upper_id;0;TYPE{;<u4;};lower_id;4;TYPE{;<u4;};einstein_A;8;TYPE{;<f4;};wavenumber;8;TYPE{;<f4;};}"

dtype_3col = np.dtype([('upper_id','<u4'), ('lower_id', '<u4'), ('einstein_A', '<f4')])
dtype_4col = np.dtype([('upper_id','<u4'), ('lower_id', '<u4'), ('einstein_A', '<f4'), ('wavenumber', '<f4')])

atol = 1E-30
rtol = 1E-6

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
		elif h.rstrip(b'\0') == BIN32_HEADER_4_COLS:
			use_dtype = dtype_4col
		else:
			raise RuntimeError(f"File {fpath} does not have a recognized header, got {h}")
		
		return np.fromfile(f, dtype=use_dtype)


a = read_file_as_arr(fpath_1)
b = read_file_as_arr(fpath_2)


assert a.dtype == b.dtype, "Must have equal dtypes to be equal"

all_fields_close = True




for x in a.dtype.names:
	if not np.allclose(a[x],b[x], atol=atol, rtol=rtol):
		all_fields_close = False
		break


if not all_fields_close:
	for x in a.dtype.names:
		if np.allclose(a[x],b[x], atol=atol, rtol=rtol):
			continue
		r = a[x] - b[x]
		a_r = np.abs(r)
		print(f'inputs not equal within error ({atol=}, {rtol=})')
		print(f'    field={x}')
		print(f'        diff={r}')
		print(f'        max_abs_diff={r[np.nanargmax(a_r)]}')
		print(f'        max_rel_diff={r[np.nanargmax(a_r/np.abs(b[x]))]}')
else:
	print('inputs equal within error')
