"""
Functions and classes etc. that fetch resources from the web.
"""
#import os
from pathlib import Path
import urllib.request
import ssl
from typing import Generator, Literal, Any
import dataclasses as dc

from exomol_helper.cfg.log import progress_lgr
from exomol_helper.cfg.log import pkg_logger as _lgr


WEB_PREFIXES = (
	'https://',
	'http://',
	'ftp://',
	'sftp://',
	'file://',
)
DEFAULT_CHUNK_SIZE = 10*1024*1024 # bytes
MEM_UNIT_BYTES = 1024*1024
MEM_UNIT_NAME = 'Mb' #'Kb'
PROGRESS_INTERVAL_MEM_UNIT : None | float = 100
# Interval (in kilobytes) on amount of data fetched to report progress (at log level `INFO`). If `None` will not report progress.

@dc.dataclass(slots=True)
class TaskState:
	state : Literal['uninitialised', 'initialised', 'waiting', 'paused', 'executing', 'failed', 'succeeded'] = 'uninitialised',
	
	def set(
			self, 
			state : Literal['uninitialised', 'initialised', 'waiting', 'paused', 'executing', 'failed', 'succeeded'],
	):
		assert state in ('uninitialised', 'initialised', 'waiting', 'paused', 'executing', 'failed', 'succeeded'), f'Unknown state "{state}"'
		self.state = state
	
	def get(self) -> str:
		return self.state
	
	def is_ready(self) -> bool:
		return self.state in ('initialised', 'waiting')
	
	def was_started(self) -> bool:
		return not self.state in ('uninitialised', 'initialised', 'waiting')
	
	def is_inprogress(self) -> bool:
		return self.state in ('paused', 'executing')
	
	def is_finished(self) -> bool:
		return self.state in ('failed', 'succeeded')
	
	def __eq__(self, state : Literal['uninitialised', 'initialised', 'waiting', 'paused', 'executing', 'failed', 'succeeded']) -> bool:
		assert state in ('uninitialised', 'initialised', 'waiting', 'paused', 'executing', 'failed', 'succeeded'), f'Unknown state "{state}" for comparison'
		return self.state == state
	
	def __ne__(self, state : Literal['uninitialised', 'initialised', 'waiting', 'paused', 'executing', 'failed', 'succeeded']) -> bool:
		return not (self.__eq__(state))



