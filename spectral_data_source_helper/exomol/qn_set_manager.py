"""
Quantum number sets are scattered aroung EXOMOL. Therefore put them here as I encounter them and they will be saved to the cache
"""
import pickle

import numpy as np
from spectral_data_source_helper.cfg.const import (
	PKG_CACHE,
)

#from spectral_data_source_helper.cfg.log import pkg_logger as _lgr
ID_TYPE = np.iinfo(np.int64)

MAX_QN_IN_SET = 16

QN_SET_FILE = PKG_CACHE / "exomol.com/db/quantum_number_sets.pkl"
QN_SET_FILE_TEMP = PKG_CACHE / "exomol.com/db/quantum_number_sets.pkl~"

qn_set : dict[str, tuple[str,...]] = dict()

qn_id_map : dict[str,int] = dict() # mapping between quantum number name and ID
qn_set_id_map : dict[str,int] = dict() # mapping between quantum number set name and ID

n_qn_set_ids = 0
qn_set_ids = np.full((8,2), fill_value=ID_TYPE.max, dtype=ID_TYPE.dtype)

qn_set_id_array = np.zeros((8,MAX_QN_IN_SET), dtype=ID_TYPE.dtype)
qn_set_n_id_array = np.zeros((8,), dtype=int)

def get_qn_set_id(qn_set_name : str):
	assert len(qn_set_name) == 2, "Ensure we have 2 characters in the code"
	
	qn_code_ascii = qn_set_name.encode('ascii')
	
	ascii_numeral_start = 48 # '0'
	ascii_numeral_end = 58 # '9' + 1
	ascii_lowercase_start = 97 # 'a'
	ascii_lowercase_end = 123 # 'z' + 1
	
	assert ascii_lowercase_start <= qn_code_ascii[0] and  qn_code_ascii[0] < ascii_lowercase_end, f"First character must be a lowercase letter: {qn_code_ascii}"
	assert ascii_numeral_start <= qn_code_ascii[1] and  qn_code_ascii[1] < ascii_numeral_end, f"Second character must be a numeral: {qn_code_ascii}"
	
	id = qn_set_id_map.get(qn_set_name,None)
	if id is not None:
		return id
	
	
	id_parts = (
		qn_code_ascii[0] - ascii_lowercase_start,
		qn_code_ascii[1] - ascii_numeral_start
	)
	
	power_2 = (
		int(np.ceil(np.log2(ascii_lowercase_end - ascii_lowercase_start))),
		int(np.ceil(np.log2(ascii_numeral_end - ascii_numeral_start))),
	)
	
	id = 0
	n = 0
	for x, y in zip(id_parts, power_2):
		id += x*(2**n)
		n += y
	
	assert n <= ID_TYPE.bits, "id must not take up more than 64 bits"
	
	return id


