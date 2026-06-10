
import datetime as dt
import inspect


class TimeSplitGen:
	class_n_instances : int = 0
	
	def __init__(self, label : None | str = None):
		self.label = label if label is not None else f'TimeSplitGen instance {self.class_n_instances} at {inspect.currentframe().f_back.f_code.co_qualname}'
		self.dt_start = dt.datetime.now()
		self.dt_split_last = self.dt_start
		self._stop_flag = False
		
		self.class_n_instances += 1
	
	def __iter__(self):
		#print(f'TimeSplitGen::__iter__()')
		return self
	
	def __next__(self) -> tuple[float,float]:
		#print(f'TimeSplitGen::__next__()')
		assert not self._stop_flag, f"Stop flag has been set for TimeSplitGen '{self.label}'"
		
		dt_now = dt.datetime.now()
		result = (dt_now - self.dt_start).total_seconds(), (dt_now - self.dt_split_last).total_seconds()
		self.dt_split_last = dt_now
		return result
	
	def stop(self):
		self._stop_flag = True
