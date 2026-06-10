
from typing import Any

class ModuleVar:
	def __init__(self, value : Any):
		self.value = value
	def set(self, v):
		self.value = v
	def get(self) -> Any:
		return self.value