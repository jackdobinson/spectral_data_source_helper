"""
Quantum number sets are scattered aroung EXOMOL. Therefore put them here as I encounter them and they will be saved to the cache
"""


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


import pickle

#import numpy as np
from spectral_data_source_helper.cfg.const import (
	PKG_CACHE,
)

import spectral_data_source_helper.cfg.log as logging
_lgr = logging.getLogger(__name__)
_lgr.setLevel(logging.INFO)


QN_SET_FILE = PKG_CACHE / "exomol.com/db/quantum_number_sets.pkl"
QN_SET_FILE_TEMP = PKG_CACHE / "exomol.com/db/quantum_number_sets.pkl~"


qn_set_store : dict[str, dict[str, dict[str, dict[str, dict[str, tuple[str,...]]]]]] = dict()

DEFAULT_KEY = 'DEFAULT'

def include_first_qn_in_qn_names(qn_set_name : str, qn_names : tuple[str,...]) -> tuple[str,...]:
	"""
		`qn_names` are the names of the quantum numbers that `qn_set_name` specifies. However, the *.def files
		always leave out the first quantum number 'J"' in most cases or '|m|' for any `qn_set_name` that starts with "m".
	"""
	
	if qn_set_name[0] == 'm':
		return ('|m|', *qn_names)
	else:
		return ('J"', *qn_names)
	

def register_set(
		quantum_case_label : str | None, # Set to `DEFAULT_KEY` to only set defaults for this value then return (if they are not already set)
		mol_formula : str | None, # Set to `DEFAULT_KEY` to only set defaults for this value then return (if they are not already set)
		iso_formula : str | None, # Set to `DEFAULT_KEY` to only set defaults for this value then return (if they are not already set)
		broad_gas_name : str | None, # Set to `DEFAULT_KEY` to only set defaults for this value then return (if they are not already set)
		qn_set_name : str, 
		qn_names : tuple[str,...]
):
	"""
		Registers the quantum number set with the `qn_set_manager` system.
		
		The `qn_set_name` -> `qn_names` relations are supposed to be defined completely within the
		*.def files. However sometimes the *.def files do not have entries for a broadening gas (e.g. "air"
		which was added later and the *.def files were not updated). Additionally, some *.def files are
		malformed and do not have some entries they are supposed to have.
		
		Therefore, instead of storing the codes an isotopologue uses when reading its *.def file, we must
		have fallback values for the cases where the *.def files are malformed. In these cases we must make
		some amount of assumption. I will make the assumption that the "closer" isotopologue A is to
		isopoologue B, the better the match between the codes for A and B.
		
		The "closeness" is in the order of `quantum_case_label` ,`mol_formula`, `iso_formula`, `broad_gas_name`.
		
		That means we must have fallbacks at each level of specificity so we can use the closest one. However,
		I cannot populate these by hand (as it would take ages) so I will populate them on a "first come first serve"
		basis. If a code is not found for a specific isotopologue + broadening gas, we should walk up the levels
		until we find a matching code. If no matching code is ever found, throw and error.
		
		# ARGUMENTS #
			
			quantum_case_label : str
				A label from [the exomol quantum number cases](https://www.exomol.com/data/quantum-cases/) that classifies
				the physical geometry and coupling schemes of a the isotopologue we are registering the (code, quantum number set) pair for.
			
			mol_formula : str
				The molecular formula for the isotopologue we are registering the (code, quantum number set) pair for.
			
			iso_formula : str
				The isotopologue formula we are registering the (code, quantum number set) pair for.
			
			broad_gas_name : str
				The broadening gas we are registering the (code, quantum number set) pair for.
			
			qn_set_name : str
				The name of the quantum number set (`code`) that we are registering.
			
			qn_names : tuple[str,...]
				The names of the quantum numbers in the set we are registering.
	"""
	_lgr.debug(f'{quantum_case_label=} {mol_formula=} {iso_formula=} {broad_gas_name=} {qn_set_name=} {qn_names=}')
	
	qn_names = include_first_qn_in_qn_names(qn_set_name, qn_names)
	
	level_values = (quantum_case_label, mol_formula, iso_formula, broad_gas_name)
	d = qn_set_store
	
	for level_value in level_values:
		d.setdefault(DEFAULT_KEY, dict()).setdefault(qn_set_name, qn_names)
		
		if level_value is DEFAULT_KEY: # Do not bother decending if a level_value is `DEFAULT_KEY`, we have set the default (if it required setting) so just return.
			return
			
		d = d.setdefault(level_value, dict())
	
	d[qn_set_name] = qn_names
	
	save()
	

