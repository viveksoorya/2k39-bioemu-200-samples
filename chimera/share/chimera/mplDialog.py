class MPLFrame:
	"""MPLFrame creates a matplotlib figure in a Tkinter Frame"""

	def __init__(self, parent, showToolbar=True):
		from matplotlib.figure import Figure
		self.figure = Figure()
		from matplotlib.backends.backend_tkagg \
			import FigureCanvasTkAgg, NavigationToolbar2TkAgg
		fc = FigureCanvasTkAgg(self.figure, master=parent)
		fc.get_tk_widget().pack(side="top", fill="both", expand=True)
		self.figureCanvas = fc
		if showToolbar:
			nt = NavigationToolbar2TkAgg(fc, parent)
			nt.update()
			self.navToolbar = nt
		else:
			self.navToolbar = None

	def add_subplot(self, *args, **kw):
		"Add a subplot to matplotlib figure"
		return self.figure.add_subplot(*args, **kw)

	def delaxes(self, ax):
		"Remove an axis object from matplotlib figure"
		self.figure.delaxes(ax)

	def draw(self):
		"Redraw matplotlib canvas.  Usually called after data updates."
		self.figureCanvas.draw()

	def registerPickHandler(self, func):
		"Add a matplotlib pick_event handler."
		self.figureCanvas.mpl_connect("pick_event", func)

	def mpl_connect(self, *args, **kw):
		"Add a generic matplotlib event handler."
		return self.figureCanvas.mpl_connect(*args, **kw)

	def mpl_disconnect(self, *args, **kw):
		"Remove a matplotlib event handler."
		self.figureCanvas.mpl_disconnect(*args, **kw)

from chimera.baseDialog import ModelessDialog
class MPLDialog(ModelessDialog, MPLFrame):
	"""MPLDialog is a Chimera dialog whose content is a matplotlib figure

	Some convenience methods are included so that caller does not need
	to remember which matplotlib component handles which calls.
	Callers generally create new "axis" objects via add_subplot and
	then manipulate the returned axis directly using matplotlib methods.
	"""

	buttons = ('Close',)
	title = "matplotlib figure"

	def __init__(self, showToolbar=True, **kw):
		"Initialize dialog with or without matplotlib toolbar"
		self.showToolbar = showToolbar
		ModelessDialog.__init__(self, **kw)
		# sets self.figure, self.figureCanvas, self.navToolbar
		del self.showToolbar

	def fillInUI(self, parent):
		"Chimera internal function for adding UI elements to dialog"
		MPLFrame.__init__(self, parent, self.showToolbar)

if __name__ == "chimeraOpenSandbox":
	#
	# Example on how to use MPLDialog
	#
	def scatterplot(d, x, y, label, title):
		ax = d.add_subplot(1,1,1)
		#print ax
		# When redrawing an axis with new data, instead of adding
		# a new subplot, we can (assuming we kept an ax reference):
		#ax.clear()
		ax.scatter(x, y, label=label)
		#ax.set_xlim(xmin = 0.0)
		ax.set_xlabel("x-axis label")
		ax.set_ylabel("y-axis label")
		ax.set_title(title)
		ax.grid(True)
		ax.legend()
		d.draw()

	from numpy.random import randn
	d = MPLDialog(showToolbar=False)
	x = randn(1000)
	y = randn(1000)
	scatterplot(d, x, y, "random", "Scatter Plot")
