# -----------------------------------------------------------------------------
#
def show_saxs_profile(molecules, selected_only, epath, expath, AdvOpt,
						expDup = False,
						legendLabel = [], tempFolder = None, dialog = None):

	import os
	
	#Temp folder location
	if os.path.exists(tempFolder):
		tpath = tempFolder
	else:
		from OpenSave import osTemporaryFile
		tempFile = osTemporaryFile(suffix=".tmp")
		tpath = os.path.dirname(tempFile)
		os.remove(tempFile)
	

	if len(molecules) <= 3:
		name = '+'.join([m.name for m in molecules])
	else:
		name = '%d models' % len(molecules)
	name = name.replace('.pdb','').replace('.PDB','')
	fname = name.replace(' ','_').replace('+','_')

	pdbpath = write_pdb(molecules, selected_only, os.path.join(tpath, fname+'.pdb'))

	if expath and not expDup:
		from os.path import basename
		legendLabel.append('Experimental: %s' %basename(expath))

	if not epath:
		# Use web services if no executable is given
		if dialog is None:
			dialog = PlotDialog()
		ProfileOpalService(pdbpath, expath, expDup, name, legendLabel, dialog.figure, AdvOpt) 
	else:
		cmd = '%s %s %s %s' % (epath, AdvOpt, pdbpath, expath)
		from chimera.replyobj import info, warning
		info('Executing command: %s\n' % cmd)
		status = os.system(cmd)
		if status != 0:
			warning('Error %d executing command "%s"' % (status, cmd))
			return dialog
		if expath:
			from os.path import basename
			ppath = pdbpath[:-4] + '_' + basename(expath)
			if expDup:
				p = read_profile(ppath, 3, dropExp = True)
			else:
				p = read_profile(ppath, 3)
		else:
			ppath = pdbpath + '.dat'
			p = read_profile(ppath, 2)
		if dialog is None:
			dialog = PlotDialog()
		chi = chiValue(ppath)
		plot_profile(p, name, legendLabel, chi = chi, fig=dialog.figure)
	return dialog

# -----------------------------------------------------------------------------
#
def write_pdb(molecules, selected_only, pdbpath):

	#import tempfile, os
	#fd, pdbpath = tempfile.mkstemp(suffix = '.pdb')
	#os.close(fd)
	import Midas

	# Profile calculation only uses first model in PDB file. So combine
	# models into a single model.
	if len(molecules) == 1:
		Midas.write(molecules, molecules[0], pdbpath, selOnly = selected_only)
	else:
		from Combine import combine
		atomMap, combined = combine(molecules, molecules[0], returnMapping = True)
		if selected_only:
			# Delete non-selected atoms from combined model.
			from chimera import selection
			satoms = selection.currentAtoms(asDict = True)
			datoms = [ac for a, ac in atomMap.items() if not a in satoms]
			import Midas
			Midas.deleteAtomsBonds(datoms)
		Midas.write(combined, None, pdbpath)

	return pdbpath

