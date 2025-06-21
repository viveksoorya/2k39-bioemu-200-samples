# --- UCSF Chimera Copyright ---
# Copyright (c) 2000-2011 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: copyright 34705 2011-10-19 23:37:43Z pett $

from prefs import prefs, MODELLER_USE_WEB, MODELLER_PATH, MODELLER_TEMP_PATH, MODELLER_KEY
from chimera import replyobj, UserError, NonChimeraError
import os

# was Apply
def model(mav, targetSeq, templateModels, numModels, preserveHetAtoms,
		preserveWater, allHydrogen, veryFast=False, loopInfo=None, tempPath="",
		executableLocation=None, customScript=None, licenseKey="", thoroughOptim=False, distRestrPath = ""):
	"""
	Function to carry on the homology modeling.
	mav             : the mav object
	targetSeq       : the target sequence, seq object
	templateModels  : the template structures, list of models
	numModels       : number of output models to generate
	preserveHetAtoms: whether to preserve HET atoms in generated models
	preserveWater   : whether to preserve water in generated models
	allHydrogen		: generate models with hydrogens?
	veryFast		: fast, crude generation of models
	loopInfo        : if not None, refine segments of template instead of remodelling
                      entire structure
	tempPath		: if not empty, where to store temporary files
	executableLocation    : if run locally, provide the Modeller binary executable file location
                      if executableLocation is None, assume run on web.
	customScript	: user's custom Modeller script
	licenseKey		: MODELLER license key
	thoroughOptim   : performs thorough optimization by adding additional lines into tail part of
					  MODELLER input file, only set to True by MDA command
	distRestrPath	: if not empty, specifies path to file with additional distance restraints				  
	"""
	from chimera import replyobj
	replyobj.info("Target seq: %s\n" % targetSeq.name)
	from chimera.misc import chimeraLabel
	replyobj.info("Template structures: \n\t"
			+ "\n\t".join([chimeraLabel(m, modelName=True) for m in templateModels]) + "\n")

	# call the homologyModeling function do the actual modeling
	if not executableLocation:
		replyobj.info("Run on web, the license key is: %s\n" % licenseKey)
		replyobj.info("Now, modeller is running on the web...\n")
		prefs[MODELLER_USE_WEB] = True
	else:
		replyobj.info("Run locally, the Modeller binary location: %s\n" % executableLocation)
		replyobj.info("Now, modeller is running locally...\n")
		prefs[MODELLER_USE_WEB] = False
		prefs[MODELLER_PATH] = executableLocation

	# Copy and rename the target sequence if it has blank space
	tempTarSeq = targetSeq.__copy__()
	tempTarSeq.name = _seqRename(targetSeq.name)

	# Construct input file map in case we are using web service
	# The main script is always called ModellerModelling.py
	inputFileMap = {}

	# for preserveHetAtoms, generate list of hetAtomsList
	if preserveHetAtoms:
		hetAtomsList = [[] for m in range(len(templateModels))]
		hetAtomsLen = 0
		for i in range(len(templateModels)):
			hetAtoms = _getHetAtoms(templateModels[i])
			hetAtomsLen += len(hetAtoms)
			for j in range(len(templateModels)):
				if j==i:
					hets = ['.']*len(hetAtoms)
					hetAtomsList[j].extend(hets)
				else:
					gaps = ['-']*len(hetAtoms)
					hetAtomsList[j].extend(gaps)
		hetAtomsList.reverse()

	# for preserveWater, generate list of watersList
	if preserveWater:
		watersList = [[] for m in range(len(templateModels))]
		watersLen = 0
		for i in range(len(templateModels)):
			waters = _getWaters(templateModels[i])
			watersLen += len(waters)
			for j in range(len(templateModels)):
				if j==i:
					hets = ['w']*len(waters)
					watersList[j].extend(hets)
				else:
					gaps = ['-']*len(waters)
					watersList[j].extend(gaps)
		watersList.reverse()

	if loopInfo:
		prefix, loopData = loopInfo
		loopIndices = set()
		for start, end in loopData:
			loopIndices.update(range(start, end+1))
		omit = []
		for mol in templateModels:
			seq = mav.associations[mol]
			mmap = seq.matchMaps[mol]
			for i in range(len(seq.ungapped())):
				if i not in mmap:
					if i not in loopIndices:
						omit.append(seq.ungapped2gapped(i))
		omit.reverse()
		for o in omit:
			for i, datum in enumerate(loopData):
				start, end = datum
				if end < o+1:
					continue
				end -= 1
				if start >= o+1:
					start -= 1
				loopData[i] = (start, end)

	# Prepare the Modeller scripts
	scriptsPath, configPath, tmpDir = writeModellerScripts(
		licenseKey, numModels, preserveHetAtoms, preserveWater, allHydrogen, veryFast,
		loopInfo, customScript, tempPath, thoroughOptim, distRestrPath)

	# Clean up the temp path, remove results from previous run
	fileList = os.listdir(tmpDir)
	prefix = "..."
	for f in fileList:
		if f == "ok_models.dat" or f == "namelist.dat" or f == "alignment.ali" :
			os.remove(os.path.join(tmpDir, f))
		elif f.endswith(".rsr"):
			prefix = f.rstrip(".rsr")
	fileList = os.listdir(tmpDir)
	for f in fileList:
		if f.startswith(prefix) or f.endswith("_fit.pdb"):
			try:
				os.remove(os.path.join(tmpDir, f))
			except (IOError, WindowsError):
				# user may be looking at the files...
				replyobj.warning("Could not remove output file from previous run: %s;"
					" continuing anyway.." % f)

	# create the template structures folder
	strucFolder = os.path.join(tmpDir, "template_struc")
	if not os.path.exists(strucFolder):
		os.makedirs(strucFolder)

	# create a namelist.dat file: first line target seq, remaining lines template seqs
	namefile = os.path.join(tmpDir, "namelist.dat")
	inputFileMap["namelist.dat"] = namefile
	fnamelist = open(namefile, 'w')
	fnamelist.write(tempTarSeq.name + '\n')
	for mol in templateModels:
		fnamelist.write(_molSaveName(mol) + '\n')
	fnamelist.close()

	configName = os.path.basename(configPath)
	inputFileMap[configName] = configPath

	# Change the seq.descript attribute according to Alignment file (PIR) format
	# (google "Alignment file (PIR)" site:salilab.org for it)
	aliSeq = []
	for mol in templateModels:
		seqMapRes = []
		seq = mav.associations[mol]
		tempSeq = _replaceGapDash(seq)
		mmap = seq.matchMaps[mol]
		tempSeq.descript = "structure:" + _molSaveName(mol)
		for i in range(len(tempSeq.ungapped())):
			if i not in mmap:
				tempSeq[seq.ungapped2gapped(i)] = "-"
			else:
				seqMapRes.append(mmap[i])
				from chimera.resCode import res3to1
				structLet = res3to1(mmap[i].type)
				if structLet != tempSeq[seq.ungapped2gapped(i)]:
					tempSeq[seq.ungapped2gapped(i)] = structLet.upper()

		# for HetAtom
		if preserveHetAtoms:
			seqMapRes += _getHetAtoms(mol)
			tempSeq.extend(hetAtomsList.pop())

		# for water 
		if preserveWater:
			seqMapRes += _getWaters(mol)
			tempSeq.extend(watersList.pop())

		tempSeq.descript += ":FIRST:@"
		tempSeq.descript += ":+" + str(len(seqMapRes))
		tempSeq.descript += ":@"
		tempSeq.descript += "::::"
		tempSeq.name = _molSaveName(mol)
		aliSeq.append(tempSeq)

		# write out the mol 
		savedResOrder = mol.residues
		seqMapRes += list(set(savedResOrder) - set(seqMapRes))
		if len(mol.residues) != len(seqMapRes):
			noDupes = []
			[noDupes.append(i) for i in seqMapRes if not noDupes.count(i)]
			seqMapRes = noDupes
		if len(mol.residues) == len(seqMapRes):
			mol.reorderResidues(seqMapRes)
		else:
			raise AssertionError("Number of residues in sequence (%d)"
				" does not equal number of residues in structure (%d)"
				% (len(seqMapRes), len(mol.residues)))
		baseName = _molSaveName(mol) + '.pdb'
		pdbFileName = os.path.join(strucFolder, baseName)
		inputFileMap[baseName] = pdbFileName
		# modified amino acids need to be written out in ATOM records
		# and have their sequence letters replaced with '.' ...
		modResidues = []
		hetResidues = []
		modResTypes = set()
		from chimera import PDBio
		for r in mol.residues:
			if r in mmap and (r.isHet or not PDBio.standardResidue(r.type)):
				modResidues.append(r)
				if r.isHet:
					hetResidues.append(r)
					r.isHet = False
				if not PDBio.standardResidue(r.type):
					modResTypes.add(r.type)
		for mr in modResidues:
			if mr in mmap:
				tempSeq[seq.ungapped2gapped(mmap[mr])] = '.'
		for resType in modResTypes:
			PDBio.addStandardResidue(resType)
		try:
			from Midas import write
			relmodel = templateModels[0]
			write(mol, relmodel, pdbFileName, temporary=True)
		finally:
			mol.reorderResidues(savedResOrder)
			for resType in modResTypes:
				PDBio.removeStandardResidue(resType)
			for r in hetResidues:
				r.isHet = True

	# Target seq
	tempTarSeq = _replaceGapDash(tempTarSeq)
	# for HetAtom
	if preserveHetAtoms and hetAtomsLen > 0:
		for i in range(hetAtomsLen): tempTarSeq.append('.')
	# for water 
	if preserveWater and watersLen > 0:
		for i in range(watersLen): tempTarSeq.append('w')
	tempTarSeq.descript = "sequence:" + tempTarSeq.name + ":.:.:.:.::::"
	aliSeq.insert(0, tempTarSeq)
	if loopInfo:
		for o in omit:
			for seq in aliSeq:
				del seq[o]

	from formatters.savePIR import save as saveali
	alignfile = os.path.join(tmpDir, 'alignment.ali')
	inputFileMap["alignment.ali"] = alignfile
	falignment = open(alignfile, 'w')
	saveali(falignment, mav, aliSeq, [])
	falignment.close()

	# Copy the (Modeller scripts, restraint file, initial models) to tmpDir
	for file in (scriptsPath,):
		if file != None and os.path.exists(file) :
			if os.path.normpath(tmpDir) != os.path.normpath(os.path.dirname(file)):
				import shutil
				shutil.copy(file, tmpDir)
				basename = os.path.basename(file)
				inputFileMap[basename] = os.path.join(tmpDir, basename)

	if executableLocation != None:
		scriptsName = os.path.basename(scriptsPath)
		RunModellerLocal(mav, templateModels, tempTarSeq.name, executableLocation,
			tmpDir, numModels, scriptsName, loopInfo)
	else:
		RunModellerWS(mav, templateModels=templateModels, numModels=numModels,
			loopInfo=loopInfo, targetSeqName=tempTarSeq.name,
			inputFileMap=inputFileMap, command=configName)