class ChunkedFileDownloader:
	def __init__(self,
			url : str,
			chunk_size : None | int = DEFAULT_CHUNK_SIZE, 
			encoding : str = 'ascii', 
			proxy : None | dict[str,str] = None,
			error_code_action : dict[int | Literal['timeout'],Literal['ignore','warning','error']] = dict(),
			skip_if_content_length : None | int = None, # If not `None` will compare the size on disk with the 'Content-Length' in the header and skip if they are equal.
			timeout : None | int = 2, # timeout in seconds to wait for response
	):
		self.url = url
		self.chunk_size = chunk_size
		self.encoding = encoding
		self.proxy=proxy
		self.error_code_action = error_code_action
		self.skip_if_content_length = skip_if_content_length
		self.status = TaskState()
		
		self.content_length = -1 # if -ve content length is not specified
	
		req = urllib.request.Request(url)
		_lgr.debug(f'{url=}')
		_lgr.debug(f'{chunk_size=} {encoding=}')
		_lgr.debug(f'{skip_if_content_length=}')
		
		
		handlers = []
		
		if req.type == 'https':
			#context = ssl._create_unverified_context()
			context = ssl.create_default_context(
				ssl.Purpose.SERVER_AUTH, # SERVER_AUTH is 'we want the server to be able to authenticate us', so it is used by clients connecting to servers.
			)
			handlers.append(urllib.request.HTTPSHandler(context=context))
		elif req.type == 'http':
			handlers.append(urllib.request.HTTPHandler())
		else:
			raise urllib.error.UrlError('Unknown request type "{req.type}", cannot assign handler')
				
		if proxy is not None:
			_lgr.info('Using the following proxies:')
			for k, v in proxy.items():
				_lgr.info(f'\t{k} : {v}')
			handlers.append(urllib.request.ProxyHandler(proxy))
		
		opener = urllib.request.build_opener(*handlers)
		
		try:
			self.response = opener.open(url, timeout=timeout)
		except urllib.error.HTTPError as e:
			self.status.set('failed')
			eca = error_code_action.get(e.code, 'error')
			match eca:
				case 'ignore':
					return
				case 'warning':
					_lgr.warn(f'Could not open url. Error: {str(e)}')
					return
				case _:
					raise
		except urllib.error.URLError as e:
			self.status.set('failed')
			if isinstance(e.__cause__, TimeoutError) or isinstance(e.__context__, TimeoutError):
				eca = error_code_action.get('timeout', 'error')
				match eca:
					case 'ignore':
						return
					case 'warning':
						_lgr.warn(f'Could not open url. Error: {str(e)}')
						return
					case _:
						raise
			else:
				raise
		
		self.content_length = int(self.response.headers.get('Content-Length', -1))
		if skip_if_content_length is not None and (skip_if_content_length == self.content_length):
			_lgr.debug(f'skipping... {skip_if_content_length=} {self.content_length=}')
			self.status.set('succeeded')
		
		if chunk_size is None:
			self.get_chunk = lambda response: response.readline()
		else:
			self.get_chunk = lambda response: response.read(chunk_size)
			
		if encoding is None:
			self.do_decode = lambda x: x
		else:
			self.do_decode = lambda x: x.decode(encoding)
		
		if self.status == 'uninitialised':
			self.status.set('waiting')
	
	def download(self) -> Generator[bytes|str]:
		self.status.set('executing')
		#last_reported_size = -1E30 # very negative number so we report the first size value
		self.accumulated_size = 0
		i = 0
		
		while (size_of_current_chunk := len(chunk := self.get_chunk(self.response))) > 0:
			
			
			#if PROGRESS_INTERVAL_MEM_UNIT is not None and ((self.accumulated_size - last_reported_size) >= (PROGRESS_INTERVAL_MEM_UNIT*MEM_UNIT_BYTES)):
			progress_lgr.info(f'Fetching chunk {i}. Chunk is {size_of_current_chunk/MEM_UNIT_BYTES:8.2f} {MEM_UNIT_NAME}. Fetched {self.accumulated_size/MEM_UNIT_BYTES:8.2f} {MEM_UNIT_NAME} so far...')
			#last_reported_size = self.accumulated_size
			
			self.accumulated_size += size_of_current_chunk
			self.status.set('paused')
			yield self.do_decode(chunk)
			self.status.set('executing')
			i += 1
			
		
		self.status.set('succeeded')
		progress_lgr.info(f'Fetch complete, downloaded {self.accumulated_size/MEM_UNIT_BYTES:8.2f} {MEM_UNIT_NAME} in total over {i} chunks.')
		
		return
	
	def can_check_download(self):
		return self.content_length > 0
	
	def is_download_complete(self):
		if not self.can_check_download():
			raise RuntimeError('Cannot say if download is complete as content length was not supplied')
		
		if self.content_length == self.accumulated_size:
			return True
		elif self.content_length > self.accumulated_size:
			return False
		else:
			raise RuntimeError(f'Accumulated size {self.accumulated_size} is greater than supplied content length {self.content_length}')