def get_qn_id(qn_name : str):
	qn_name_ascii = qn_name.encode('ascii')
	
	ascii_double_quote = 34 # '"'
	ascii_single_quote = 39 # '\''
	ascii_numeral_start = 48 # '0'
	ascii_numeral_end = 58 # '9' + 1
	ascii_uppercase_start = 65 # 'A'
	ascii_uppercase_end = 90 # 'Z' + 1
	ascii_lowercase_start = 97 # 'a'
	ascii_lowercase_end = 123 # 'z' + 1
	
	qn_name_ascii_len = len(qn_name_ascii)
	
	assert qn_name_ascii[-1] in (ascii_double_quote, ascii_single_quote), f"Last character must be a single or double quote: {qn_name_ascii}"
	for i in range(qn_name_ascii_len-1):
		assert (
			(ascii_numeral_start <= qn_name_ascii[i] and  qn_name_ascii[i] < ascii_numeral_end)
			or (ascii_uppercase_start <= qn_name_ascii[i] and  qn_name_ascii[i] < ascii_uppercase_end)
			or (ascii_lowercase_start <= qn_name_ascii[i] and  qn_name_ascii[i] < ascii_lowercase_end)
		), f"All characters except the final one must be a numeral or lowercase letter: {qn_name_ascii}"
	
	id = qn_id_map.get(qn_name,None)
	if id is not None:
		return id
	
	ascii_numeral_n = (ascii_numeral_end - ascii_numeral_start) 
	ascii_uppercase_n = (ascii_uppercase_end - ascii_uppercase_start)
	ascii_lowercase_n = (ascii_lowercase_end - ascii_lowercase_start)
	
	ascii_part_n_states = (
		ascii_numeral_n
		+ ascii_uppercase_n
		+ ascii_lowercase_n
	)
	
	id_parts = (
		0 if qn_name_ascii[-1] == ascii_double_quote else 1,
		*(
			(x - ascii_numeral_start) if (x < ascii_numeral_end) else ((ascii_numeral_n+(x - ascii_uppercase_start) if (x < ascii_uppercase_end) else ((ascii_numeral_n+ascii_uppercase_n)+(x-ascii_lowercase_start)))) for x in qn_name_ascii[:-1]
		)
	)
	
	power_2 = (
		1,
		*([int(np.ceil(np.log2(ascii_part_n_states)))] * (qn_name_ascii_len-1))
	)
	
	id = 0
	n = 0
	for x, y in zip(id_parts, power_2):
		id += x*(2**n)
		n += y
	
	assert n <= ID_TYPE.bits, "id must not take up more than 64 bits"
	
	return id
	

def get_qn_set_ids(qn_set_id : int) -> tuple[int,np.ndarray]:
	i = np.searchsorted(qn_set_ids[:,0], qn_set_id)
	if qn_set_ids[i,0] != qn_set_id:
		raise RuntimeError(f'{qn_set_id=} not found in {qn_set_ids=}')
	
	j = qn_set_ids[i,1]
	
	return qn_set_n_id_array[j], qn_set_id_array[j]


def add(set_name : str, qn_names : tuple[str,...]):

	if len(qn_names) > MAX_QN_IN_SET:
		raise RuntimeError(f'Number of quantum numbers in set {set_name} exceeded maximum ({len(qn_names)} > {MAX_QN_IN_SET}). Update MAX_QN_IN_SET in {__file__}')
	
	if set_name in qn_set:
		assert len(qn_set[set_name]) == len(qn_names), f'All definitions of Quantum Number set "{set_name}" must be equivalent.'
		assert all(x in qn_set[set_name] for x in qn_names), f'All definitions of Quantum Number set "{set_name}" must be equivalent.'
		assert all(x in qn_names for x in qn_set[set_name]), f'All definitions of Quantum Number set "{set_name}" must be equivalent.'
	else:
		qn_set[set_name] = qn_names
		qn_set_id_map[set_name] = get_qn_set_id(set_name)
		for qn_name in qn_names:
			qn_id_map[qn_name] = get_qn_id(qn_name)
		
		update_set_ids()
		save()

def update_set_ids():
	global qn_set_ids, n_qn_set_ids, qn_set_id_array, qn_set_n_id_array
	
	m_qn_set_ids = len(qn_set_id_map)
	if m_qn_set_ids > n_qn_set_ids:
		if m_qn_set_ids > qn_set_ids.shape[0]:
			new_qn_set_ids = np.zeros((2*qn_set_ids.shape[0], *qn_set_ids.shape[1:]), dtype=ID_TYPE.dtype)
			new_qn_set_ids[:n_qn_set_ids] = qn_set_ids
			
			new_qn_set_id_array = np.zeros((2*qn_set_id_array.shape[0], *qn_set_id_array.shape[1:]), dtype=ID_TYPE.dtype)
			new_qn_set_id_array[:n_qn_set_ids] = qn_set_id_array
			
			new_qn_set_n_id_array = np.zeros((2*qn_set_n_id_array.shape[0],), dtype=int)
			new_qn_set_n_id_array[:n_qn_set_ids] = qn_set_n_id_array
			
			qn_set_ids = new_qn_set_ids
			qn_set_id_array = new_qn_set_id_array
			qn_set_n_id_array = new_qn_set_n_id_array
	
		for qn_set_name, qn_set_id in qn_set_id_map.items():
			if qn_set_id not in qn_set_ids[:,0]:
				qn_set_ids[n_qn_set_ids] = (qn_set_id, n_qn_set_ids)
				
				qn_set_n_id_array[n_qn_set_ids] = len(qn_set[qn_set_name])
				qn_set_id_array[n_qn_set_ids, :qn_set_n_id_array[n_qn_set_ids]] = sorted(get_qn_id(x) for x in qn_set[qn_set_name])
				
				n_qn_set_ids += 1
	
		qn_set_ids.sort(axis=0)