from CGLtk.Citation import Citation
class ModellerCitation(Citation):
	def __init__(self, parent):
		Citation.__init__(self, parent, "A. Sali and T. L. Blundell. \n"
			"Comparative protein modelling by satisfaction of spatial restraints.\n"
			"J. Mol. Biol. 234, 779-815, 1993.",
			prefix= "Publications using Modeller results should cite:",
			url='https://www.ncbi.nlm.nih.gov/pubmed/8254673')

def restoreRunModellerWS(mav, sesData, versioned=False):
	RunModellerWS(mav, sessionData=sesData, versionedSesData=versioned)

def writeModellerScripts(licenseKey, numModels, preserveHetAtoms, preserveWater, allHydrogen,
		veryFast, loopInfo, customScript, tempPath, thoroughOptim, distRestrPath):
	"""
	Function to prepare the Modeller scripts.
	Return tuple (pathScript, pathConfig)
	"""

	if licenseKey:
		prefs[MODELLER_KEY] = licenseKey

	# prepare the Temp path
	tmpDir = _tempPathCheck(tempPath)

	# Write out a config file
	# Remember to bump version when changing XML contents
	pathConfig = os.path.join(tmpDir, 'ModellerScriptConfig.xml')
	fconfig = open( pathConfig, 'w')
	print>>fconfig, '<?xml version="1.0" encoding="UTF-8"?>'
	print>>fconfig, '<modeller9v8>'
	print>>fconfig, '\t<key>%s</key>' % licenseKey
	print>>fconfig, '\t<version>2</version>'
	print>>fconfig, '\t<numModel>%s</numModel>' % numModels
	print>>fconfig, '\t<hetAtom>%s</hetAtom>' % int(preserveHetAtoms)
	print>>fconfig, '\t<water>%s</water>' % int(preserveWater)
	print>>fconfig, '\t<allHydrogen>%s</allHydrogen>' % int(allHydrogen)
	print>>fconfig, '\t<veryFast>%s</veryFast>' % int(veryFast)
	print>>fconfig, '\t<loopInfo>%s</loopInfo>' % repr(loopInfo)
	print>>fconfig, '</modeller9v8>'
	fconfig.close()


	# if custom script provided by user, use it
	if customScript:
		return customScript, pathConfig, tmpDir

	# if no scripts provided by user, construct the Modeller scripts

	# create the temp Modeller scripts file
	fModellerScripts = open(os.path.join(tmpDir, 'ModellerModelling.py'), 'w')

	# Head part: read ModellerScriptsHead.py and write it into ModellerModelling.py
	pkgdir = os.path.dirname(__file__)
	fModellerScriptsHead = open(os.path.join(pkgdir, 'ModellerScriptsHead.py'), 'r')
	fileContent = fModellerScriptsHead.read()
	fModellerScriptsHead.close()
	fModellerScripts.write(fileContent)

	# scripts according to settings
	codes = '\n'
	if preserveHetAtoms:
		codes += '# Read in HETATM records from template PDBs \n'
		codes += 'env.io.hetatm = True\n\n'
	if preserveWater:
		codes += '# Read in water molecules from template PDBs \n'
		codes += 'env.io.water = True\n\n'

	codes += '# create a subclass of automodel or loopmodel, MyModel.\n'
	codes += '# user can further modify the MyModel class, to override certain routine.\n'

	if allHydrogen:
		codes += 'class MyModel(allhmodel):'
	elif loopInfo:
		method_prefix, loopData = loopInfo
		resRange = ",\n".join(["\t\t\tself.residue_range(%s, %s)" % (start, end)
								for start, end in loopData])
		codes += 'class MyModel(%sloopmodel):' % method_prefix
		codes += """
	def select_loop_atoms(self):
		from modeller import selection
		return selection(
%s)
	def select_atoms(self):
		from modeller import selection
		return selection(
%s)
""" % (resRange, resRange)
	else:
		codes += 'class MyModel(automodel):'



	if distRestrPath == "":	# put in an outcommented line for special restraints
		codes += """
		def customised_function(self): pass
		#code overrides the special_restraints method

		#def special_restraints(self, aln):

		#code overrides the special_patches method.
		# e.g. to include the addtional disulfides.
		#def special_patches(self, aln):
		"""
	else:
		codes += """
		def customised_function(self): pass

		def special_restraints(self, aln):
			%s

		#code overrides the special_patches method.
		# e.g. to include the addtional disulfides.
		#def special_patches(self, aln):
		"""	% parseDistRestr(distRestrPath) # This function returns Python code for MODELLER specifying pseudoatoms and distance restraints

	if loopInfo:
		codes += """
a = MyModel(env, sequence = tarSeq,
		# alignment file with template codes and target sequence
		alnfile = 'alignment.ali',
		# name of initial PDB template
		knowns = template[0])

# one fixed model to base loops on
a.starting_model = 1
a.ending_model = 1

# %s loop models
loopRefinement = True
a.loop.starting_model = 1
a.loop.ending_model = %s
a.loop.assess_methods=(assess.DOPE, assess.GA341, assess.normalized_dope)

""" % (numModels, numModels)
	else:
		codes += """
a = MyModel(env, sequence = tarSeq,
		# alignment file with template codes and target sequence
		alnfile = 'alignment.ali',
		# PDB codes of the templates
		knowns = template)
# index of the first model
a.starting_model = 1
# index of the last model
a.ending_model = %s
loopRefinement = False

""" % numModels

	if veryFast:
		codes += '# To get an approximate model very quickly\n'
		codes += 'a.very_fast()\n\n'

	if thoroughOptim:	
		codes += """
# perform thorough optimization
a.library_schedule = autosched.normal
a.max_var_iterations = 500
a.md_level = refine.slow

		"""

	fModellerScripts.write(codes)

	# Tail part: contains the a.make and data output

 	tailfilename = 'ModellerScriptsTail.py'
	fModellerScriptsTail = open(os.path.join(pkgdir, tailfilename), 'r')
	fileContent = fModellerScriptsTail.read()
	fModellerScriptsTail.close()
	fModellerScripts.write(fileContent)

	fModellerScripts.close()
	return fModellerScripts.name, pathConfig, tmpDir

