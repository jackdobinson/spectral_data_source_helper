
from typing import Callable, Any

from .base import BaseProgressTracker

from .datatypes.chunk_rate_info import ChunkRateInfo
from .datatypes.memory_rate_info import MemoryRateInfo
	
class ChunkProgressTracker(BaseProgressTracker):
	def __init__(
			self, 
			data_handler : Callable[[Any],Any] = None,
			rate_limit_timeout : float = 0,
			chunk_element_name : str = 'Line',
		):
		super().__init__(data_handler, rate_limit_timeout)
		self.chunk_element_name = chunk_element_name
		self.source_name = ''
		
		self.total_bytes = 0
		self.prev_total_bytes = 0
		self.total_elements = 0
		self.prev_total_elements = 0
		

	def reset(self):
		super().reset()
		self.total_elements = 0
		self.total_bytes = 0
		self.prev_total_bytes = 0
		self.prev_total_elements = 0

	def set(self, delta_chunk_elements : int, delta_bytes : int):
		self.total_bytes += delta_bytes
		self.total_elements += delta_chunk_elements
	
		if not self.rate_limit_expired():
			return
		
		self.data = ChunkRateInfo(
			self.source_name,
			element_name = self.chunk_element_name,
			total_elements = self.total_elements,
			rolling_elements = self.total_elements - self.prev_total_elements,
			total_memory_rate = MemoryRateInfo(
				self.total_bytes,
				self.total_elapsed_sec,
			),
			rolling_memory_rate = MemoryRateInfo(
				self.total_bytes - self.prev_total_bytes,
				self.split_elapsed_sec,
			),
		)
		
		self.prev_total_bytes = self.total_bytes
		self.prev_total_elements = self.total_elements
		
		
		self.emit()