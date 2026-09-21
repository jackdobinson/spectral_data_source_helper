


import textwrap

power_10_zero_index = 80 # index of 10^{0}
powers = tuple(range(-80,81)) # power of 10
values = []
exp_2 = []

power_of_two_to_pull_out = 2

for p in powers:
	x = (5/(2**power_of_two_to_pull_out))**p
	y = (1+power_of_two_to_pull_out)*p
	
	while x > 2E9:
		x /= 2
		y += 1
	while x < 1E9:
		x *= 2
		y -= 1
	values.append(x)
	exp_2.append(y)



first = True


usage = textwrap.dedent("""
	/*
		10^{n} = 2^{n} * 5^{n}
				= 2^{3n} * (1+1/4)^{n}
							^^^^^^^^^^^
							`factor` we must multiply by
		
		Therefore 10^n -> factor * 2^{3n}
		
		Want to shift factor so that we have integer factors to multiply by,
		therefore want to ensure all values are between 1E9 and 2E9, shift by
		powers of two until that is true.
	*/
""")

struct_def = textwrap.dedent("""
	typedef struct PowerOfTwoFactorEntry {
		int16_t exp_10;
		uint32_t factor;
		int16_t exp_2;
	} PowerOfTwoFactorEntry;
""")

with open('power_of_two_factor_lut.h', 'w') as f:

	
	
	print(usage, file=f)
	
	print(f'#define POWER_OF_TWO_FACTOR_LUT_ZERO_INDEX ({power_10_zero_index})\n', file=f)
	
	print(struct_def, file=f)
	
	print(f'const PowerOfTwoFactorEntry power_of_two_factor_lut[{len(powers)}] = {{', file=f)
	for p, v, e in zip(powers, values, exp_2):
		if first:
			print(f'\t{{{p}, {v:.0f}, {e}}}', end='', file=f)
			first = False
		else:
			print(f',\n\t{{{p}, {v:.0f}, {e}}}', end='', file=f)
	print('\n};', file=f)