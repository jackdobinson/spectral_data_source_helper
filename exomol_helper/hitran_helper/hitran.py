
from pathlib import Path
from typing import NamedTuple, Annotated, get_origin, get_args, Union
import urllib
import dataclasses as dc

import numpy as np

from .html import isotopologue
from .datatypes.hitran_isotope import HitranIsotope
from .datatypes.partition_function import PartitionFunctionEntry
import exomol_helper.utils.dtype
import exomol_helper.utils.fetch
import exomol_helper.utils.read

from ..cfg.const import (
	EXOMOL_CACHE,
)


HITRAN_PF_URL_FMT = 'https://www.hitran.org/data/Q/q{global_id}.txt'
HITRAN_160_PAR_FILE_API_URL_FMT = "https://hitran.org/lbl/api?iso_ids_list={global_id}&head=False&fixwidth=0"
HITRAN_API_URL_FMT = "https://hitran.org/lbl/api?iso_ids_list={global_id}&head=False&fixwidth=0&sep=[comma]&request_params={par_list}"


HITRAN_INDEX = None

HITRAN_PF_DATA = None

class HitranLineDataFiles(NamedTuple):
	par_file : Path
	broadener_files : dict[str,Path]



Hitran160Layout = (2,1,12,10,10,5,5,10,4,8,15,15,15,15,(1,1,1,1,1,1),(2,2,2,2,2,2),1,7,7)

class Hitran160Record(NamedTuple):
	"""
	Fixed width format can be specified like a table with the following columns:

	attribute name                     : type                           = width (in ascii characters)
	"""
	mol_id                             : Annotated[int, "molecular id", 2]
	iso_id                             : Annotated[int, 'isotopologue id', 1]
	line_wavenumber                    : Annotated[float, "", 12]
	line_strength                      : Annotated[float, "", 10]
	einstein_a_coeff                   : Annotated[float, "", 10]
	gamma_amb                          : Annotated[float, "", 5]
	gamma_self                         : Annotated[float, "", 5]
	e_lower                            : Annotated[float, "", 10 ]
	n_amb                              : Annotated[float, "", 4]
	delta_amb                          : Annotated[float, "", 8]
	global_upper_quanta                : Annotated[str, "", 15]
	global_lower_quanta                : Annotated[str, "", 15]
	local_upper_quanta                 : Annotated[str, "", 15]
	local_lower_quanta                 : Annotated[str, "", 15]
	#ierr                               : Annotated[tuple[int,int,int,int,int,int], "", (1,1,1,1,1,1)]
	ierr                               : Annotated[str, "", 6]
	#iref                               : Annotated[tuple[int,int,int,int,int,int], "", (2,2,2,2,2,2)]
	iref                               : Annotated[str, "", 12]
	line_mixing_flag                   : Annotated[str, "", 1]
	gp                                 : Annotated[float, "", 7]
	gpp                                : Annotated[float, "", 7]

	@classmethod
	def dtype(cls) -> np.dtype:
		def get_dtype(t, use_var_strings=False, max_str_len=32):
		
			ot = get_origin(t)
			if ot is None:
				if t == str:
					return np.dtype('T') if use_var_strings else np.dtype(f'U{max_str_len}')
				else:
					return np.dtype(t)
			if ot == Union:
				t = get_args(t)[0]
				if t == str:
					return np.dtype('T') if use_var_strings else np.dtype(f'U{max_str_len}')
				else:
					return np.dtype(t)
			else:
				tt = get_args(t)
				if all (x == tt[0] for x in tt):
					t= get_dtype(tt[0])
					return np.dtype((t.type,(len(tt),*t.shape)))
				else:
					ts = []
					for xt in tt:
						t = get_dtype(xt)
						ts.append(
							('', t)
						)
					return np.dtype(ts)
		names = []
		types = []
		descriptions = []
		widths = []
		dtypes = []
		for nn,anno in cls.__annotations__.items():
			(tt,dd,ww) = get_args(anno)
			names.append(nn)
			types.append(tt)
			descriptions.append(dd)
			widths.append(ww)
			dtypes.append(get_dtype(tt, use_var_strings=False, max_str_len=ww))
		
		return np.dtype({"names":names, "formats":dtypes})
	
	@classmethod
	def widths(cls):
		return dict((nn,get_args(anno)[2]) for nn,anno in cls.__annotations__.items())

	@classmethod
	def structured_array_from(
			cls, 
			fpath : Path, 
			chunk_size : int = 1_000,
		):
		
		# Account for `iso_id` values greater than 9 when only have a single digit to use
		mutator = lambda it: (x if i!=1 else {0:10,'A':11,'B':12}.get(x,x) for i,x in enumerate(it))
		
		return exomol_helper.utils.read.load_line_records_into_structured_array_by_chunks(
			fpath,
			cls.dtype(),
			widths=tuple(cls.widths().values()),
			mutator=mutator
		)

