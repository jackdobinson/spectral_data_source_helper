

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.figure
import matplotlib.axis

class BasePlotter:
	def __init__(
			self,
			fig : None | mpl.figure.Figure = None,
			ax : None | mpl.axis.Axis = None,
	):
		if ax is not None:
			if fig is None:
				fig = ax.figure
			else:
				assert fig == ax.figure, "If providing an axis and a figure, the axis must belong to the figure."
		
		self.fig = plt.figure() if fig is None else fig
		self.ax = self.fig.add_subplot(1,1,1) if ax is None else ax
		
		self.hdls = dict()
	
	def plot(self, *args, **kwargs):
		raise NotImplementedError('Subclasses of `BasePlotter` must implement the `plot` method')
	
	def xlog(self):
		self.ax.set_xscale('log')
		return self
	
	def xlin(self):
		self.ax.set_xscale('linear')
		return self
	
	def ylog(self):
		self.ax.set_yscale('log')
		return self
	
	def ylin(self):
		self.ax.set_yscale('linear')
		return self