def verifyModelKw(kw):
	for key, val in kw.items():
		if key == 'licenseKey' and not val.strip():
			return False, 'Modeller license key required.  Use Help button for more info'
		for testKey, text in [('executableLocation', "Modeller executable"),
					("customScript", "custom Modeller script")]:
			if key == testKey and not os.path.exists(val) and (
					key == "executableLocation" or val):
				return False, "Specified %s location does not exist" % text
	return True, ""

class RunModeller:
	# This is actually an abstract base class.
	# Derived class needs to run Modeller and call _parseOKModels

	def __init__(self, mav, templateModels, numModels, loopInfo, targetSeqName):
		self.mav = mav
		self.templateModels = templateModels
		self.numModels = numModels
		self.loopInfo = loopInfo
		self.targetSeqName = targetSeqName

	def _progressEstimate(self, fileList):
		"""
		Based on the output files, estimate the progress of the modeling.
		"""
		prefix = "..."
		count = 1.0
		fileTotal = float(int(self.numModels) + 2.0)
		for f in fileList:
			if f.endswith(".ini"):
				prefix = f.rstrip(".ini")
			elif f == "ok_models.dat":
				return 1.0

		if prefix == "...": return 0.0

		for f in fileList:
			if f.startswith(prefix) and f.endswith(".pdb") and not f.endswith("_fit.pdb"):
				if self.loopInfo and ".BL" not in f:
					continue
				count+=1.0

		return count / fileTotal

	def _parseOKModels(self, lines, stdoutLines, openModel):
		headers = [h.strip() for h in lines[0].split("\t")][1:]
		for i, hdr in enumerate(headers):
			if hdr.endswith(" score"):
				headers[i] = hdr[:-6]
		models = []
		if not self.loopInfo:
			prevMavAutoAssociate = self.mav.autoAssociate
			self.mav.autoAssociate = True
		kw = {'temporary': True}
		from ModBase.gui import assignModbaseInfo, ModBaseDialog
		from ModBase.prefs import col2pdb
		for i, line in enumerate(lines[1:]):
			fields = line.strip().split()
			pdb, scores = fields[0], [float(f) for f in fields[1:]]
			kw['subid'] = i+1
			kw['identifyAs'] = "%s model %d" % (self.targetSeqName, i+1)
			model = openModel(pdb, **kw)
			kw['baseId'] = model.id
			models.append(model)
			info = {}
			for hdr, score in zip(headers, scores):
				hdr = col2pdb.get(hdr, hdr)
				info[hdr] = score
			assignModbaseInfo(model, info)
		if self.templateModels:
			# structural alignment with the first target structure
			from MatchMaker import match, CP_SPECIFIC_SPECIFIC, defaults, \
				MATRIX, SEQUENCE_ALGORITHM, GAP_OPEN, GAP_EXTEND, ITER_CUTOFF
			ref = self.templateModels[0]
			mseq = self.mav.associations[ref].matchMaps[ref]['mseq']
			if len(mseq) > len(mseq.residues):
				from copy import copy
				mseq = copy(mseq)
				mseq[:] = mseq.ungapped()
			for model in models:
				pairings = []
				for seq in model.sequences():
					if len(seq.chainID) > 1:
						continue
					pairings.append((mseq, seq))
				match(CP_SPECIFIC_SPECIFIC, pairings, defaults[MATRIX],
					defaults[SEQUENCE_ALGORITHM], defaults[GAP_OPEN],
					defaults[GAP_EXTEND], iterate=defaults[ITER_CUTOFF])
		from StringIO import StringIO
		alignment = StringIO()
		from formatters import savePIR
		savePIR.save(alignment, self.mav, self.mav.seqs,
						self.mav.fileMarkups)
		mbd = ModBaseDialog(None, models, alignment=alignment.getvalue())
		alignment.close()
		for hdr in headers:
			if hdr in col2pdb:
				continue
			mbd.addScoreColumn(hdr)
		mbd.hideEmptyColumns()
		numOK = numFailed = 0
		state = None
		for line in stdoutLines:
			if line.startswith(">> "):
				if line[3:] == "Summary of successfully produced loop models:":
					state = "success"
				elif line[3:] == "Summary of failed loop models:":
					state = "failure"
				else:
					state = None
			elif state == "success":
				if ".pdb" in line:
					numOK += 1
			elif state == "failure":
				if ".pdb" in line:
					numFailed += 1
		if numFailed:
			from chimera import replyobj
			replyobj.warning("Modeller failed to generate %d of %d models.\n"
					"Showing the %s successful models.\n" % (numFailed, numFailed+numOK, numOK))
		# allow models to associate to alignment (e.g. Sequence inspector) and show RMSD
		if models:
			from chimera.update import checkForChanges
			checkForChanges()
			if self.loopInfo:
				aseq = self.mav.associations[self.templateModels[0]]
				for model in models:
					self.mav.associate(model.sequences()[0], seq=aseq)
			self.mav.showHeaders([h for h in self.mav.headers() if h.name == "RMSD"])

		if not self.loopInfo:
			self.mav.autoAssociate = prevMavAutoAssociate
		return models

