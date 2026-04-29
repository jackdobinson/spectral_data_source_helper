
from typing import Callable, Any

from .base import BaseProgressTracker

from .datatypes.value_rate_info import ValueRateInfo
	
class ValueProgressTracker(BaseProgressTracker):
	def __init__(
			self, 
			data_handler : Callable[[Any],Any] = None,
			rate_limit_timeout : float = 0,
			unit : str = 'items'
		):
		super().__init__(data_handler, rate_limit_timeout)
		self.prev_total_value = 0
		self.unit = unit
		

	def set(self, total_value : float):
		if not self.rate_limit_expired():
			return
		
		self.data = ValueRateInfo(
			unit = self.unit,
			total_value = total_value,
			total_elapsed_sec = self.total_elapsed_sec,
			split_value = total_value - self.prev_total_value,
			split_elapsed_sec = self.split_elapsed_sec,
		)
		self.prev_total_value = total_value
		
		self.emit()