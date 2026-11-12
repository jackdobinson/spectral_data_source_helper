
from pathlib import Path

import numpy as np

BIN32_HEADER_3_COLS = b"STRUCTURED{;upper_id;0;TYPE{;<u4;};lower_id;4;TYPE{;<u4;};einstein_A;8;TYPE{;<f4;};}"
BIN32_HEADER_4_COLS = b"STRUCTURED{;upper_id;0;TYPE{;<u4;};lower_id;4;TYPE{;<u4;};einstein_A;8;TYPE{;<f4;};wavenumber;8;TYPE{;<f4;};}"

N_ROWS = 10_000

np.random.seed(12345)
script_dir = Path(__file__).parent
test_list_fpath = script_dir / "test_list.txt"
test_expected_result_fpath = script_dir / "test_expected_result.txt.bin32"


data = np.empty((N_ROWS,), dtype=[('upper_id','<u4'), ('lower_id', '<u4'), ('einstein_A', '<f4')])

data['upper_id'] = np.random.randint(0, 1000, size=N_ROWS, dtype=np.int32)
data['lower_id'] = np.random.randint(0, 1000, size=N_ROWS, dtype=np.int32)
data['einstein_A'][:N_ROWS//2] = 1E-20*np.exp(np.log(1-np.random.random_sample(size=N_ROWS//2))).astype(np.float32)
data['einstein_A'][N_ROWS//2:] = 1E-30*np.exp(np.log(1-np.random.random_sample(size=N_ROWS-N_ROWS//2))).astype(np.float32)

print(f'{script_dir=}')
print(f'{data=}')


with open(test_list_fpath, 'w') as f:
	for (a,b,c) in data:
		f.write(f'{a:4} {b:4} {c:.3e}\n')

bin_result = np.empty_like(data)
with open(test_list_fpath, 'r') as f:
	for i, aline in enumerate(f):
		a, b, c = aline.split()
		bin_result[i] = (np.uint32(a), np.uint32(b), 1E20*np.float32(c)) # Remember that the binary representation of `einstein_A` is multiplied by 1E20

print(f'{bin_result=}')

with open(test_expected_result_fpath, 'wb') as f:
	f.write(BIN32_HEADER_3_COLS)
	i = len(BIN32_HEADER_3_COLS)
	
	f.write(b'\0') # header must end with null byte on a 4 byte boundary
	i+=1
	while i % 4 != 0:
		print(f'{i=} {i%4=}')
		f.write(b'\0')
		i += 1
	
	f.write(bin_result.tobytes())