class RunModellerLocal(RunModeller):

	def __init__(self, mav, templateModels, targetSeqName, executableLocation, tmpDir,
			numModels, scriptsName, loopInfo):
		# Run Modeller locally in the tmpDir
		RunModeller.__init__(self, mav, templateModels, numModels, loopInfo, targetSeqName)
		self.pathTemp = tmpDir
		self.mav.status("Running Modeller locally")
		import os, sys
		cmd = [executableLocation, os.path.join(tmpDir, scriptsName)]
		if sys.platform == 'win32':
			# need to set some environment variables
			environ = {}
			environ.update(os.environ)
			binDir, exe = os.path.split(executableLocation)
			while True:
				head, tail = os.path.split(binDir)
				if not head:
					raise UserError("Expect MODELLER executable to be located"
						" under a folder whose name begins with 'Modeller' or"
						" 'modeller' (the MODELLER home folder).  The"
						" executable specified (%s) does not.  If you feel"
						" this requirement is a bug, use 'Report A Bug'"
						" in the Help menu to report it." % executableLocation)
				elif tail.startswith("Modeller") or tail.startswith("modeller"):
					home = binDir
					break
				binDir = head
			if not exe.startswith("mod") or not exe.endswith(".exe"):
				raise UserError("Expect MODELLER executable name to start"
					" with 'mod' and end with '.exe'.  The executable"
					" specified (%s) does not.  If you feel this"
					" requirement is a bug, use 'Report A Bug'"
					" in the Help menu to report it." % executableLocation)
			version = exe[3:-4]
			if 'v' not in version and version.count('.') == 1:
				version = version.replace('.', 'v')
			environ['VERSION'] = version
			environ['KEY_MODELLER' + version] = prefs[MODELLER_KEY]
			environ['DIR'] = home
			environ['MODINSTALL' + version] = home
			environ['PYTHONPATH'] = os.path.join(home, 'modlib')
			environ['LIB_ASGL'] = os.path.join(home, 'asgl')
			environ['BIN_ASGL'] = binDir
			environ['PATH'] = binDir + ';' + environ.get('PATH', '')
		else:
			environ = None
		oldDir = os.getcwd()
		os.chdir(tmpDir)
		from chimera import SubprocessMonitor as SM
		from chimera.tasks import Task
		self.task = Task("Running Modeller for %s locally" % targetSeqName, None)
		self.task.updateStatus("Running Modeller locally")
		try:
			self.subproc = SM.Popen(cmd, stdin=None, stdout=SM.PIPE,
						stderr=SM.PIPE, daemon=True, env=environ,
						progressCB = self._progressCBLocal)
		except OSError, e:
			raise UserError("Unable run Modeller: %s" %e)
		finally:
			os.chdir(oldDir)
		subprog = SM.monitor('progress ',
					self.subproc, title="Comparative (Homology) Modeling",
					task=self.task,
					afterCB=self._collectResultsCB )
		self.mav._addRunModellerLocal(self)

	def _progressCBLocal(self, inProgress):
		"""
		Based on the output files, estimate the progress of the modeling.
		"""
		if inProgress:
			fileList = os.listdir(self.pathTemp)
			return RunModeller._progressEstimate(self, fileList)
		else:
			return 0.0

	def _collectResultsCB(self, aborted):
		"""
		Call back funcion of SM.monitor
		"""
		if aborted:
			self.task.finished()
			self.mav.status("Modeller job canceled\n", log=True)
		else:
			info = replyobj.info
			info("MODELLER process output\n")
			info("-----------------------\n")
			for line in self.subproc.stdout:
				info(line)
			info("-----------------------\n")
			info("MODELLER process errors\n")
			info("-----------------------\n")
			for line in self.subproc.stderr:
				info(line)
			info("-----------------------\n")
			if not self._showingOKmodels(self.pathTemp):
				self.task.finished()
				raise NonChimeraError("Running Modeller failed; see reply log")
			self.mav.status("Done running Modeller; showing results")
			self.task.finished()
		self.mav._removeRunModellerLocal(self)
		return

	def _showingOKmodels(self, outputPath):
		"""
		Function: read in the file ok_models.dat in the outputPath and show
		the result models in the ModBase dialog
		"""
		from OpenSave import osOpen
		okModelsPath = os.path.join(outputPath, "ok_models.dat")
		if not os.path.exists(okModelsPath):
			return False
		modelsInfoFile = osOpen(okModelsPath)
		lines = modelsInfoFile.readlines()
		modelsInfoFile.close()
		def openModel(pdb, outputPath=outputPath, **kw):
			from chimera import openModels
			return openModels.open(os.path.join(outputPath, pdb), **kw)[0]
		possibleInfoNames = ["stdout.txt", "ModellerModelling.log"]
		for infoName in possibleInfoNames:
			infoPath = os.path.join(outputPath, infoName)
			if os.path.exists(infoPath):
				break
		else:
			raise AssertionError("Cannot find file with informational Modeller output\n"
				"(%s)" % " or ".join(possibleInfoNames))
		stdout = osOpen(infoPath)
		stdoutLines = stdout.readlines()
		stdout.close()
		self._parseOKModels(lines, stdoutLines, openModel)
		return True

	def terminate(self):
		self.task.cancel()