@dc.dataclass
class HitranDatasetHolder:
	d : HitranIsotope
	
	# private attributes
	_pf_data_file : None | Path = None
	_pf_data : None | np.ndarray = None
	_broadener_files : None | dict[str, Path] = None
	_broadeners : None | dict[str, np.ndarray] = None
	_linedata_file : None | Path = None
	_linedata : None | np.ndarray = None
	
	@property
	def pf_data_file(self) -> Path:
		if self._pf_data_file is None:
			self._pf_data_file = exomol_helper.utils.fetch.file_from_cache(
				HITRAN_PF_URL_FMT.format(global_id=self.d.global_id),
				cache = EXOMOL_CACHE,
				return_fpath=True,
				#refresh=True,
			)
		return self._pf_data_file
	
	@property
	def pf_data(self) -> np.ndarray:
		if self._pf_data is None:
			self._pf_data = PartitionFunctionEntry.structured_array_from(
				self.pf_data_file
			)
		return self._pf_data
	
	@property
	def broadener_files(self) -> dict[str,Path]:
		if self._broadener_files is None:
			self._broadener_files = dict()
			for j, broadener in enumerate(isotopologue.hitran_broadeners):
				print(f'Fetching "{broadener}" [{j}/{len(isotopologue.hitran_broadeners)} %] [{100*j/len(isotopologue.hitran_broadeners):6.2f}] broadening data for {self.d.iso_formula=}')
				broad_pars = [x+broadener for x in isotopologue.hitran_broadener_pars]
				broad_url = HITRAN_API_URL_FMT.format(global_id=self.d.global_id, par_list=','.join(broad_pars))
				
				try:
					bfp = exomol_helper.utils.fetch.file_from_cache(
						broad_url,
						cache = EXOMOL_CACHE,
						return_fpath=True,
						not_found_in_cache_action='cache_empty',
						error_code_action={
							500:'ignore',
							404:'warning',
						},
					)
				except urllib.error.HTTPError as e:
					if e.code == 403:
						# Have run out of API queries for today
						bfp = None
				
				if bfp is not None:
					self._broadener_files[broadener] = bfp
		return self._broadener_files
	
	@property
	def broadeners(self) -> dict[str,np.ndarray]:
		if self._broadeners is None:
			self._broadeners = dict()
			for j, (broadener, broadener_file) in enumerate(self.broadener_files.items()):
				print(f'Loading "{broadener}" [{j}/{len(self.broadener_files)} %] [{100*j/len(self.broadener_files):6.2f}] broadening data for {self.d.iso_formula=} {self.d.global_id=} from {broadener_file.name=}')
				broad_pars = [x+broadener for x in isotopologue.hitran_broadener_pars]
				broad_dtype = np.dtype([(x,float) for x in broad_pars])
				
				broad_data = exomol_helper.utils.read.load_line_records_into_structured_array_by_chunks(
					broadener_file,
					dtype=broad_dtype,
					delim=',',
					mutator=lambda it: (x if not x.startswith('#') else 'nan' for x in it)
				)
				
				if len(broad_data) > 0:
					self._broadeners[broadener] = broad_data
		return self._broadeners

	@property
	def linedata_file(self) -> Path:
		if self._linedata_file is None:
			par_url = HITRAN_160_PAR_FILE_API_URL_FMT.format(global_id = self.d.global_id)
			try:
				self._linedata_file = exomol_helper.utils.fetch.file_from_cache(
					par_url,
					cache = EXOMOL_CACHE,
					return_fpath=True,
					not_found_in_cache_action='cache_empty',
					error_code_action={
						500:'ignore',
						404:'warning',
					},
				)
			except urllib.error.HTTPError as e:
				if e.code == 403:
					# Have run out of API queries for today
					self._linedata_file = ''
		return self._linedata_file

	@property
	def linedata(self) -> np.ndarray:
		if self._linedata is None:
			print(f'Loading linedata for {self.d.iso_formula=} {self.d.global_id=}')
			if self.linedata_file != '':
				self._linedata = Hitran160Record.structured_array_from(
					self.linedata_file,
				)
			else:
				self._linedata = np.empty((0,), Hitran160Record.dtype())
		return self._linedata





def build_index():
	global HITRAN_INDEX
	
	HITRAN_INDEX = dict()
	isotopologue.download_hitran_isotope_data()

	# Load HITRAN index
	#HITRAN_INDEX = HitranIsotope.structured_array_from(isotopologue.HITRAN_ISO_TABLE)
	for rec in HitranIsotope.record_array_from(isotopologue.HITRAN_ISO_TABLE):
		HITRAN_INDEX.setdefault(str(rec.mol_formula).strip(), dict())[str(rec.iso_formula).strip()] = HitranDatasetHolder(HitranIsotope(*rec))
	#print(f'{HITRAN_INDEX=}')


def load_partition_function_data():
	# Load partition function data for each isotopologue
	for mol_formula, isos in HITRAN_INDEX.items():
		for iso_formula, ds_holder in isos.items():
			#ds_holder.pf_data
			ds_holder.pf_data_file

def load_line_data():
	for mol_formula, isos in HITRAN_INDEX.items():
		for iso_formula, ds_holder in isos.items():
			#ds_holder.linedata
			ds_holder.linedata_file

def load_broadening_data():
	for mol_formula, isos in HITRAN_INDEX.items():
		for iso_formula, ds_holder in isos.items():
			ds_holder.broadeners


build_index()

load_partition_function_data()

load_line_data()

load_broadening_data()






