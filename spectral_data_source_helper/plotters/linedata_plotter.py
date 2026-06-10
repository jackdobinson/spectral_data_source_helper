


import numpy as np

import matplotlib as mpl
import matplotlib.figure
import matplotlib.axis


from .base import BasePlotter



class LinedataPlotter(BasePlotter):
	def __init__(
			self,
			fig : None | mpl.figure.Figure = None,
			ax : None | mpl.axis.Axis = None,
	):
		super().__init__(fig, ax)
		
	
	def plot(
			self, 
			linedata : np.ndarray, # structured array
	):
		# IN PROGRESS
	
		self.hdls['lines'] = self.ax.plot(linedata['wavenumber'], linedata['spec_line_intensity'], linestyle='none', marker='.', label='line absorption')
		
		self.ax.set_xlabel('wavenumber (cm^{-1})')
		self.ax.set_ylabel('absorption coeff (cm^{2} mol^{-1} cm^{-1})')
		
		return self
	