class RunModellerWS(RunModeller):

	def __init__(self, mav, templateModels=None, numModels=5, loopInfo=None,
				targetSeqName=None, inputFileMap=None, command=None, sessionData=None,
				versionedSesData=False):
		if sessionData:
			targetSeqName = "target" # default for old versions
			if versionedSesData:
				if sessionData[0] == 1:
					version, inputFileMap, loopInfo, sessionData = sessionData
				else:
					version, inputFileMap, loopInfo, targetSeqName, sessionData = sessionData
		self.inputFileMap = inputFileMap
		from WebServices import appWebService
		serviceName = "modeller"
		RunModeller.__init__(self, mav, templateModels, numModels, loopInfo, targetSeqName)
		kw = dict()
		kw["finishTest"] = "ok_models.dat"
		kw["progressCB"] = self._progressCBWeb
		kw["cleanupCB"] = self._jobFinished
		kw['backend'] = "cx"
		if sessionData:
			kw["sessionData"] = sessionData
		else:
			kw["params"] = (serviceName, targetSeqName, self.inputFileMap, command)
			self.mav.status("Running Modeller web service")
		self.ws = appWebService.AppWebService(self._wsFinish, **kw)
		self.mav._addRunModellerWS(self)

	def _jobFinished(self, backend, completed, success):
		if not completed:
			self.mav.status("Modeller job canceled\n", log=True)
			if not success:
				self.mav._removeRunModellerWS(self)

	def _progressCBWeb(self, stdout):
		if stdout:
			if not self.inputFileMap:
				return 1.0
			fpath = os.path.join(os.path.dirname(self.inputFileMap["alignment.ali"]),
					'stdout.txt')
			file = open(fpath, 'w')
			file.write(stdout)
			file.close()
			count = 1.0
			total = float(int(self.numModels) + 2.0)
			if self.loopInfo:
				prevOpen = False
				for line in stdout.split('\n'):
					if line.startswith("openf") and ".BL" in line and "_fit.pdb" not in line:
						prevOpen = True
						continue
					if prevOpen and line.startswith("wrpdb"):
						count += 1.0
					prevOpen = False
			else:
				for line in stdout.split('\n'):
					if line.startswith(
							'# Heavy relative violation of each residue is written to:'):
						count += 1.0
			return count / total
		else:
			return 0.0

	def _wsFinish(self, opal, fileMap):
		data = opal.getURLContent(fileMap["ok_models.dat"])
		lines = data.strip().split('\n')
		def openModel(pdb, opal=opal, fileMap=fileMap, **kw):
			from cStringIO import StringIO
			f = StringIO(opal.getURLContent(fileMap[pdb]))
			from chimera import openModels
			return openModels.open(f, type="PDB", **kw)[0]
		data = opal.getURLContent(fileMap["stdout.txt"])
		stdoutLines = data.strip().split('\n')
		self._parseOKModels(lines, stdoutLines, openModel)
		self.mav._removeRunModellerWS(self)

	def sessionData(self):
		return (1, self.inputFileMap, self.loopInfo, self.ws.sessionData())

	def terminate(self):
		self.ws.task.cancel()

