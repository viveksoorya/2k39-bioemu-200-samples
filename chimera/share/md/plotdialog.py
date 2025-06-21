# Glue code between Chimera and matplotlib
from chimera.baseDialog import ModelessDialog
class PlotDialog(ModelessDialog):
	"PlotDialog is a Chimera dialog whose content is a matplotlib figure"

	buttons = ('Close',)
	title = "matplotlib figure"

	def __init__(self, showToolbar=True, **kw):
		self.showToolbar = showToolbar
		ModelessDialog.__init__(self, **kw)

	def fillInUI(self, parent):
		from matplotlib.figure import Figure
		self.figure = Figure()
		from matplotlib.backends.backend_tkagg \
			import FigureCanvasTkAgg, NavigationToolbar2TkAgg
		fc = FigureCanvasTkAgg(self.figure, master=parent)
		fc.get_tk_widget().pack(side="top", fill="both", expand=True)
		self.figureCanvas = fc
		if self.showToolbar:
			nt = NavigationToolbar2TkAgg(fc, parent)
			nt.update()
			self.navToolbar = nt
		else:
			self.navToolbar = None

	def add_subplot(self, *args):
		return self.figure.add_subplot(*args)

	def delaxes(self, ax):
		self.figure.delaxes(ax)

	def draw(self):
		self.figureCanvas.draw()

	def registerPickHandler(self, func):
		self.figureCanvas.mpl_connect("pick_event", func)

if __name__ == "chimeraOpenSandbox":
	#
	# Example on how to use PlotDialog
	#
	def scatterplot(d, x, y, title):

		ax = d.add_subplot(1,1,1)
		print ax
		ax.scatter(x, y)
		#ax.set_xlim(xmin = 0.0)
		ax.set_xlabel('x-axis label')
		ax.set_ylabel('y-axis label')
		ax.set_title(title)
		ax.grid(True)
		#ax.legend(title, 'upper right' )
		d.draw()

	from numpy.random import randn
	d = PlotDialog(showToolbar=False)
	x = randn(1000)
	y = randn(1000)
	scatterplot(d, x, y, "Scatter Plot Example")
