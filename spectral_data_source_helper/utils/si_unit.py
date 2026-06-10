


from typing import Any

import numpy as np

SI_BINS = np.array([
	1E-12,
	1E-9,
	1E-6,
	1E-3,
	1,
	1E3,
	1E6,
	1E9,
	1E12,
	1E15,
	1E18,
])

SI_CHAR_PREFIX = ('f','p','n','u','m','','k','M','G','T','P','E','Z')
SI_SCALE = np.array([
	1E-15,
	1E-12,
	1E-9,
	1E-6,
	1E-3,
	1,
	1E3,
	1E6,
	1E9,
	1E12,
	1E15,
	1E18,
	1E21,
])
SI_SCALE_PREFIX = np.array([
	" x 1E-15",
	" x 1E-12",
	" x 1E-9",
	" x 1E-6",
	" x 1E-3",
	"",
	" x 1E3",
	" x 1E6",
	" x 1E9",
	" x 1E12",
	" x 1E15",
	" x 1E18",
	" x 1E21",
])
SI_SCALE_10_PREFIX = np.array([
	" x 10^{-15}",
	" x 10^{-12}",
	" x 10^{-9}",
	" x 10^{-6}",
	" x 10^{-3}",
	"",
	" x 10^{3}",
	" x 10^{6}",
	" x 10^{9}",
	" x 10^{12}",
	" x 10^{15}",
	" x 10^{18}",
	" x 10^{21}",
])



def to_si_prefix_unit(value : Any, unit : str) -> str:
	idx = np.searchsorted(SI_BINS, np.abs(value))
	si_scale = SI_SCALE[idx]
	si_prefix = SI_CHAR_PREFIX[idx]
	return f'{value/si_scale:5.2f} {si_prefix}{unit}'

def to_si_numeric_unit(value : Any, unit : str) -> str:
	idx = np.searchsorted(SI_BINS, np.abs(value))
	si_scale = SI_SCALE[idx]
	si_prefix = SI_SCALE_PREFIX[idx]
	return f'{value/si_scale:5.2f}{si_prefix} {unit}'