# was _countHetAtom
def _getHetAtoms(mol):
	"""
	# count hetAtoms in mol, return a list of non-water residues
	"""
	chainHets = set()
	for seq in mol.sequences():
		# all-het chains may be desirable to preserve, so don't skip those
		existing = [r for r in seq.residues if r]
		if len(existing) != len([r for r in existing if r.isHet]):
			chainHets.update(existing)
	hetAtoms = []
	for res in mol.residues:
		if res.isHet and res.type not in ['HOH', 'MSE', 'ACE', 'NME'] and res not in chainHets:
			hetAtoms.append(res)
	return hetAtoms

# was _countWater
def _getWaters(mol):
	"""
	# count water in mol, return a list of water residues
	"""
	waters = []
	for res in mol.residues:
		if res.type == 'HOH':
			waters.append(res)
	return waters

def _molSaveName(mol): # give the molecules new names with info of their subids
	"""return mol.name.replace(':','_') + '_%d' % mol.subid"""
	return mol.name.replace(':','_').replace(' ', '_') + '_%d_%d' % (mol.id, mol.subid)

def _replaceGapDash(seq): #replace the non-alpha char in a seq with dash
	cs = seq.__copy__()
	modseq = [] # replace the gap "." with "-"
	for let in seq:
		if let.isalpha():
			modseq.append(let.upper())
		else:
			modseq.append("-")
	cs[:] = modseq
	return cs

