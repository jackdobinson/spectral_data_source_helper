
from typing import NamedTuple

from .memory_rate_info import MemoryRateInfo
from ...utils.time import elapsed_time_str
from ...utils.si_unit import to_si_numeric_unit

class ChunkRateInfo(NamedTuple):
	source_name : str
	element_name : str
	total_elements : int
	rolling_elements : int
	total_memory_rate : MemoryRateInfo
	rolling_memory_rate : MemoryRateInfo
	
	def __str__(self) -> str:
		return f'[{self.source_name}] {self.element_name}: Number {self.total_elements} Avg rate {to_si_numeric_unit(self.total_elements/self.total_memory_rate.elapsed_time_sec, f"/s")} Split rate {to_si_numeric_unit(self.rolling_elements/self.rolling_memory_rate.elapsed_time_sec, f"/s")} :: Mem rate: Avg {self.total_memory_rate!s} Split {self.rolling_memory_rate!s} :: Time: Elapsed {elapsed_time_str(self.total_memory_rate.elapsed_time_sec)} Split {elapsed_time_str(self.rolling_memory_rate.elapsed_time_sec)}'
