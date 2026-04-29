
from typing import Callable, Any, Self
import inspect

from ..utils.time_split_gen import TimeSplitGen

class BaseProgressTracker:
	def __init__(
			self, 
			data_handler : Callable[[Any],Any] = None,
			rate_limit_timeout : float = 0,
		):
		self.label = self._get_label()
		self.data_handler = data_handler
		self.rate_limit_timeout = rate_limit_timeout
		
		self.time_split_iter = iter(TimeSplitGen())
		self.total_elapsed_sec = 0
		self.split_elapsed_sec = 0
		
		self.data = None
	
	@classmethod
	def _get_label(cls):
		frame = inspect.currentframe().f_back.f_back.f_back
		return f'[{cls.__name__} from {frame.f_code.co_filename.rsplit('/')[-1]} {frame.f_lineno}]'
	
	def reset(self) -> Self:
		self.time_split_iter = iter(TimeSplitGen())
		self.total_elapsed_sec = 0
		self.split_elapsed_sec = 0
		
		self.data = None
		return self
	
	def rate_limit_expired(self) -> bool:
		(self.total_elapsed_sec, split_elapsed_sec) = next(self.time_split_iter)
		self.split_elapsed_sec += split_elapsed_sec
		
		if (self.rate_limit_timeout == 0) | (self.split_elapsed_sec >= self.rate_limit_timeout):
			return True
		return False
	
	def set(self, *args, **kwargs):
		if not self.rate_limit_expired():
			return
		
		# NOTE: at this point the current attributes have been set:
		# * self.total_elapsed_sec
		# * self.split_elapsed_sec
	
		raise NotImplementedError("Subclasses of BaseProgressTracker should implement the `set(...)` method")
	
		self.emit()
	
	def get(self)->Any:
		return self.data
	
	def emit(self):
		self.split_elapsed_sec = 0
		if self.data_handler is not None:
			self.data_handler(self.data)