def save():
	QN_SET_FILE_TEMP.parent.mkdir(parents=True, exist_ok=True)
	try:
		with open(QN_SET_FILE_TEMP, 'wb') as f:
			pickle.dump(
				(qn_set, qn_set_id_map, qn_id_map), 
				f
			)
	except Exception as e:
		raise e
	else:
		QN_SET_FILE_TEMP.replace(QN_SET_FILE)

def load():
	global qn_set, qn_set_id_map, qn_id_map
	
	if QN_SET_FILE.exists():
		with open(QN_SET_FILE, 'rb') as f:
			qn_set, qn_set_id_map, qn_id_map = pickle.load(f)
			update_set_ids()

load()

# Codes are in the *.def files for specific molecules, and technically there are no "universal" codes. However
# See table 13 in [the 2024 release paper](https://www.researchgate.net/publication/380007184_The_2024_Release_of_the_Exomol_Database_Molecular_Line_Lists_for_Exoplanetand_Other_Hot_Atmospheres)
# and footnotes of table 16 of [this paper](https://arxiv.org/html/1603.05890v3#S5.SS6)
#
# The codes will change based upon what the *.def file contains. However, some
# *.def files are not complete they are missing the quantum number set codes.
# Therefore, we will assume a set of quantum numbers at this point.
#
# Technically, the exact quantum numbers represented are based upon a 
# VAMDC-aligned taxonomy system to classify a molecule's structural physics.
# So which quantum numbers are available, actually depends upon the *.def file
# as well. The [exomol quantum cases documentation](https://www.exomol.com/data/quantum-cases/)
# has some information on what quantum numbers are available, however it explicity
# states that the *.def files should contain the information in case they use
# non-standard quantum numbers.
#
# Therefore, each quantumn number set is actually specific to the *.def file, and
# any fallbacks should account for the quantum case of the molecule.
# 
# What I have done here is be very lazy and not done that at all. I have just 
# shoved all the cases into the same dictionary and hoped that they worked fine.
#
# Also, the "mX" quantumn number sets are fundamentally different than the 
# others. They use |m| in place of J" as the first quantum number entry of a 
# row in the *.broad files. This means that I need to add an extra piece of data
# to the transitions, a |m| value.
#
# m is defined as follows:
#   * m = -J" for P-branch transitions (lose exactly 1 angular momentum, J'=J"-1)
#   * m = J" for Q-branch transitions (no angular momentum gain, J'=J")
#   * m = J"+1 for R-branch transitions (gain exactly 1 anglular momentum, J'=J"+1)
#   * m is undefined in all other cases (probably implemented as set to NAN)
#
# This means I need to re-do how I handle the broadening parameters.
#
# TODO: Re-do how broadening lookup is handled to be consistent with the above

add('a0', tuple()) # J"
add('a1', tuple()) # J", K"
add('a5', tuple()) # J", J', Ka", Kc", Ka', Kc' 
add('m0', tuple()) # |m|
add('m1', tuple()) # |m|, K"'

"""
print(f'{qn_set=}')
print(f'{qn_set_id_map=}')
print(f'{qn_id_map=}')
print(f'{qn_set_ids=}')
print(f'{qn_set_id_array=}')
print(f'{qn_set_n_id_array=}')
"""



