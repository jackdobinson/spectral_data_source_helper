"""
Quantum number sets are scattered aroung EXOMOL. Therefore put them here as I encounter them and they will be saved to the cache
"""
import pickle

from exomol_helper.cfg.const import (
	EXOMOL_CACHE,
)

#from exomol_helper.cfg.log import pkg_logger as _lgr

QN_SET_FILE = EXOMOL_CACHE / "exomol.com/db/quantum_number_sets.pkl"
QN_SET_FILE_TEMP = EXOMOL_CACHE / "exomol.com/db/quantum_number_sets.pkl~"

qn_set : dict[str, tuple[str,...]] = dict()

def add(set_name : str, qn_names : tuple[str,...]):
	
	if set_name in qn_set:
		assert len(qn_set[set_name]) == len(qn_names), f'All definitions of Quantum Number set "{set_name}" must be equivalent.'
		assert all(x in qn_set[set_name] for x in qn_names), f'All definitions of Quantum Number set "{set_name}" must be equivalent.'
		assert all(x in qn_names for x in qn_set[set_name]), f'All definitions of Quantum Number set "{set_name}" must be equivalent.'
	else:
		qn_set[set_name] = qn_names
		save()

def save():
	QN_SET_FILE_TEMP.parent.mkdir(parents=True, exist_ok=True)
	try:
		with open(QN_SET_FILE_TEMP, 'wb') as f:
			pickle.dump(qn_set, f)
	except Exception as e:
		raise e
	else:
		QN_SET_FILE_TEMP.replace(QN_SET_FILE)

def load():
	global qn_set
	
	if QN_SET_FILE.exists():
		with open(QN_SET_FILE, 'rb') as f:
			qn_set = pickle.load(f)

load()

add('m0', tuple()) # m0 seems to be the same as 'a0' but used in air broadening files
add('a0', tuple())