def _seqRename(name): # Rename a seq to match Modeller's requirement
	mappedName = list()
	for c in name:
		if c.isalnum():
			mappedName.append(c)
		else:
			mappedName.append('_')
	return ''.join(mappedName[:16])

_tempPath = None
# was _pathTempCheck
def _tempPathCheck(tempPath):
	"""
	check the existance of the temp dir. if it doese not exist, create one.
	"""
	global _tempPath
	if _tempPath == None: # first time using
		if os.path.exists(tempPath) :
			_tempPath = tempPath
		else:
			_tempPath = _tempPathCreate()
	else : # not first time using
		if _tempPath != tempPath:
			_tempPath = tempPath
		if _tempPath == "" or not os.path.exists(_tempPath):
			_tempPath = _tempPathCreate()

	if os.path.exists(tempPath) or tempPath == "" : # save the customised temp path
		prefs[MODELLER_TEMP_PATH] = tempPath
	return _tempPath

# was _pathTempCreate
def _tempPathCreate():
	"""
	create a temp dir, which will be removed after closing Chimera
	"""
	from OpenSave import osTemporaryFile
	tempFile = osTemporaryFile(suffix=".tmp")
	tempDir = os.path.dirname(tempFile)
	os.remove(tempFile)
	return tempDir


def parseDistRestr(filename):
	"""
	Parses the distance restraints file specified by user and returns code that needs 
	to be injected into the "special_restraints" method of the Modeller input script.
	The distance restraints file needs four space-seperated numbers on each line.
	Format: res1 res2 dist stdev
	res1 and res2 can be residue ranges (e.g. res1 = 123-789), in which case atoms
	pseudoatom will be created by Modeller.
	"""

	# this function will check whether a reidue number is valid
	def verifyResidue(value):		
		try:
			res = int(value)
		except ValueError:
			raise UserError('The residue nr. %s specified in the additional distance restraints file is not an integer.' % value)
		if res <= 0:	
			raise UserError('The residue nr. %d specified in the additional distance restraints file needs to be bigger than 0.' % res)
		return res	


	# check whether the specified path is a file:
	from os.path import isfile
	if not isfile(filename):
		raise UserError('The user-specified additional distance restraints file "%s" does not exist.' % filename) 

	# initialize code that will be returned:
	headcode = """
				rsr = self.restraints
				atm = self.atoms
"""
	maincode = ""


	# parse file:
	from OpenSave import osOpen
	distrestrfile = osOpen(filename, 'r')
	i = 0 # number of pseudoatoms
	pseudodict = {} # to avoid having duplicate pseudoatoms
	for line in distrestrfile:
		
		values = line.split()
		
		#check whether we have four values in that line:
		if len(values) != 4:
			raise UserError('The line %s specified in the additional distance restraints file has less or more than the required four space-seperated values.' % line)
		
		# check whether dist and stdev are ok:	
		try:
			dist = float(values[2])
		except ValueError:
			raise UserError('The distance %s specified in the additional distance restraints file is not a real number.' % values[2])
		if dist <= 0:	
			raise UserError('The distance %f specified in the additional distance restraints file needs to be bigger than 0.' % dist)
		try:	
			stdev = float(values[3])	
		except ValueError:
			raise UserError('The standard deviation %s specified in the additional distance restraints file is not a real number.' % values[3])
		if stdev <= 0:	
			raise UserError('The standard deviation %f specified in the additional distance restraints file needs to be bigger than 0.' % stdev)	
		
		# check whether residue ranges or single residues where specified:
		# for 1st atom:	
		if '-' in values[0]: # looks like a residue range was specified -> verify
			resrange = values[0].split('-')
			if len(resrange) != 2:
				raise UserError('The residue range %s specified in the additional distance restraints file is not valid.' % resrange)
			resA = verifyResidue(resrange[0])
			resB = verifyResidue(resrange[1])
			if (resA, resB) not in pseudodict:
				i += 1
				atom1 = 'pseudo' + str(i)
				# add to dict:
				pseudodict[(resA, resB)] = atom1
				# add pseudoatoms to output code:
				headcode +=	"""
				%s = pseudo_atom.gravity_center(self.residue_range('%d:','%d:'))
				rsr.pseudo_atoms.append(%s)
""" % (atom1, resA, resB, atom1)
			else:
				atom1 = pseudodict[(resA, resB)]
		else: # hopefully, a single residue was specified -> verify	
			res1 = verifyResidue(values[0])
			atom1 = "atm['CA:" + str(res1) +"']"	
		# for 2nd atom:		
		if '-' in values[1]: # looks like a residue range was specified -> verify
			resrange = values[1].split('-')
			if len(resrange) != 2:
				raise UserError('The residue range %s specified in the additional distance restraints file is not valid.' % resrange)
			resA = verifyResidue(resrange[0])
			resB = verifyResidue(resrange[1])
			if (resA, resB) not in pseudodict:
				i += 1
				atom2 = 'pseudo' + str(i)
				# add to dict:
				pseudodict[(resA, resB)] = atom2
				# add pseudoatoms to output code:
				headcode +=	"""
				%s = pseudo_atom.gravity_center(self.residue_range('%d:','%d:'))
				rsr.pseudo_atoms.append(%s)
""" % (atom2, resA, resB, atom2)
			else:
				atom2 = pseudodict[(resA, resB)]
		else: # hopefully, a single residue was specified -> verify		
			res2 = verifyResidue(values[1])
			atom2 = "atm['CA:" + str(res2) +"']"	

		# add restraints line to output
		maincode += """
				rsr.add(forms.gaussian(group=physical.xy_distance, feature=features.distance(%s,%s), mean=%f, stdev=%f))
""" % (atom1, atom2, dist, stdev)


	# compile and return output code:
	return headcode + maincode


