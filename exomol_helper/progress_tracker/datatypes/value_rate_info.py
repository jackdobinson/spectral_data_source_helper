
from typing import NamedTuple

from ...utils.si_unit import to_si_prefix_unit
from ...utils.time import elapsed_time_str

class ValueRateInfo(NamedTuple):
	unit : str
	total_value : float
	total_elapsed_time_sec : float
	split_value : float
	split_elapsed_time_sec : float

	def __str__(self) -> str:
		total_per_sec_str = to_si_prefix_unit(self.total_value/self.total_elapsed_time_sec, f'{self.unit}/s')
		split_per_sec_str = to_si_prefix_unit(self.split_value/self.split_elapsed_time_sec, f'{self.unit}/s')
		
		return f'Total rate {total_per_sec_str} :: Elapsed time {elapsed_time_str(self.total_elapsed_time_sec)} :: Split rate {split_per_sec_str} :: Split time {elapsed_time_str(self.split_elapsed_time_sec)}'

