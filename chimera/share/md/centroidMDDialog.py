from StructMeasure.Geometry import GeometryInterface

class mdCentroidDialog(GeometryInterface):
	def __init__(self, parent, status, showCB):
		GeometryInterface.__init__(self, parent, status, showCB)
		import Pmw, Tkinter
		row = 0
		parent.columnconfigure(0, weight = 1)
		parent.columnconfigure(1, weight = 1)
		parent.columnconfigure(2, weight = 1)
		self.axeButton.grid_remove()
		self.planeButton.grid_remove()
		self.centroidButton.grid_remove()
		self.centroidButton = Tkinter.Button(parent, text="Define Centroid", pady=0,
				command=self._createCentroidCB).grid(row=row,column=0)
