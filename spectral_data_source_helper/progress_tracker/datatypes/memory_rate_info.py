
from typing import NamedTuple

from ...utils.si_unit import to_si_prefix_unit

class MemoryRateInfo(NamedTuple):
	n_bytes : int
	elapsed_time_sec : float

	def __str__(self) -> str:
		return to_si_prefix_unit(self.n_bytes/self.elapsed_time_sec, 'b/s')