# -----------------------------------------------------------------------------
#
class ProfileOpalService:

	def __init__(self, pdbpath, expath, expDup, name, legendLabel, fig, AdvOpt):
		from WebServices.opal_client import OpalService
		from WebServices.opal_client import makeInputFile
		self.pdbpath = pdbpath
		self.expath = expath
		self.expDup = expDup
		self.name = name
		self.legendLabel = legendLabel
		self.figure = fig
		self.AdvOpt = AdvOpt
		self.chi = 0.0

		self.fname = self.name.replace(' ','_').replace('+','_')

		argList = AdvOpt

		files = [ makeInputFile(pdbpath, name="pdbfile") ]
		argList += "pdbfile"
		if expath:
			exFile = makeInputFile(expath, name="exfile")
			files.append(exFile)
			argList += " exfile"
		
		try:
			self.opal = OpalService("SAXS2Service")
		except:
			import traceback, sys
			print "Traceback from SAXS request:"
			traceback.print_exc(file=sys.stdout)
			print """
Typically, if you get a TypeError, it's a problem on the remote server
and it should be fixed shortly. If you get a different error or
get TypeError consistently for more than a day, please report the
problem using the Report a Bug... entry in the Help menu. Please
include the traceback printed above as part of the problem description."""
			from chimera import NonChimeraError
			raise NonChimeraError("SAXS web service appears "
						"to be down. See Reply Log "
						"for more details.")

		self.opal.launchJob(argList, _inputFile=files)
		from chimera.tasks import Task
		self.task = Task("SAXS " + self.name, self.cancelCB, self.statusCB)
		
	def cancelCB(self):
		self.task.finished()
		self.task = None

	def statusCB(self):
		self.task.updateStatus(self.opal.currentStatus())
		if not self.opal.isFinished():
			self.opal.queryStatus()
			return
		self.task.finished()
		self.task = None
		self.filemap = self.opal.getOutputs()
		if self.opal.isFinished() > 0:
			# Successful completion
			self.showFileContent("stdout.txt")
			self.finished()
		else:
			# Failed
			from chimera import replyobj
			replyobj.error("SAXS %s failed; see Reply Log for more information"
					% self.name)
			self.showFileContent("stdout.txt")
			self.showFileContent("stderr.txt")

	def finished(self):
		import shutil, os.path
		if self.expath:
			data = self.getFileContent("pdbfile_exfile.dat")
			if self.expDup: 
				p = read_profile_data(data, 3, dropExp = True)
			else: 
				p = read_profile_data(data, 3)
			self.chi = self.chiValue("stdout.txt")	
			#print self.expath
			#print self.pdbpath
			if os.path.normpath( os.path.dirname(self.expath) ) != \
					os.path.normpath( os.path.dirname(self.pdbpath) ):
				shutil.copy(self.expath, os.path.dirname(self.pdbpath))
			self.copyURLfile("pdbfile_exfile.dat",
					os.path.join(os.path.dirname(self.pdbpath), self.fname + "_saxs.dat" ))
		else:
			data = self.getFileContent("pdbfile.dat")
			p = read_profile_data(data, 2)
			self.copyURLfile("pdbfile.dat",
					os.path.join(os.path.dirname(self.pdbpath), self.fname + "_saxs.dat" ))
		# copy the output file into the tmp path
		self.copyURLfile("stdout.txt",
				os.path.join(os.path.dirname(self.pdbpath), self.fname + "_stdout.txt" ))
		self.copyURLfile("stderr.txt",
				os.path.join(os.path.dirname(self.pdbpath), self.fname + "_stderr.txt" ))
		# plot the figure
		self.figure = plot_profile(p, self.name, self.legendLabel, chi=self.chi, fig=self.figure)

	def getURLContent(self, url):
		import urllib2
		f = urllib2.urlopen(url)
		data = f.read()
		f.close()
		return data
	
	def copyURLfile(self, filename, path):
		data = self.getFileContent(filename)
		f = open( path, 'w')
		f.write(data)
		f.close()
		return
		

	def getFileContent(self, filename):
		return self.getURLContent(self.filemap[filename])

	def showURLContent(self, title, url):
		from chimera import replyobj
		data = self.getURLContent(url)
		replyobj.message("%s\n-----\n%s-----\n" % (title, data))

	def showFileContent(self, filename):
		try:
			url = self.filemap[filename]
		except KeyError:
			from chimera import replyobj
			replyobj.message("SAXS profile: there is no file named \"%s\"" % filename)
		else:
			self.showURLContent("SAXS profile %s" % filename, url)

	def chiValue(self, filename): # return the Chi value 
		output = self.getFileContent(filename)
		return FindChiValue(output)	


# -----------------------------------------------------------------------------
#
def read_profile(path, columns, dropExp = False):
	p = open(path, 'r')
	data = p.read()
	p.close()
	return read_profile_data(data, columns, dropExp = dropExp)

# -----------------------------------------------------------------------------
#
def read_profile_data(data, columns, dropExp = False):
	lines = data.splitlines()
	values = []
	for line in lines:
		if line[0] != '#':
			v = [ float(x) for x in line.split() ]
			if columns == 3 and dropExp:
				values.append( tuple( [v[0], v[2]] ) )
			else:
				values.append( tuple( v[:columns] ) )
	return values


# -----------------------------------------------------------------------------
#
def chiValue(path): # return the Chi value 
	f = open(path, 'r')
	s = f.readline()
	s += f.readline()
	f.close()
	return FindChiValue(s)

def FindChiValue(s):
	import re
	match = re.search(r'(Chi\s*=[\ \t]*)([-+]?([0-9]*\.[0-9]+|[0-9]+))', s)
	if match:
		return float(match.group(2))
	else:	
		return 0.0

		
# -----------------------------------------------------------------------------
#
def plot_profile(p, name, legendLabel, chi = 0.0, fig = None):

	if fig is None:
		d = PlotDialog()
		fig = d.figure
	ax = fig.add_subplot(1,1,1)
	q = [qi[0] for qi in p]
	i = [qi[1] for qi in p]
	if len(p[0]) == 3:
		e = i
		i = [qi[2] for qi in p]
		ax.semilogy(q, e, '+')
	proLine = ax.semilogy(q, i, linewidth=1.0)
	ax.set_xlim(xmin = 0.0)
	ax.set_xlabel('q [$\AA^{-1}$]')
	ax.set_ylabel('I(q) log-scale')
	ax.set_title('Small-angle X-ray scattering profile')
	ax.grid(True)
	legendLabel.append('FoXS: %s' %name)
	if chi != 0.0:
		legendLabel[-1] += " ($\chi$ = %.3f)" %(chi)
	ax.legend(tuple(legendLabel), loc=0)
	fig.canvas.draw()
	return fig

# -----------------------------------------------------------------------------
#
from chimera.baseDialog import ModelessDialog
class PlotDialog(ModelessDialog):

	title = "SAXS Profile"
	help = 'ContributedSoftware/saxs/saxs.html'

	def fillInUI(self, parent):
		from matplotlib.figure import Figure
		self.figure = Figure()
		from matplotlib.backends.backend_tkagg \
			import FigureCanvasTkAgg, NavigationToolbar2TkAgg
		fc = FigureCanvasTkAgg(self.figure, master=parent)
		fc.get_tk_widget().pack(side="top", fill="both", expand=True)
		nt = NavigationToolbar2TkAgg(fc, parent)
		nt.update()

# -----------------------------------------------------------------------------

