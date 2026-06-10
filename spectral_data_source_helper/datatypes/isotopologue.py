


import re
from typing import NamedTuple, Self

from .atomic_isotope import AtomicIsotope
from .molecule import Molecule


plural_atomic_isotope_regex = re.compile(r'\((?P<nucleon_number>\d+)(?P<name>[A-Z][a-z]*)\)(?P<plurality>\d*)')
isotopologue_regex          = re.compile(r'(?P<isotopes>(' +plural_atomic_isotope_regex.pattern+ r')+)(?P<charge>[+-]\d*)?')

plural_atomic_isoslug_regex              = re.compile(r'(?P<nucleon_number>\d+)(?P<name>[A-Z][a-z]*)(?P<plurality>\d*)')
plural_atomic_isoslug_regex_no_grp_names = re.compile(r'(\d+)([A-Z][a-z]*)(\d*)')
isoslug_regex                            = re.compile(r'(?P<isotopes>(' +plural_atomic_isoslug_regex_no_grp_names.pattern+ r')(-' + plural_atomic_isoslug_regex_no_grp_names.pattern + r')*)(?P<charge>_[pm]\d*)?')

class Isotopologue(NamedTuple):
	isotopes : tuple[AtomicIsotope,...]
	charge : int
	
	@classmethod
	def regex_match(cls, formula) -> tuple[None | Self, str]:
		match = isotopologue_regex.match(formula)
		
		if match is not None:
			item_counts = tuple((AtomicIsotope(pm["name"], int(pm["nucleon_number"])), (int(pm["plurality"]) if len(pm["plurality"]) > 0 else 1)) for pm in plural_atomic_isotope_regex.finditer(match["isotopes"]))
			items = []
			for item, count in item_counts:
				while count > 0:
					items.append(item)
					count -= 1
			
			charge_str = match["charge"]
			if charge_str is None or len(charge_str) == 0:
				charge = 0
			elif len(charge_str) == 1:
				charge = int(charge_str+'1')
			else:
				charge = int(charge_str)
			return cls(tuple(items), charge), formula[match.end():]
		else:
			return None, formula
	
	@classmethod
	def isoslug_regex_match(cls, formula) -> tuple[None | Self, str]:
		match = isoslug_regex.match(formula)
		
		if match is not None:
			item_counts = tuple((AtomicIsotope(pm["name"], int(pm["nucleon_number"])), (int(pm["plurality"]) if len(pm["plurality"]) > 0 else 1)) for pm in plural_atomic_isoslug_regex.finditer(match["isotopes"]))
			items = []
			for item, count in item_counts:
				while count > 0:
					items.append(item)
					count -= 1
			
			charge_str = match["charge"]
			if charge_str is None or len(charge_str) == 0:
				charge = 0
			elif charge_str.startswith('_p'):
				charge = int(charge_str[2:]) if len(charge_str) > 2 else 1
			elif charge_str.startswith('_m'):
				charge = -int(charge_str[2:]) if len(charge_str) > 2 else -1
			else:
				raise ValueError(f'Invalid charge string {charge_str} in isotopologue slug')
			return cls(tuple(items), charge), formula[match.end():]
		else:
			return None, formula
	
	@classmethod
	def from_str(cls, formula : str, multiple=False) -> Self | tuple[Self,...]:
		# Example "(1H)2(16O)", "(16O)(17O)(16O)"
		
		instance, formula = cls.regex_match(formula)
		
		if instance is None:
			raise ValueError(f'{formula=} does not denote an Isotopologue')
		
		if not multiple:
			return instance
		else:
			instances = []
			while instance is not None:
				instances.append(instance)
				instance, formula = cls.regex_match(formula)
			
			return tuple(instances)
	@classmethod
	def from_isoslug(cls, formula : str, multiple=False) -> Self | tuple[Self,...]:
		# Example "1H2-16O", "16O-17O-16O"
		
		instance, formula = cls.isoslug_regex_match(formula)
		
		if instance is None:
			raise ValueError(f'{formula=} does not denote an Isotopologue')
		
		if not multiple:
			return instance
		else:
			instances = []
			while instance is not None:
				instances.append(instance)
				instance, formula = cls.isoslug_regex_match(formula)
			
			return tuple(instances)
	
	def _get_charge_str(self):
		if self.charge == 0:
			return ''
		elif self.charge == 1:
			return '+'
		elif self.charge == -1:
			return '-'
		else:
			return str(self.charge)
	
	def __repr__(self):
		s = []
		n = []
		prev_iso = None
		for iso in self.isotopes:
			if prev_iso is not None and prev_iso == iso:
				n[-1] += 1
			else:
				s.append(str(iso))
				n.append(1)
			prev_iso = iso
		return ''.join((a if x == 1 else f'{a}{x}' for a,x in zip(s,n)))+self._get_charge_str()
	
	def as_iso_slug(self):
		s = []
		n = []
		prev_iso = None
		for iso in self.isotopes:
			if prev_iso is not None and prev_iso == iso:
				n[-1] += 1
			else:
				s.append(f'{iso.nucleon_number}{iso.name}')
				n.append(1)
			prev_iso = iso
		return '-'.join((a if x == 1 else f'{a}{x}' for a,x in zip(s,n))) + (f'_{("p" if self.charge > 0 else "m")}{abs(self.charge)}' if self.charge != 0 else '')
	
	@property
	def Molecule(self):
		return Molecule(tuple(sorted(isotope.AtomicElement for isotope in self.isotopes)), self.charge)
