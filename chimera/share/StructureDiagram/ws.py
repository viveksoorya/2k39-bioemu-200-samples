class CDKDepictionService:

	service = "CDKDepictionService"
	output = "depiction.png"

	def __init__(self, finishCB=None, failCB=None,
			width=200, height=200,
			smiles=None, molecules=None, background=True):
		# "molecule" can be either a single chimera.Molecule
		# or a list of them.  If single, the returned data
		# is an image file; otherwise, the returned data
		# is a zip file whose entries are named depiction-%d.png,
		# where %d corresponds to the index of the molecule in
		# the list.
		if not smiles and not molecules:
			raise ValueError("No input specified")
		if smiles and molecules:
			raise ValueError("Only one input may be specified")
		self.argList, self.kwArgs = self._constructArgs(width,
							height, smiles,
							molecules)
		from WebServices.opal_client import OpalService
		self.opal = OpalService(self.service)
		self.finishCB = finishCB
		self.failCB = failCB
		if background:
			self._runAsTask()
		else:
			self._run()

	def _constructArgs(self, width, height, smiles, molecules):
		argList = "-w %d -h %d -o %s" % (width, height, self.output)
		kwArgs = dict()
		if smiles:
			argList += " -s %s" % smiles
		else:
			from WebServices.opal_client import makeInputFileWithContents
			contents, isSingle = makeMol2(molecules)
			name = "input.mol2"
			mol2File = makeInputFileWithContents(name, contents)
			if isSingle:
				argList += " -m %s" % name
			else:
				argList += " -M %s" % name
			kwArgs["_inputFile"] = [ mol2File ]
		return argList, kwArgs

	def _run(self):
		code, self.fileMap = self.opal.launchJobBlocking(self.argList,
								**self.kwArgs)
		self._finish()

	def _runAsTask(self):
		self.opal.launchJob(self.argList, **self.kwArgs)
		from chimera.tasks import Task
		self.task = Task("Structure Diagram", self._cancelCB,
							self._statusCB)

	def _cancelCB(self):
		self.task.finished()
		self.task = None

	def _statusCB(self):
		self.task.updateStatus(self.opal.currentStatus())
		if not self.opal.isFinished():
			self.opal.queryStatus()
			return
		self.task.finished()
		self.task = None
		self.fileMap = self.opal.getOutputs()
		self._finish()

	def _finish(self):
		if self.opal.isFinished() < 0:
			if self.failCB:
				self.failCB()
				return
			self.showErrors()
			from chimera import replyobj
			replyobj.error("Structure diagram generation failed; "
					"see Reply Log for more information\n")
			return
		self.data = self.opal.getURLContent(self.fileMap[self.output])
		if self.finishCB:
			self.finishCB(self.data)

	def showErrors(self):
		from chimera import replyobj
		self.opal.showURLContent("%s stderr" % self.service,
					self.fileMap["stderr.txt"])
		self.opal.showURLContent("%s stdout" % self.service,
					self.fileMap["stdout.txt"])

def makeMol2(mList):
	from chimera import Molecule
	if isinstance(mList, Molecule):
		mList = [ mList ]
		isSingle = True
	else:
		isSingle = False
	from StringIO import StringIO
	from WriteMol2 import writeMol2
	mol2 = StringIO()
	writeMol2(mList, mol2, temporary=True)
	return mol2.getvalue(), isSingle