def get_sets_for_broad_gas_name(
		quantum_case_label : str, 
		mol_formula : str, 
		iso_formula : str, 
		broad_gas_name : str, 
) -> tuple[str,...]:
	
	
	level_values = (quantum_case_label, mol_formula, iso_formula, broad_gas_name)
	_lgr.debug(f'{level_values=}')
	
	default_stack = [qn_set_store[DEFAULT_KEY], None, None, None, None]
	d_stack = [qn_set_store, None, None, None, None]
	d = d_stack[0]
	
	i = 0
	for level_value in level_values:
		d = d_stack[i].get(level_value, None)
		
		_lgr.debug(f'{i=} {level_value=} {d=}')
		if d is not None:
			default_stack[i+1] = dict(default_stack[i])
			default_stack[i+1].update(d.get(DEFAULT_KEY, {}))
			d_stack[i+1] = d
			i += 1
		else:
			# rewind stack until we find a match
			while (i >= 0) and (d is None):
				
				d = default_stack[i]
				_lgr.debug(f'REWIND: {i=} {d=}')
				i -= 1
			break

	if d is None:
		# There are not entries or defaults for us to get so throw an error
		raise RuntimeError(f'Could not find quantum number sets for specifiers {level_values}')
	
	return d


def get_set(
		quantum_case_label : str, 
		mol_formula : str, 
		iso_formula : str, 
		broad_gas_name : str, 
		qn_set_name : str, 
) -> tuple[str,...]:
	
	d = get_sets_for_broad_gas_name(quantum_case_label, mol_formula, iso_formula, broad_gas_name)
	result = d.get(qn_set_name)
	_lgr.debug(f'{result=}')
	
	if result is None:
		raise RuntimeError(f'Could not find a quantum number set with {qn_set_name=} for specifiers {(quantum_case_label, mol_formula, iso_formula, broad_gas_name)}')
	
	return result


def update_leaf_dict(
		leaf_dict : dict[str, tuple[str,...]], 
		new_dict : dict[str, tuple[str,...]], 
		specifiers : tuple[str,...] = tuple()
):
	"""
		Given `leaf_dict` and `new_dict` update `leaf_dict` with members of `new_dict`. 
		Raise an error if any shared keys in `leaf_dict` and `new_dict` do not share the same value.
	"""
	for qn_set_name, qn_names in new_dict.items():
		z = leaf_dict.get(qn_set_name, None)
		
		if z is None: # If `qn_set_name` was not in the dictionary to be updated, then just set the new value
			leaf_dict[qn_set_name] = qn_names
		
		elif len(z) != len(qn_names) or any(a!=b for a,b in zip(z,qn_names)): # Otherwise, check that the new and old values agree
			raise RuntimeError(f'When updating quantum number sets, have inconsistent defaults for {qn_set_name=} with {specifiers=}. Expected {qn_names=} but {z} found.')

def update_sets(
		new_qn_set_dict : dict[str, dict[str, dict[str, dict[str, dict[str, tuple[str,...]]]]]]
):
	"""
		Update `qn_set_store` with the values in `new_qn_set_dict`, however if they both have entries they must agree. Throw an error if both dictionaries have entries that disagree.
	"""	
	x = [qn_set_store, None, None, None, None]
	
	for qcl, qcl_dict in new_qn_set_dict.items():
		x[1] = x[0].setdefault(qcl, dict())
		
		if qcl == DEFAULT_KEY:
			update_leaf_dict(x[1], qcl_dict)
			continue
			
		for mol, mol_dict in qcl_dict.items():
			x[2] = x[1].setdefault(mol, dict())
			
			if mol == DEFAULT_KEY:
				update_leaf_dict(x[2], mol_dict)
				continue
			
			for iso, iso_dict in mol_dict.items():
				x[3] = x[2].setdefault(iso, dict())
				
				if iso == DEFAULT_KEY:
					update_leaf_dict(x[3], iso_dict)
					continue
				
				for bgn, bgn_dict in iso_dict.items():
					x[4] = x[3].setdefault(bgn, dict())
					
					if bgn == DEFAULT_KEY:
						update_leaf_dict(x[4], bgn_dict)
						continue
					
					update_leaf_dict(x[4], bgn_dict)
	return

def save():
	QN_SET_FILE_TEMP.parent.mkdir(parents=True, exist_ok=True)
	try:
		with open(QN_SET_FILE_TEMP, 'wb') as f:
			pickle.dump(
				(qn_set_store,),
				f
			)
	except Exception as e:
		raise e
	else:
		QN_SET_FILE_TEMP.replace(QN_SET_FILE)

def load():
	
	if QN_SET_FILE.exists():
		with open(QN_SET_FILE, 'rb') as f:
			qn_set_store_temp, = pickle.load(f)
		
		_lgr.debug(f'{qn_set_store_temp=}')
		
		update_sets(qn_set_store_temp)


_register_default_target = (DEFAULT_KEY, DEFAULT_KEY, DEFAULT_KEY, DEFAULT_KEY)
register_set(*_register_default_target, 'a0', tuple()) # J"
register_set(*_register_default_target, 'a1', ('K"',)) # J", K"
register_set(*_register_default_target, 'a5', ("J'", 'Ka"', 'Kc"', "Ka'", "Kc'")) # J", J', Ka", Kc", Ka', Kc' 
register_set(*_register_default_target, 'm0', tuple()) # |m|
register_set(*_register_default_target, 'm1', ('K"',)) # |m|, K"'

_lgr.debug(f'{qn_set_store=}')

load()