def file(
		url : str, 
		*, # All following arguments are keyword only
		to_fpath : None | str | Path = None, 
		encoding : None | str = None, 
		proxy : None | dict[str,str] = None,
		prefix : None | str = None, # string to prefix to downloaded data
		error_code_action : dict[int,Literal['ignore','warning','error']] = dict(),
		use_working_file = False, # If True will use a "working file" to download data into, then move it into the "real" file after download is complete. Has not effect if `to_fpath` is None.
		chunk_size : None | int = DEFAULT_CHUNK_SIZE, 
		skip_if_size_on_disk : bool = True,
		remove_file_on_failure : bool = True, # If possible, remove the file if the download failed for any reason
		timeout : None | int = 2, # Number of seconds to wait for internet
) -> None | bytes | str:
	"""
	## ARGUMENTS ##
		url : str
			Universal Resource Location to fetch file from, written as a string.
		to_fpath : None | str = None
			filepath to save file to. If present will save data to the file and
			return `None`, otherwise will not save file and will return
			the data instead.
		encoding : None | str = None
			Name of file encoding ('ascii', 'utf-8', ...). If `None` will return bytes
		proxy : None | dict[str,str] = None
			`None` or a dictionary detailing proxy mappings

	## RETURNS ##
		data : None | bytes | str
			If `to_fpath` is not `None` will return data from the file at the `url`.
			Otherwise will write the data to a file at `to_fpath` and return `None`.
	"""
	to_fpath = None if to_fpath is None else Path(to_fpath)
	
	file_chunk_downloader = ChunkedFileDownloader(
		url, 
		chunk_size=chunk_size, 
		encoding=encoding, 
		proxy=proxy, 
		error_code_action=error_code_action,
		skip_if_content_length=(
			None if (
				(not skip_if_size_on_disk) 
				or (to_fpath is None) 
				or (not to_fpath.exists())
			) else to_fpath.lstat().st_size
		),
		timeout=timeout
	)
	
	if not file_chunk_downloader.status.is_finished():
	
		print('Performing download...')
		
		if encoding is None:
			if prefix is not None and isinstance(prefix, str):
				prefix = bytes(prefix, encoding='utf-8')
			
		if to_fpath is not None:
			_lgr.info(f"Downloading from {url} and saving to path '{to_fpath}'")
			
			write_mode = 'wb' if encoding is None else 'w'
			
			if use_working_file:
				_lgr.debug('Using working file')
				real_fpath = Path(to_fpath)
				to_fpath = real_fpath.with_stem('~'+real_fpath.stem)
			
			_lgr.info(f'Writing to "{to_fpath}"')
			with open(to_fpath, write_mode) as f:
				if prefix is not None:
					f.write(prefix)
				try:
					for chunk in file_chunk_downloader.download():
						f.write(chunk)
				except:
					file_chunk_downloader.status = 'failed'
					# delete file if something goes wrong
					if remove_file_on_failure:
						to_fpath.unlink()
					raise
			
			# If no error, move the working file to the desired file path
			if use_working_file:
				_lgr.debug('Moving working file')
				to_fpath.replace(real_fpath)
			
			return
		
		else:
			empty_str = b'' if encoding is None else ''
			try:
				return (empty_str if prefix is None else prefix) + empty_str.join(file_chunk_downloader.download())
			except:
				file_chunk_downloader.status = 'failed'
				raise

	elif file_chunk_downloader.status == 'failed':
		_lgr.error(f'Could not download {url}')
		return None
	elif file_chunk_downloader.status == 'succeeded':
		# This should only happen if `to_fpath` is not None and the downloadable content length is the same as the file. Therefore return None
		return None
	else:
		raise RuntimeError(f'File chunk downloader has unhandled status {file_chunk_downloader.status=}')


def file_from_cache(
		url : str,
		cache : str | Path,
		return_fpath : bool = False, # if True will return the file path to to cached data instead of the cached data itself
		remove_www : bool = True, # if True, will remove "www.xxx.yyy" from URLs to give "xxx.yyy".
		refresh : bool = False, # if True, will refresh the cache
		check_web_first : bool = False,
		not_found_in_cache_action : Literal['error', 'return_none', 'return_empty', 'cache_empty'] = 'error',
		**kwargs : dict[str,Any], # Passed to `fetch.file(...)`
	) -> Path | bytes | str:
	
	default_kwargs = {
		'remove_file_on_failure' : True,
	}
	
	url_copy = url[:]
	for x in WEB_PREFIXES:
		if url_copy.startswith(x):
			url_copy = url_copy[len(x):]
			break
	
	if remove_www and url_copy.startswith('www.'):
		url_copy = url_copy[4:]
	
	site_dir, fpath = url_copy.split('/',1)
	
	#print(f'{cache=} {site_dir=} {fpath=}')
	
	cache_fpath = Path(cache) / Path(site_dir) / fpath
	
	if not cache_fpath.is_relative_to(cache):
		raise RuntimeError(f'Constructed cache path {cache_fpath} is not relative to {cache}')
	
	#print(f'{cache_fpath=}')
	
	# Check cache for file, return it if it exists
	
	if not check_web_first and not refresh and cache_fpath.exists():
		#print('CACHE HIT')
		if return_fpath:
			return cache_fpath
		else:
			with open(cache_fpath, 'r') as f:
				return f.read()
	
	
	#print('CACHE MISS')
	# otherwise cache is not found
	
	# ensure containing folder is created
	cache_fpath.parent.mkdir(parents=True,exist_ok=True)
	
	# download file into folder
	file(
		url, 
		to_fpath = cache_fpath, 
		skip_if_size_on_disk=not refresh, 
		**{**default_kwargs, **kwargs},
	)

	
	if not cache_fpath.exists():
		if not_found_in_cache_action == 'return_none':
			return None
			
		elif not_found_in_cache_action == 'return_empty':
			if return_fpath:
				EMPTY_CACHE_PATH = Path(cache)/'empty'
				with open(EMPTY_CACHE_PATH, 'w') as f:
					pass
				return EMPTY_CACHE_PATH
			else:
				return ''
				
		elif not_found_in_cache_action == 'cache_empty':
			with open(cache_fpath, 'w') as f:
				pass
				
		else:
			raise RuntimeError(f'Could not retrieve {url} from cache at {cache_fpath}')
	
	if return_fpath:
		return cache_fpath
	else:
		with open(cache_fpath, 'r') as f:
			return f.read()




