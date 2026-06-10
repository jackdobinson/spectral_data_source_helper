


import numpy as np

import matplotlib as mpl
import matplotlib.figure
import matplotlib.axis


from .base import BasePlotter



class ContinuumPlotter(BasePlotter):
	def __init__(
			self,
			fig : None | mpl.figure.Figure = None,
			ax : None | mpl.axis.Axis = None,
	):
		super().__init__(fig, ax)
		
	
	def plot(
			self, 
			continuum_data : np.ndarray, 
			continuum_bin_edges : np.ndarray,
	):
	
		x = np.zeros((continuum_data.size+2,), dtype=float)
		y = np.zeros((continuum_data.size+2,), dtype=float)
		
		x[1:] = continuum_bin_edges
		x[0] = continuum_bin_edges[0]
		
		y[1:-1] = continuum_data
		
		self.hdls['continuum'] = self.ax.step(x, y, where='post', label='continuum absorption')
		
		self.ax.set_xlabel('wavenumber (cm^{-1})')
		self.ax.set_ylabel('absorption coeff (cm^{2} mol^{-1} cm^{-1})')
		
		return self
	