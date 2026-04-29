
from typing import Callable, Any

from .base import BaseProgressTracker

from .datatypes.chunk_rate_info import ChunkRateInfo
from .datatypes.memory_rate_info import MemoryRateInfo
	
class ChunkProgressTracker(BaseProgressTracker):
	def __init__(
			self, 
			data_handler : Callable[[Any],Any] = None,
			rate_limit_timeout : float = 0,
			chunk_element_name : str = 'Line'
		):
		super().__init__(data_handler, rate_limit_timeout)
		self.prev_total_bytes = 0
		self.chunk_element_name = chunk_element_name
		

	def set(self, chunk_element_num : int, total_bytes : int):
		if not self.rate_limit_expired():
			return
		
		self.data = ChunkRateInfo(
			total_elements = chunk_element_num,
			element_name = self.chunk_element_name,
			total_memory_rate = MemoryRateInfo(
				total_bytes,
				self.total_elapsed_sec + 1E-30,
			),
			rolling_memory_rate = MemoryRateInfo(
				total_bytes - self.prev_total_bytes,
				self.split_elapsed_sec + 1E-30,
			),
		)
		
		self.prev_total_bytes = total_bytes
		
		self.emit()