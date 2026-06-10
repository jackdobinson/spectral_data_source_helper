
from pathlib import Path
from typing import Generator, Callable, Literal, Self
import dataclasses as dc
import urllib

import numpy as np

import spectral_data_source_helper.utils.dtype
import spectral_data_source_helper.utils.fetch
import spectral_data_source_helper.utils.read

from spectral_data_source_helper.cfg.const import (
	PKG_CACHE,
)

from spectral_data_source_helper.cfg.log import pkg_logger as _lgr

from .cfg.const import (
	HITRAN_API_URL_FMT,
	HITRAN_PF_URL_FMT,
	HITRAN_160_PAR_FILE_API_URL_FMT,
	HITRAN_BAD_BROADENER_LINE_STARTS,
)

from . import html
from .datatypes.hitran_isotope import HitranIsotope
from .datatypes.partition_function import PartitionFunctionEntry
from .datatypes.hitran_160_record import Hitran160Record


@dc.dataclass(slots=True)
class HitranDatasetHolder:
	d : HitranIsotope
	
	# private attributes
	_pf_data_file : None | Path = None
	_pf_data : None | np.ndarray = None
	_broadener_line_mutator : Literal[dc.MISSING] | None | Callable[[str],None | str] = dc.field(default_factory=lambda : dc.MISSING)
	_broadener_files : None | dict[str, Path] = None
	_broadeners : None | dict[str, np.ndarray] = None
	_linedata_file : None | Path = None
	_linedata : None | np.ndarray = None
	
	@property
	def pf_data_url(self) -> str:
		return HITRAN_PF_URL_FMT.format(global_id=self.d.global_id)
	
	@property
	def pf_data_file(self) -> Path:
		if self._pf_data_file is None:
			self._pf_data_file = spectral_data_source_helper.utils.fetch.file_from_cache(
				self.pf_data_url,
				cache = PKG_CACHE,
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
	def broadener_urls(self) -> dict[str,str]:
		for broadener in html.isotopologue.hitran_broadeners:
			broad_pars = [x+broadener for x in html.isotopologue.hitran_broadener_pars]
			broad_url = HITRAN_API_URL_FMT.format(global_id=self.d.global_id, par_list=','.join(broad_pars))
			yield broadener, broad_url
	
	@property
	def broadener_files(self) -> dict[str,Path]:
		if self._broadener_files is None:
			self._broadener_files = dict()
			for j, (broadener, broad_url) in enumerate(self.broadener_urls):
				_lgr.debug(f'Fetching "{broadener}" [{j}/{len(html.isotopologue.hitran_broadeners)}] [{100*j/len(html.isotopologue.hitran_broadeners):6.2f} %] broadening data for {self.d.iso_formula=}')
			
				try:
					bfp = spectral_data_source_helper.utils.fetch.file_from_cache(
						broad_url,
						cache = PKG_CACHE,
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
				
				if bfp is not None and bfp.lstat().st_size != 0:
					self._broadener_files[broadener] = bfp
		return self._broadener_files
	
	@property
	def broadener_names(self) -> tuple[str,...]:
		return self.broadener_files.keys()
	
	@property
	def broadener_pars(self) -> dict[str,tuple[str,...]]:
		return dict((broadener,[x+broadener for x in html.isotopologue.hitran_broadener_pars]) for broadener in self.broadener_names)
	
	@property
	def broadener_dtypes(self) -> dict[str, np.dtype]:
		bpd = self.broadener_pars
		return dict((broadener,np.dtype([(x,float) for x in bpd[broadener]])) for broadener in self.broadener_names)
	
	@property
	def broadener_line_mutator(self) -> Callable[[str], None | str]:
		if self._broadener_line_mutator is dc.MISSING:
			if self.d.global_id in HITRAN_BAD_BROADENER_LINE_STARTS:
				bad_line_start_info = tuple((len(x),x) for x in HITRAN_BAD_BROADENER_LINE_STARTS[self.d.global_id])
				self._broadener_line_mutator = lambda s: 'nan,nan,nan\n' if any(s[:n] == x for n,x in bad_line_start_info) else None
			else:
				self._broadener_line_mutator = None
		return self._broadener_line_mutator
		
	@property
	def broadeners(self) -> dict[str,np.ndarray]:
		if self._broadeners is None:
			self._broadeners = dict()
			broad_dtypes = self.broadener_dtypes
			
			for j, (broadener, broadener_file) in enumerate(self.broadener_files.items()):
				_lgr.debug(f'Loading "{broadener}" [{j}/{len(self.broadener_files)}] [{100*j/len(self.broadener_files):6.2f} %] broadening data for {self.d.iso_formula=} {self.d.global_id=} from {broadener_file.name=}')
				
				broad_data = spectral_data_source_helper.utils.read.load_line_records_into_structured_array_by_chunks(
					broadener_file,
					dtype=broad_dtypes[broadener],
					delim=',',
					mutator=lambda it: (x if not x.startswith('#') else 'nan' for x in it),
					line_mutator = self.broadener_line_mutator
				)
				
				if len(broad_data) > 0:
					self._broadeners[broadener] = broad_data
		return self._broadeners

	@property
	def linedata_url(self) -> str:
		return HITRAN_160_PAR_FILE_API_URL_FMT.format(global_id = self.d.global_id)

	@property
	def linedata_file(self) -> Path:
		if self._linedata_file is None:
			try:
				self._linedata_file = spectral_data_source_helper.utils.fetch.file_from_cache(
					self.linedata_url,
					cache = PKG_CACHE,
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
			_lgr.info(f'Loading linedata for {self.d.iso_formula=} {self.d.global_id=} [HITRAN ID: {self.d.global_id=}]')
			if self.linedata_file != '':
				self._linedata = Hitran160Record.structured_array_from(
					self.linedata_file,
				)
			else:
				self._linedata = np.empty((0,), Hitran160Record.dtype())
		return self._linedata
	
	def get_linedata_file(self, refresh : bool = False) -> Path:
		if refresh and self.linedata_file != '':
			self._linedata_file.unlink(missing_ok=True)
			self._linedata_file = None
			self._linedata = None
		return self.linedata_file
	
	def get_pf_data_file(self, refresh : bool = False) -> Path:
		if refresh:
			self._pf_data_file.unlink(missing_ok=True)
			self._pf_data_file = None
			self._pf_data = None
		return self.pf_data_file
	
	def get_broadener_files(self, refresh : bool = False) -> dict[str, Path]:
		if refresh:
			for broadener_file in self.broadener_files.values():
				broadener_file.unlink(missing_ok=True)
			self._broadener_files = None
			self._broadeners = None
		return self.broadener_files
	
	def cache_data(self, refresh : bool = False) -> Self:
		# Cache all data for this dataset
		self.get_pf_data_file(refresh=refresh)
		self.get_linedata_file(refresh=refresh)
		self.get_broadener_files(refresh=refresh)
	
		return self
	
	def iter_broadener_chunk(self, broadener : str, chunk_size : int =1_000_000) -> Generator[np.ndarray]:
		assert broadener in self.broadener_names, f"Unknown broadener '{broadener}' for {self.d.iso_formula} [HITRAN ID: {self.d.global_id=}]"
		
		broad_file = self.broadener_files[broadener]
		broad_dtype = self.broadener_dtypes[broadener]
		
		yield from spectral_data_source_helper.utils.read.iter_line_records_via_structured_array_chunk(
			broad_file,
			dtype=broad_dtype,
			delim=',',
			mutator=lambda it: (x if not x.startswith('#') else 'nan' for x in it),
			line_mutator = self.broadener_line_mutator,
			chunk_size=chunk_size,
		)
	
	
	def iter_broadeners_chunk(self, chunk_size : int = 1_000_000) -> Generator[np.ndarray]:
		# Build combined structured array for all valid broadeners
		bpd = self.broadener_pars
		broad_pars = []
		for broadener, bp in bpd.items():
			broad_pars += list(bp)
		
		broad_dtype = np.dtype([(x,float) for x in broad_pars])
		
		chunk = np.empty((chunk_size,), dtype=broad_dtype)
		
		single_broad_chunk_gens = dict((x, (bpd[x], self.iter_broadener_chunk(x, chunk_size=chunk_size))) for x in bpd.keys())
		
		gen_exhausted = dict((x,False) for x in bpd.keys())
		
		while True:
			chunk.fill(np.nan)
			result_chunk_size = 0
			
			for broadener, (bp, sbc_gen) in single_broad_chunk_gens.items():
				if not gen_exhausted[broadener]:
					_lgr.info(f'Loading "{broadener}" broadening data for {self.d.iso_formula} [HITRAN_ID: {self.d.global_id}]')# from {self.broadener_files[broadener].name=}')
					try:
						sb_chunk = next(sbc_gen)
					except StopIteration:
						gen_exhausted[broadener] = True
					else:
						sb_chunk_size = sb_chunk.shape[0]
						result_chunk_size = max(result_chunk_size, sb_chunk_size)
						chunk[bp][:sb_chunk_size] = sb_chunk
			
			if not all(gen_exhausted.values()):
				yield chunk[:result_chunk_size]
			else:
				return
	
	
	def iter_linedata_chunk(self, chunk_size : int = 1_000_000) -> Generator[np.ndarray]:
		yield from Hitran160Record.iter_structured_array_from(
			self.linedata_file,
			chunk_size=chunk_size,
		)