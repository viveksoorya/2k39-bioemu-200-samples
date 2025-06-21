###################################################################################################
#
# MULTI DOMAIN ASSEMBLER for Chimera v1.10 and up
# by Sam Hertig, samuel.hertig@ucsf.edu
#
# Scroll down to the functions "mda" and "main" to get an idea of how the code works.
#
###################################################################################################


def OpenReplyLog():
	from chimera import dialogs, tkgui
	dialogs.display(tkgui._ReplyDialog.name)

def getUniprotID(pdbid, chain):
	from chimera.fetch import default_fetch_directory
	dbpath = default_fetch_directory()
	from os.path import expanduser, join
	dbpath = expanduser(dbpath)
	filename = join(dbpath, 'MDA', 'MDA_uniprot')
	import shelve 
	from SeqAnnotations import uniprotIDs as uIDs
	shelf = shelve.open(filename, 'c')
	key = pdbid + chain
	try:
		uniprotids = shelf[key]
	except KeyError:
		try:
			uniprotids = uIDs(pdbid, chain)
		except:
			print 'no uniprot id found, assigning dummy id for ', pdbid, chain 
			uniprotids = set(['-----'])
			
	shelf[key] = uniprotids
	shelf.close()		
	return uniprotids

def dot2Bars(structures):
	for s in structures:
		newseq = s.sequence.replace('.', '-')
		s.sequence = newseq
		
def lowerMuts(structures):
	for s in structures:
		for i, aa in enumerate(s.sequence):
			if aa != structures[0].sequence[i] and aa != '-':
				s.sequence = s.sequence[:i] + aa.lower() + s.sequence[i+1:]


def limitstructs(structures, limit, keepPDB, skipPDB, maxgapsize = 20):
	"""
	Custom winnowing: limits the number of structures imported but retains at least n structures per residues, where n=limit.
	"""
	if limit == 0:
		limit = len(structures) + 1
	# parse keepPDB and skipPDB user input
	requiredPDBs = keepPDB.upper().replace(".PDB", "").split(",")
	undesiredPDBs = skipPDB.upper().replace(".PDB", "").split(",")
	# sort structures by percentId, then by BLAST score, then by length
	from operator import itemgetter, attrgetter
	temp1 = sorted(structures[1:], key=attrgetter('useqlength'), reverse=True)
	temp2 = sorted(temp1, key=attrgetter('score'), reverse=True)
	idsortedstructs = sorted(temp2, key=attrgetter('percentid'), reverse=True)
	# handle query sequence
	query = structures[0]
	# create dictionary that indicates the number of templates (value) for every residue (key)
	coveragedict = {}
	for i in range(query.uend):
		coveragedict[i] = 0
	# selects structures to keep:
	selectedstructs = []
	for s in idsortedstructs:
		skip = True
		if s.pdb in requiredPDBs:
			selectedstructs.append(s)
			continue
		if s.pdb in undesiredPDBs:
			continue	
		newlycovered = 0
		for i in range(s.ustart, s.uend):
			if coveragedict[i] < limit:
				newlycovered += 1
		if newlycovered > maxgapsize:
			skip = False
		if not skip:
			for i in range(s.ustart, s.uend):		
				coveragedict[i] += 1
			selectedstructs.append(s)		
	# reconstruct list of structures and return	
	selectedstructs.append(query)
	temp = reversed(selectedstructs)
	structures = list(temp)
	return structures


def elimAllGapColumns(structures):
	myseqs = []
	for s in structures:	
		myseqs.append(s.sequence)	
	# get rid of all gap columns
	origlen = len(myseqs[0])
	for i, col in enumerate(reversed(zip(*myseqs))):
		if col.count('-') == len(col):
			for j, seq in enumerate(myseqs):
				x = origlen - i - 1
				myseqs[j] = seq[0:x] + seq[x+1:]			
	# update mymatches
	for k, s in enumerate(structures):
		s.sequence = myseqs[k]

def closeModels(availablemodels):
	import chimera
	chimera.openModels.close(availablemodels)
	availablemodels[:] = []



def processBlast(results, uid, path = '.', minscore = 50, includeNative = True, suppressdoubles = False, percentId = 0, winnow = '0', limit = 0, keepPDB = '', skipPDB = '', excludeSelected = False, deleteHidden = True, hideSubmodels = True, noConfirm = False):

	"""
	Parses BLAST results, filters results, writes output .txt and .fasta files, loads models.
	"""	

	import chimera	
	from blastpdb.ParserBlastP import Parser
	from chimera.replyobj import status

	# parse Blast
        params, output = results
	try:
		parser = Parser("MDAquery", params, output, False)
	except SyntaxError, v:
		from chimera import replyobj
		replyobj.error("BLAST error: %s\n" % str(v))
		
	# prepare the first match, which is always the query sequence
	structures=[]
	firstmatch = parser.matches[0]
	s = Structure('QUER', 'Y', firstmatch.sequence, 'SCO', firstmatch.qStart, firstmatch.qEnd)	
	structures.append(s)
	
	# filtering and structure initialization
	chainscoredict = {}
	pdblist = []
	for m in parser.matches[1:]:
		currentpdb = str(m.pdb[:4])		
		currentchain = str(m.pdb[5])
		if  m.score >= minscore or ( includeNative and uid in getUniprotID(currentpdb, currentchain) ):

			if (currentpdb, m.qStart, m.qEnd) not in chainscoredict:
				
				if suppressdoubles: 
					if currentpdb in pdblist:
						continue

				# only add the match if its not a duplicate result which happens if the matching pdb has two or more identical chains
				s = Structure(currentpdb, currentchain, m.sequence, m.score, m.qStart, m.qEnd)	
				structures.append(s)
				chainscoredict[(currentpdb, m.qStart, m.qEnd)] = s
				if suppressdoubles: 
					pdblist.append(currentpdb)
			elif currentchain != chainscoredict[(currentpdb, m.qStart, m.qEnd)].chain:
				# add this identical chain into the altchains list attribute of the resp. structure
				chainscoredict[(currentpdb, m.qStart, m.qEnd)].altchains.add(currentchain)

	# convert dots to bars
	dot2Bars(structures)
	
	# make mutated residues lower case (used to be automatic in old blast version)
	lowerMuts(structures)		

	# get rid of all gap columns
	elimAllGapColumns(structures)
	
	# process query
	q = structures[0]
	q.findBounds()
	q.percentid = 100.00
	querysequence = q.sequence
	
	# filter structures by percent id
	fstructures = []
	fstructures.append(q)
	for s in structures[1:]:
		s.findBounds() # make sure that the boundaries are updated (start and end residues...)
		s.calcPercentId(querysequence)
		if s.percentid >= percentId:
			fstructures.append(s)
		else:
			print 'Left out %s since the percent identity is only %f (threshold: %f).' % (s.pdb, s.percentid, percentId)	 	
	structures = fstructures

	# sort matches by starting residue number, then by reverse ending residue number:
	def sortstructs(structures):
		from operator import itemgetter, attrgetter
		sortedstructs = sorted(structures, key=attrgetter('end'), reverse=True)
		structures = sorted(sortedstructs, key=attrgetter('start'))
		return structures
	structures = sortstructs(structures)

	# get rid of all gap columns
	elimAllGapColumns(structures)
	# update bounds:
	for s in structures:
		s.findBounds()

	# parse user input for limit and maxgapsize
	from chimera import UserError
	origlimit = limit
	try:
		limitlist = limit.split(",")
		limit = int(limitlist[0])
		if len(limitlist) == 2:
			maxgapsize = int(limitlist[1])
		elif len(limitlist) == 1:
			maxgapsize = 20
		else:
			raise UserError("Unrecognized limit input: %s" % origlimit)
	except:
		raise UserError("Unrecognized limit input: %s" % origlimit)
				

	# limit number of structures
	structures = limitstructs(structures, limit, keepPDB, skipPDB, maxgapsize)
	structures = sortstructs(structures)
	# get rid of all gap columns
	elimAllGapColumns(structures)
	# update bounds:
	for s in structures:
		s.findBounds()

	# initialize output file
	from time import strftime
	from OpenSave import osOpen
	from os.path import join
	filename = join(path, 'MDA_output_%s.txt' % uid)
	fout = osOpen(filename, 'w')
	fout.write('Output from MultiDomainAssembler generated at ' + strftime("%Y-%m-%d %H:%M:%S") + '. \n')
	if winnow != '0':
		fout.write( 'Blast winnowing: %s (max. nr. of hits per query region).\n' % winnow )
		print 'Blast winnowing: %s (max. nr. of hits per query region).' % winnow 
	fout.write( 'A total of %d Blast hits were found.\n' % (int(len(parser.matches)) - 1) )
	print 'A total of %d Blast hits were found.' % (int(len(parser.matches)) - 1)
	if includeNative:
		fout.write('Including all native BLAST results. Non-native results filtered by a minimum score of %d.\n' % (minscore))
		print 'Including all native BLAST results. Non-native results filtered by a minimum score of %d.' % (minscore)
	else:	
		fout.write('All BLAST results filtered by a minimum score of %d.\n' % (minscore))
		print 'All BLAST results filtered by a minimum score of %d.' % (minscore)
	if suppressdoubles:	
		fout.write('Only including the best hit per pdb.\n')
		print 'Only including the best hit per pdb.'
	else:
		fout.write('Allowing multiple hits per pdb.\n')	
		print 'Allowing multiple hits per pdb.'
	fout.write('Percent ID threshold: %3.2f%%.\n' % (percentId))
	print 'Percent ID threshold: %3.2f%%.' % (percentId)
	if skipPDB:
		fout.write('Skipping the PDB files %s if found by BLAST.\n' % (skipPDB.upper().replace(".PDB", "").split(",")))
		print 'Skipping the PDB files %s if found by BLAST.' % (skipPDB.upper().replace(".PDB", "").split(","))
	if limit != 0:
		fout.write('Limiting hits: allowing %d structures per residue in target sequence (allowing gaps of max. %d residues). \n' % (limit, maxgapsize))
		print 'Limiting hits: allowing %d structures per residue in target sequence (allowing gaps of max. %d residues).' % (limit, maxgapsize)
		if keepPDB:
			fout.write('Retaining the PDB files %s if found by BLAST.\n' % (keepPDB.upper().replace(".PDB", "").split(",")))
			print 'Retaining the PDB files %s if found by BLAST.' % (keepPDB.upper().replace(".PDB", "").split(","))
	nrofstructs = len(structures)-1
	fout.write('Number of structures to be imported: %d.\n' % nrofstructs)
	print 'Number of structures to be imported: %d.' % nrofstructs
	if nrofstructs == 0:
		fout.write('No structures passed the filtering, aborting mda.')
		print 'No structures passed the filtering, aborting mda.'
		raise chimera.CancelOperation # this error will be caught in main()
	if excludeSelected:
		fout.write('(Molecules selected in Chimera were deleted, see corresponding output.fa file.) \n')
		print '(Molecules selected in Chimera were deleted, see corresponding output.fa file..)'	
	
	# print sequences with new order and res numbering rel. to query	
	for s in structures:
		fout.write(s.pdb)
		fout.write('  ')
		fout.write(s.chain)
		fout.write('  ')
		fout.write(str('%4.2f' % (s.percentid)).rjust(7))
		fout.write('  ')
		fout.write('%4s' % (str(s.score)))
		fout.write('  ')
		fout.write('%4d' % (s.ustart))
		fout.write('  ')
		fout.write('%4d' % (s.uend))
		fout.write('  ')
		fout.write('%4d' % (s.start))
		fout.write('  ')
		fout.write('%4d' % (s.end))
		fout.write('   ') 
		fout.write(s.sequence)
		fout.write('\n')
	fout.write('\n \n')

	
	# make new list of all available models that are already open to keep track of unneeded models
	availablemodels = list(chimera.openModels.list(modelTypes=[chimera.Molecule]))
	
	#store selected models in selmolset
	if excludeSelected:
		from chimera import selection
		selectedmols = selection.currentMolecules()
		selmolset = set()
		for m in selectedmols:
			try:
				selmolset.add((str(m.name), m._mda_ustart))
			except AttributeError:
				print "A model has been selected that was not previously imported by MDA, it will be deleted anyway."

	# check which of these models got modified (i.e. atom number changed) by the user or MDA, close them
	modifiedmodels = []
	for m in availablemodels:
		try:
			if len(m.atoms) != m._mda_nrofatoms:
				print "Model %d (%s) has been modified in a previous MDA run, thus reloading that pdb file." % (m.id, str(m.name))
				modifiedmodels.append(m)
		except AttributeError:
			modifiedmodels.append(m)		
	for m in modifiedmodels:
		availablemodels.remove(m)
	closeModels(modifiedmodels)			

	# warn user if a large number of models are about to be opened
	if nrofstructs > 10 and not noConfirm: #the limit depends on the patience of the user and the available RAM
		from chimera.baseDialog import AskYesNoDialog
		dlg = AskYesNoDialog("Are you sure you want to import %d pdb files?" % nrofstructs, default="Yes")
		if dlg.run(chimera.tkgui.app) == "no":
			raise chimera.CancelOperation # this error will be caught in main()

	# load models
	openedstructs = []
	openedstructs.append(q)
	from chimera import tasks
	task = tasks.Task("Opening MDA models...", modal=True)
	try:
		for i,s in enumerate(structures[1:]):
			task.updateStatus('Opening %d of %d' % (i+1, nrofstructs))
			s.getId()
			s.openModels(availablemodels, excludeSelected, deleteHidden, hideSubmodels)
			if s.models == None: # this only happens if the user presses the stop button while opening that particular model
				raise chimera.CancelOperation # this error will be caught in main()
			try:
 				s.seqStructMapping()
			except ValueError:
 				print 'WARNING: Not able to process sequence-structure association for', s.pdb, ', thus excluding this model.'
				closeModels(s.models)
				continue
			s.truncateSequence()
			s.findLigands()
			openedstructs.append(s)
			#print 'The structure', s.pdb, 'has the ligands', s.ligands, 'with a resp. length of', s.liglengths, 'residues.'
	finally:
		task.finished()
		structures = openedstructs

	# delete structures whose models have selected residues in case excludeSelected=true
	if excludeSelected:
		notselectedstructs = []
		notselectedstructs.append(q)
		# the following two lines don't work, since some previously selected models might have been closed and reopened, thus loosing the selection:
		#from chimera import selection
		#selectedmols = selection.currentMolecules()
		# instead we use selmolset, see above:
		for s in structures[1:]:
			for m in s.models:
				if (str(m.name), m._mda_ustart) in selmolset:
					print "WARNING: Excluding %d: %s since it was selected by the user." % (m.id, s.pdb)
					closeModels(s.models)
					break
				elif m == s.models[-1]:	
					notselectedstructs.append(s)
		structures = notselectedstructs		
		if len(structures)-1 == 0:
			print 'Too many structures were selected for deletion, aborting mda.'
			raise chimera.CancelOperation # this error will be caught in main()		

	# write FASTA alignment file
	writeFasta(structures, path, uid)

	# if we still have open models, we need to close these unneeded ones
	if len(availablemodels) > 0:
		closeModels(availablemodels)

	# get rid of all gap columns
	elimAllGapColumns(structures)

	# inform the user about structures that have missing coordinates:
	truncated = [s for s in structures if s.truncated]
	missing = [s for s in structures if s.missing]
	if truncated:
		fout.write('The following models have missing coordinates at the termini and thus \ntheir sequences were truncated in the alignment file:\n')
		print 'The following models have missing coordinates at the termini and thus their sequences were truncated in the alignment file:'
	for s in truncated:
		fout.write( '%s %s \n' % (s.models[0].id, s.pdb) )
		print '%s %s' % (s.models[0].id, s.pdb)
	if missing:		
		fout.write('\nThe following models have missing coordinates somewhere in the middle \nof their sequence and might thus not be ideal templates for Modeller:\n')
		print 'The following models have missing coordinates somewhere in the middle of their sequence and might thus not be ideal templates for Modeller:'
	for s in missing:
		fout.write( '%s %s \n' % (s.models[0].id, s.pdb) )
		print '%s %s' % (s.models[0].id, s.pdb)		

	# close output file and return results			
	fout.close()
	return structures



def destroyGroups():
	"""
	Destroys all groups in model panel.
	"""
	from ModelPanel.base import groupCmd, _mp
	from ModelPanel.Group import Group
 	if _mp is None: # Model Panel has not been created yet
 		return		
	foundagroup=True
	while foundagroup:
		items = _mp.items[:]
		foundagroup=False
		for i in items:
			if isinstance(i, Group):
				groupCmd([i])
				foundagroup=True


def groupSubModels():
	"""
	Groups submodels in model panel. Normally this would happen automatically
	with "chimera.openModels.open", but we have set "checkForChanges" to "False"!
	"""
	import chimera
 	from ModelPanel.base import groupCmd#, _mp
 	openmodels = list(chimera.openModels.list(modelTypes=[chimera.Molecule]))
 	allids = set([m.id for m in openmodels])
 	for currentid in allids:
 		sameidmodels = [m for m in openmodels if m.id == currentid]
 		if len(sameidmodels) > 1:
 			groupCmd(sameidmodels, sameidmodels[0].name)	



def writeFasta(structures, path, uid):
	from OpenSave import osOpen
	from os.path import join
	filename = join(path, 'MDA_output_%s.fa' % uid)
	fout = osOpen(filename, 'w')
	query = structures[0]
	fout.write('> %s  %d aa\n' % (uid, query.uend-query.ustart) )
	fout.write(query.sequence+'\n')
	nrofhits = len(structures) - 1
	i = 0
	for s in structures[1:]:
		fout.write( '>%s %s  %%ID %d \n' % (s.models[0].id, s.pdb, s.percentid) )
		fout.write(s.sequence+'\n')
		i += 1
	fout.close()	



class Structure:

	"""
	The main datastructure for open models. 
	"""
	
	def __init__(self, pdb, chain, seq, score, start, end):
		self.pdb = pdb # a string
		self.chain = chain # the chain that was aligned in the BLAST
		self.sequence = seq # the sequence of the aligned chain
		self.seqlength = end - start + 1 # length of that sequence (can contain gaps within!)
		self.useqlength = None # ungapped sequence length, assigned by the truncateSequence() method
		self.score = score # BLAST score
		self.uniprot = None # string, uniprot ID of resp. pdb file
		self.models = [] # a list of model objects in chimera
		self.percentid = None #  a custom % identity instead of the BLAST score
		self.template = False # is true if the sequence should be used as a template for match
		self.ligands = [] # a list of chain IDs that are ligands, i.e. have different uniprot IDs than self.uniprot
		self.liglengths = [] # see self.findLigands()
		self.overlap = None # nr. of residues that overlap with the previous structure (needed for match)
		self.ustart = start # number of the 1st aligned residue resp. to UniProt(no gaps)
		self.uend = end # number of the last aligned residue resp. to UniProt (no gaps)
		self.start = None # starting residue nr. resp. to query sequence (might have gaps)
		self.end = None # ending residue nr. resp. to query sequence (might have gaps)
		self.altchains = set() # other chains of the pdb that aligned equally well in Blast as self.chain
		self.seqobj = None # a sequence object of self.sequence, assigned in percentid method
		self.structseqobj = None # a sequence object of the actual sequence in the pdb, might have missing or extra res.
		self.matchmap = {} # a dictionary relating indices from self.sequence to self.structseqobj
		self.blastresind = [] # a list of indices where the matchmap actually points to an existing residue
		self.blastresinst = [] # a list of instances of residues in the matchmap
		self.covering = None # see hideSimilar()
		self.ishiddenunderneath = None # see hideSimilar()
		self.yshift = None # see arrangeModelsY() and rearrangeHidden()
		self.row = 1 # needed for y-placement, see arrangeModelsY()
		self.truncated = False # see truncateSequence()...
		self.missing = False # see truncateSequence()...
		self.Nmissingres = 0 # Nr. of residues that were deleted near N-terminus due to lacking coordinates
		

	def findBounds(self):		
		totseqlength= len(self.sequence) #actually corresponds to totseqlength since it contains '-' for gaps!
		# find start		
		for i in range(totseqlength):
			if self.sequence[i] != '-' :
				self.start = i
				break	
		# find end
		for i in range(totseqlength):
			i = totseqlength - i - 1
			if self.sequence[i] != '-' :
				self.end = i
				break
					
		
		
	def openModels(self, availablemodels, excludeSelected, deleteHidden, hideSubmodels):
		
		"""
		Only opens a new model if no open model with the same pdb ID is found.
		In case of excludeSelected=True, it needs to find a model previously opened with MDA and aligned at the same position.
		"""	
		
		import chimera

		# check whether the model is already open
		samenamemodels = [m for m in availablemodels if m.name == self.pdb]
		# if selected models are to be deleted, we have to make sure we assign the same models to the BLAST hits that we had previously
		if excludeSelected: 
			temp = []
			for m in samenamemodels:
				try:
					if m._mda_ustart == self.ustart:
						temp.append(m)
				except AttributeError:
					print "Model %s doesn't seem to belong to any MDA structure previously, thus it will be deleted and reloaded." % str(m.id)
			samenamemodels = temp

		# if its empty open a new one
		if not samenamemodels: 
			try:
				if deleteHidden and hideSubmodels: # this is much faster than loading all submodels and deleting them later
					#self.models = chimera._openPDBIDModel(self.pdb, explodeNMR=False) # alternative way of loading 1st model, but crashes for e.g. 2MFN.pdb
					self.models = chimera._openPDBIDModel(self.pdb)[:1]
					chimera.openModels.add(self.models)
				else: # traditional way of opening all submodels
					self.models = chimera.openModels.open(self.pdb, type="PDBID", checkForChanges=False)	
			except:
				raise
				print 'No model exists for %s' % self.pdb
				self.models = []
			# store number of atoms as an attribute of each model, see the creation of the list of availablemodels above...	
			for m in self.models:
				m._mda_nrofatoms = len(m.atoms) # the prefix _mda_ hides this attributes from the attribute gathering process in the render by attribute tool
				m._mda_ustart = self.ustart # the prefix _mda_ hides this attributes from the attribute gathering process in the render by attribute tool
		else: 
			currentid = samenamemodels[0].id
			for m in samenamemodels:
				if m.id == currentid:
					m._mda_ustart = self.ustart # the prefix _mda_ hides this attributes from the attribute gathering process in the render by attribute tool
					self.models.append(m)
					availablemodels.remove(m)		
			
		
	def getId(self):
		import chimera
		uniprotset = getUniprotID(self.pdb, self.chain)
		self.uniprot = uniprotset.pop() # assume the set only contains one ID	
		
		
	
	def calcPercentId(self, querysequence):
		from chimera.Sequence import percentIdentity, Sequence
		self.seqobj = Sequence()
		queryseqobj = Sequence()
	 	self.seqobj[:] = self.sequence
	 	queryseqobj[:] = querysequence
		self.percentid = percentIdentity(self.seqobj, queryseqobj)


	
	def findLigands(self):
		"""
		Finds chains in pdb that were not part of the BLAST results but in the same file (most likely complexed).
		"""	
		import chimera
		from Measure import inertia		
		for m in self.models[0:1]: #assume that the other models in an nmr bundle are the same as the first one... 
			chainIDs = set([str(r.id.chainId) for r in m.residues]) #make a set to avoid double entries
			# the str() in the line above is essential on linux machines, since shelve uses dumbdbm there which needs strings and not unicodes!
			if len(chainIDs) > 1:
				# remove the ID which we are assembling
				chainIDs.remove(self.chain)
				# create dictionary mapping from uniprot ids to chains
				ligands = {}
				chainIDs2 = set()
				for c in chainIDs: 
					id = (getUniprotID(self.pdb, c)).pop()
					if id != self.uniprot:	
						chainIDs2.add(id)
						if id not in ligands:
							ligands[id] = [c]
						else:
							ligands[id].append(c)
				# find receptor atom coordinates:	
				recatomlist = [r.findAtom('CA') for r in m.residues if (r.findAtom('CA') and r.id.chainId == self.chain)]			
 	 	 	 	axes, moments, reccenter = inertia.atoms_inertia(recatomlist)
 	 	 	 	# loop over ligand uniprot IDs
				for id in chainIDs2:
					chains = ligands[id]
					mindistance = 1000000
					# loop over chain letters with the same uniprot ID
					for c in chains:
						# find ligand atom coordinates:			
 	 	 	 			ligatomlist = [chimera.misc.principalAtom(r) for r in m.residues if r.id.chainId == c and chimera.misc.principalAtom(r)]
 	 	 	 			if len(ligatomlist) ==0: #ugly but works...
 	 	 	 				ligatomlist = [r.atoms[0] for r in m.residues if r.id.chainId == c and r.atoms]
 	 	 	 			axes, moments, ligcenter = inertia.atoms_inertia(ligatomlist)
						diff = reccenter - ligcenter
						distance = ( (diff[0])**2 + (diff[1])**2 + (diff[2])**2 )**(0.5)
						if distance < mindistance:
							ligandchain = c
							ligandlength = len(ligatomlist)
							mindistance = distance				
					self.ligands.append(ligandchain)
					self.liglengths.append(ligandlength)
				
				
	def seqStructMapping(self):

		"""
		Establishes a map linking sequence residues to model residues.
		Raises a ValueError if sthg. goes wrong.
		"""	
	
		threshold = 10	
		errortolerance = 0.1	
		
		from chimera.Sequence import Sequence
		from MultAlignViewer.structAssoc import tryAssoc, estimateAssocParams
		
		origchain = self.chain
		allchains = (self.altchains | set(self.chain))

		for chain in allchains:
			
			# match the s.sequence residue numbers to pdb residue numbers 
 			try:
 				curstructseqobj = self.models[0].sequence(chain)
 			except KeyError:
 				print 'Chain %s of structure %s has been deleted in a previous MDA run or by the user, thus keeping chain %s as the structure-associated chain.' % (chain, self.pdb, self.chain)
 				continue
 			estlen, segments, gaps = estimateAssocParams(curstructseqobj)
 			try:
 				curmatchmap, errors = tryAssoc(self.seqobj, curstructseqobj, segments, gaps, estlen, maxErrors=errortolerance*estlen)
	 		except ValueError:
 				print 'Error while determining seqstruct matchmap residues for ', self.pdb, chain, '.'
 				raise
			if len(curmatchmap) > len(self.matchmap):
				self.matchmap = curmatchmap
				self.chain = chain
				self.structseqobj = curstructseqobj
		
 		if origchain != self.chain:
 			print 'Found a better structure-sequence association for chain ', self.chain, ' in model ', self.pdb, '.'
 			print '(Compared to the original chain', origchain, 'found by BLAST.)'
 			
 		if len(self.matchmap) < threshold:	
 			print 'Bad structure-sequence association for chain ', self.chain, ' in model ', self.pdb, '.'
 			#raise ValueError	

 		# store	residue indices of matchmap that exist:
 		for i,char in enumerate(self.seqobj.ungapped()):
			try:
				r = self.matchmap[i]
			except KeyError:
				continue
			self.blastresind.append(i)
			self.blastresinst.append(r)

		# in rare cases, none of the coordinates of the residues that aligned in BLAST will be in the structure
		if self.blastresind == []:
			print "None of the coordinates of the residues that aligned in BLAST are in the structure of %s." % self.pdb
			raise ValueError		


 	def truncateSequence(self):

 		"""
		Truncates the sequence of structures if the termini have residues with missing coordinates
		"""

		useq = self.seqobj.ungapped()
		useqlength = len(useq)
		# find missing residues:
		missingres = []
		for i in range(useqlength):
			if i not in self.blastresind:
				missingres.append(i)
		if len(missingres) > 0:
			# categorize into res. missing at the C-terminus and N-terminus		
			Nmissingres = [i for j,i in enumerate(missingres) if i-j == 0]
			if missingres[-1] == useqlength - 1:
				lastdiff  =  missingres[-1] - len(missingres) + 1
				Cmissingres = [ i for j,i in enumerate(missingres) if i-j == lastdiff ]
			else:	
				Cmissingres = []
			# edit sequence:	
			truncseq = self.sequence	
			if len(Nmissingres) > 0:
				print "Structure %s is missing coordinates for the following N-terminal residues: %s" % (self.pdb, str(Nmissingres))
				i = self.start
				j = i	
				while i in range(self.start, self.start+len(Nmissingres)): 		
					if truncseq[j] != '-':
						i += 1
					truncseq = truncseq[0:j] + '-' + truncseq[j+1:]	
					j += 1
				self.sequence = truncseq
				self.findBounds()
				self.ustart = self.ustart + len(Nmissingres)
				# mark as truncated:
				self.truncated = True
			if len(Cmissingres) > 0:		
				print "Structure %s is missing coordinates for the following C-terminal residues: %s" % (self.pdb, str(Cmissingres))
				i = 0
				for pos, char in reversed(list(enumerate(self.sequence))):
					if char != '-':
						i += 1
						truncseq = truncseq[0:pos] + '-' + truncseq[pos+1:]
					if i == len(Cmissingres):
						break
				self.sequence = truncseq
				self.findBounds()
				self.uend = self.uend - len(Cmissingres)			
				# mark as truncated:
				self.truncated = True
			# mark if there are missing coordinates inbetween N and C: 	
			if len(missingres) > len(Nmissingres) + len(Cmissingres):
				self.missing = True
			# store nr of N-terminal missing res.
			self.Nmissingres = len(Nmissingres)
		# store actual sequence length
		self.useqlength = useqlength - len(missingres)

		

			
def reduceModels(Structures, hideSubmodels = True, hideComplex = False, hideAltChain = True, deleteHidden = True):
	
	"""
	Hides or deletes unwanted models/chains.
	"""	

	import chimera
	from Midas import unmodeldisplay, undisplay, unribbon
	# hide or delete all subids after the first one
	modelstobeclosed=[]
	for s in Structures[1:]:
		for m in reversed(s.models):
			if m.subid > 1: 
				if hideSubmodels:
					if deleteHidden:	
						s.models.remove(m) # has to be removed from the modellist since otherwise underlying stuff is missing when referenced later
						modelstobeclosed.append(m) # select for deletion
						print 'Deleting model %s.' % str(m) 
					else:	
						unmodeldisplay(str(m))
						print 'Hiding model %s.' % str(m)
			else:							
				chainIDs = set([r.id.chainId for r in m.residues])
				if len(chainIDs) > 1: # delete or hide all but one chain that was retrieved by BLAST earlier
					chainIDs.remove(s.chain) # make sure the main chain doesn't get hidden
					for c in chainIDs:
						identifier = str(m) + ':.' + c 
						if c not in s.ligands and hideAltChain:
							if deleteHidden:
								print 'Deleting alternate chain %s of model %s.' % (c, str(m))
								chimera.runCommand('delete %s' % identifier) 
								#better option: use chimera.deleteAtom or similar...
							else:	
								print 'Hiding alternate chain %s of model %s.' % (c, str(m))
								undisplay(identifier) # might not be necessary...
								unribbon(identifier)
						elif c in s.ligands and hideComplex:
							if deleteHidden:
								print 'Deleting complexed chain %s of model %s.' % (c, str(m))
								chimera.runCommand('delete %s' % identifier)
								#better option: use chimera.deleteAtom or similar...
							else:	
								print 'Hiding complexed chain %s of model %s.' % (c, str(m))
								undisplay(identifier) # might not be necessary...
								unribbon(identifier)		
	# close doomed models:
	if hideSubmodels:
		chimera.openModels.close(modelstobeclosed)

	# delete ions if desired:
	if hideComplex:
		if deleteHidden:
			chimera.runCommand('delete ions')
		else:	
			chimera.runCommand('~show ions')
	


class Box:

	"""
	Within a box, there should be enough overlap to align models using the match command.
	"""	
	
	def __init__(self, number):
		self.nr = number
		self.structures = []
		
	def __str__(self):
		return 'Box number %2d contains %3d structures' % (self.nr, len(self.structures))	
		
	def appendStructure(self, s):	
		self.structures.append(s)
		
	def findtemplate(self, i): 
		if self.structures[i].template:
			return self.structures[i]
		else:
			if i > 0:
				return self.findtemplate(i-1)
			else:
				#print 'No template structure for matching found.'
				return self.structures[0]
		

class Gap:

	"""
	Handles gaps (where no model was found) and draws spheres proportional to the number of missing residues.
	"""

	def __init__(self, aa, x):
		self.length = aa # length in residues
		# (1.21 x MW) Angstrom^3 / molecule, see www.basic.northwestern.edu/biotools/proteincalc.html#vol
		# assume 110 Da per aa -> V = 133 * aa = 4/3 Pi r^3
		self.radius = 3.17*(float(aa))**(1./3) # radius of the sphere
		self.minx = x

	def __str__(self):
		x = self.minx + self.radius
		return 'This gap has a length of %d amino acids, represented by a sphere at x = %g with radius r = %g.' % (self.length, x, self.radius)	
		
	def drawsphere(self, sphereID):
		
		import chimera
		from Shape import shapecmd
		
		xpos = self.minx + self.radius
		zpos = 0
		ypos = 0
		
		spherename = 'Gap of %d residues' % self.length
		sphere = shapecmd.sphere_shape(radius = self.radius, center = '%f, %f, %f' % (xpos, ypos, zpos), rotation = None, qrotation = None, coordinateSystem = None, divisions = 72, color = (0.663,0.663,0.663,0.5), mesh = False, linewidth = 1, slab = None, modelName = spherename, modelId = sphereID)
		sphere = chimera.openModels.list()[-1] # the above line does not return a model, so I need this line... CAUTION; only works if sphereID is high enough
		
		# the coordinate are relative to the first open model, so transform the sphere with the inverse of the first model's xform
		model0 = chimera.openModels.list(modelTypes=[chimera.Molecule])[0]
		model0pos = model0.openState.xform
		invmodel0pos = chimera.Xform.inverse(model0pos)
		spherepos = sphere.openState.xform
		spherepos.multiply(invmodel0pos)
		sphere.openState.xform = spherepos
			
	def diameter(self):
		return 2*(self.radius)
			
					
		
def createBoxes(Structures):

	"""
	Groups structures into boxes. Within a box, there should be enough overlap to align models using the match command.
	"""	
	
	minoverlap = 10 # minimum overlap of two sequences such that they will be used with match
	prevend = 0
	prevxslot = 0
	prevseq = []
	Boxes = []
	
	for s in Structures[1:]:

		# calculate length of aligning sequence, which will be used later in hideSimilar()
		s.length = s.end - s.start

		curseq = s.sequence
		if prevseq != []:
			overlapaalist = [caa for caa, paa in zip(curseq[s.start:prevend], prevseq[s.start:prevend]) if (caa != '-' and paa != '-')]
			curoverlap=len(overlapaalist)
		else:
			curoverlap = -1
			
		s.overlap = curoverlap
				
		if curoverlap >= minoverlap or s.length <= minoverlap:
			curxslot = prevxslot
		else:
			curxslot = prevxslot + 1
			b = Box(curxslot)
			Boxes.append(b)
			
		b.appendStructure(s)
				
		prevxslot = curxslot	
	
		if s.end >= prevend:
			prevseq = curseq
			prevend = s.end
			s.template = True # will be used for match
			
	return Boxes
	


def hideSimilar(Boxes, uid, group):

	"""
	Hides models that are considered to be in the same group (only if group=True).
	"""

	# if no grouping desired, all structures must be labeled as covering structures
	if not group:
		for b in Boxes:
			for s in b.structures:
				s.covering = True
		return		
	
	# otherwise, continue to grouping procedure:
	print "Hiding structures that are similar to each other..."

	overhang = 25 # number of aa that can differ from the ends of two structures where one will be hidden
	showligands = False # if true, an extra group for structures with ligands will be created
 	import chimera
 	from Midas import unmodeldisplay
 		
	for b in Boxes:
	
		# classify structures as native/foreign and ligands	
		n_structs = []
		f_structs = []
		n_noligstructs = []
		n_ligstructs = []
		f_noligstructs = []
		f_ligstructs = []		
		for s in b.structures:
 			if s.uniprot == uid and s.ligands == []:
 				n_structs.append(s)
 				n_noligstructs.append(s)
 			elif s.uniprot == uid and s.ligands != []:
 				n_structs.append(s)
 				n_ligstructs.append(s)					
			elif s.ligands == []:		
				f_structs.append(s)
				f_noligstructs.append(s)
			else:	
				f_structs.append(s)
				f_ligstructs.append(s)
		
		def classviz(allstructures):
			'''
			Classifies structures into covering and covered structures, hides covered ones.
			Covering structures are the longest ones in their subbox and slightly different from s.template.
			'''
			# find covering structures:
			prevend = -overhang
			prevcoverstruct = None
			coveringstructs = []
			for s in allstructures:
				if prevend + overhang < s.end:
					# check whether the starting residue of the previous covering structure isn't too far back 
					if prevcoverstruct and prevcoverstruct.start + overhang > s.start:
						prevcoverstruct.covering = False # then the previous covering structure doesn't need to be one!
						coveringstructs.remove(prevcoverstruct)
						print prevcoverstruct.pdb, prevcoverstruct.models[0].id, 'is not covering other structures, instead:'
					s.covering = True
					coveringstructs.append(s)
					prevend = s.end
					prevcoverstruct = s
					#print s.pdb, s.models[0].id, 'is covering other structures.'
			# find covered structures and hide them	
			for s in allstructures:
				if not s.covering:
					for c in coveringstructs:
						if s.end < c.end + overhang:
							s.ishiddenunderneath = c
							#print s.pdb, s.models[0].id, "is hidden underneath", c.pdb, c.models[0].id
							for m in s.models:
								unmodeldisplay(str(m))
							break # the fist covering structure is the one we want
 			return coveringstructs
 				
 		def groupmodels(allstructures, coveringstructures):
 			'''
			Make groups in model panel.
 			'''
			from ModelPanel.base import groupCmd, getGroupOf
			showModelPanel()	# Have to create model panel for group
			for c in coveringstructures:
	 	  		itemstogroup = []
	 	  		# add cover structure to groupable items
	 	  		modelzero = c.models[0]
	 	  		item = getGroupOf(modelzero)
		 	  	if not item:
					for m in c.models:
		 	  	 		itemstogroup.append(m) # m is a model	
		 	  	else:
		 	  		itemstogroup.append(item) # item is a group
		 	  	# add to be hidden structures to groupable items 
	 	  	 	for s in allstructures:
	 	  	 		if s.ishiddenunderneath == c:
		 	  	 		modelzero = s.models[0]
		 	  	 		item = getGroupOf(modelzero)
		 	  	 		if not item:
		 	  	 			for m in s.models:
		 	  	 				itemstogroup.append(m) # m is a model	
		 	  	 		else:
		 	  	 			itemstogroup.append(item) # item is a group
		 	  	# cannot make a group if only one item 		
		 	  	groupsize = len(itemstogroup)
		 	  	if groupsize <= 1:
		 	  		continue
		 	  	# name of group that will appear in model panel
 	  			name = '%s and %d similar' % (c.pdb, groupsize-1)
		 	  	# make group				
 	  	 		mygroup = groupCmd(itemstogroup, name)	
  	  	 		
 		# execute for all desired lists
 		if showligands:
			coveringstructs = classviz(n_noligstructs)
			groupmodels(n_noligstructs, coveringstructs)
			coveringstructs = classviz(n_ligstructs)
			groupmodels(n_ligstructs, coveringstructs)
			coveringstructs = classviz(f_noligstructs)
			groupmodels(f_noligstructs, coveringstructs)
			coveringstructs = classviz(f_ligstructs)
			groupmodels(f_ligstructs, coveringstructs)
		else:
			coveringstructs = classviz(n_structs)
	 		groupmodels(n_structs, coveringstructs)
			coveringstructs = classviz(f_structs)
	 		groupmodels(f_structs, coveringstructs)

def showModelPanel():
	from chimera import dialogs
	import ModelPanel
	dialogs.display(ModelPanel.ModelPanel.name)

 		
def closeSpheres():
	import chimera
	tocloselist = [m for m in chimera.openModels.list() if 'Gap of' in m.name]
	chimera.openModels.close(tocloselist)

		
def arrangeModelsX(Boxes, Structures, uid, totseqlength):
	"""
	Lines up models along X-axis according to their position in the BLAST alignment.
	"""
	xpadding = 0 # adjust for tuning x-placement (in Angstrom)
	Gaps = []
	import chimera, Matrix
	from Measure import inertia
	from numpy import float32
	# call match within boxes		
	for b in Boxes:
		nrofstructs = len(b.structures)
		if nrofstructs > 1: # only prepare matchmaking if we have at least two structures
			for i in range(nrofstructs-1): # loop over structure-pairs in the box
				# for j = 0, use match
				curstruct = b.structures[i+1]
				curmodelzero = curstruct.models[0]
				curnrofsubmodels = len(curstruct.models) 
				# use a function to check whether the ith structure is suitable or whether we need to go further back	
				tempstruct = b.findtemplate(i)	
				tempmodelzero = tempstruct.models[0]
				# find atoms that align and are not gaps (atomlists have to be the same length for current structure and template!)
				tempstructatoms = []
				curstructatoms = []
				temprescounter = tempstruct.Nmissingres-1
				currescounter = curstruct.Nmissingres-1
				for (tempres, curres) in zip(tempstruct.sequence, curstruct.sequence):
					if tempres != '-':
						temprescounter +=1
					if curres != '-':
						currescounter +=1
					if tempres != '-' and curres != '-':
						try:
							curresobj = curstruct.matchmap[currescounter]
						except KeyError:
							continue
						try:
							tempresobj = tempstruct.matchmap[temprescounter]	
						except KeyError:
							continue
						tempatom = tempresobj.findAtom("CA")
						curatom = curresobj.findAtom("CA")
						if tempatom is not None and curatom is not None:
							tempstructatoms.append(tempatom)
							curstructatoms.append(curatom)
				# check whether we have enough atoms to call match
				lent = len(tempstructatoms)
				lenc = len(curstructatoms)
				if lent < 3 or lenc < 3 or lenc != lent:
					print 'Could not align %s to %s since not enough residues were found to call match directly. Trying matchmaker...' % (curstruct.pdb, tempstruct.pdb)
					# use matchmaker...
					#atomspec1 = str(tempmodelzero) + ':.' + tempstruct.chain
					#atomspec2 = str(curmodelzero) + ':.' + curstruct.chain
					#chimera.runCommand("mmaker %s %s ss false iterate false pairing ss" % (atomspec1, atomspec2))
					chimera.runCommand("mmaker %s %s" % (str(tempmodelzero), str(curmodelzero)))
					# store position after alignment
					curpos = curmodelzero.openState.xform
					# for j > 0, use the stored position of the 0th model
					for j in range(curnrofsubmodels-1):
						curmodel = curstruct.models[j+1]
						curmodel.openState.xform = curpos
				else:	
					# call match only if it will work properly
	 				from chimera import match
			 		xform, rmsd = match.matchAtoms(tempstructatoms, curstructatoms)
			 		xf = tempmodelzero.openState.xform
			 		xf.multiply(xform)
			 		curmodelzero.openState.xform = xf 
			 		chimera.replyobj.info("RMSD between %s and %s over %d residues is %.3f angstroms\n" % (tempstruct.pdb, curstruct.pdb, lenc, rmsd))
					# for j > 0, use the stored position of the 0th model
					for j in range(curnrofsubmodels-1):
						curmodel = curstruct.models[j+1]
						curmodel.openState.xform = xf
	# position boxes along the x-axis 
	prevxmax = 0
	prevend = -1
	for b in Boxes:
		# find first and last structure
		firststruct = None
		laststruct = None
		i = 0
		for i in range(len(b.structures)):
			if b.structures[i].template and not firststruct:
				firststruct = b.structures[i]
			if b.structures[-1-i].template and not laststruct:
				laststruct = b.structures[-1-i]
		if not firststruct:
			firststruct = b.structures[0]		
		if not laststruct:
			laststruct = b.structures[-1]						
		# find coordinates of N and C terminus
		firstmodel = firststruct.models[0]
		lastmodel = laststruct.models[0]
		# finding the N terminus:
		i = 0
		while True:
			Nind = firststruct.blastresind[i]
			resN = firststruct.matchmap[Nind]
			caN = resN.findAtom('CA')
			if caN:
				coordN = caN.xformCoord()
				break
			i += 1
			#print 'An N-terminal residue of %s is missing a C_alpha atom.' % (firststruct.pdb)
		# finding the C terminus:
		i = 0
		while True:
			Cind = laststruct.blastresind[-1-i]
			resC = laststruct.matchmap[Cind]
			caC = resC.findAtom('CA')
			if caC:
				coordC = caC.xformCoord()
				break
			i += 1
			#print 'A C-terminal residue of %s is missing a C_alpha atom.' % (laststruct.pdb)
 		# define translation to center
 		relevantatoms = [resN.findAtom('CA'), resC.findAtom('CA')]
 		axes, moments, center = inertia.atoms_inertia(relevantatoms)
 		cx, cy, cz = center # in global coordinates
 		cxf = chimera.Xform.translation(-cx, -cy, -cz)
 		# define rotation to orient along x-axis
 		axis = coordC - coordN 
  		xN = Matrix.inner_product(axis, coordN)
 		xC = Matrix.inner_product(axis, coordC)
 		correctorientation = (xN < xC)
 		if not correctorientation:
 			axis = -axis			
		rtf = Matrix.vector_rotation_transform(axis.data(), (1, 0, 0))
		rxf = Matrix.chimera_xform(rtf)
		# execute transformations
 		for s in b.structures:
 		 	for m in s.models:
 		  		xf = chimera.Xform()
 		 		xf.premultiply(cxf)
 		 		xf.premultiply(rxf)
 			 	xf.multiply(m.openState.xform)
 		 		m.openState.xform = xf	
	 	# figure out how much to translate along x
	 	# determine length of box
		xmin, xmax = 0, 0
		for s in b.structures:
			if s.ishiddenunderneath:
				continue
			relevantatoms = [r.findAtom('CA') for r in s.models[0].residues if (r.findAtom('CA') and r.id.chainId == s.chain and r in s.blastresinst)]
			axyz = chimera.numpyArrayFromAtoms(relevantatoms, xformed=True).astype(float32)
			curxmin, curxmax = axyz[:,0].min(), axyz[:,0].max()
			if curxmin < xmin:
				xmin = curxmin
			if curxmax > xmax:
				xmax = curxmax			
		xoverlap = prevxmax - xmin
		# determine gap between current and previous box:
		curstart = firststruct.start
		gaplength = curstart - prevend - 1
		# store the last residue of this box for the next iteration 	
		prevend = laststruct.end
		# create gap instance if necessary
		if gaplength <= 0 and prevxmax != 0:
			gaplength, gapspacing = 0, 0	 
		else:
			g = Gap(gaplength, prevxmax + xpadding)
			Gaps.append(g)
			gapspacing = g.diameter()
		# set translation	
		xshift = xoverlap + gapspacing + 2*xpadding
		# store values for next iteration
		prevxmax = xmax + xshift
		# define x translation
		txf = chimera.Xform.translation(xshift, 0, 0)
		# execute transformations
 		for s in b.structures:
 		 	for m in s.models:
 		  		xf = chimera.Xform()
 		 		xf.premultiply(txf)
 			 	xf.multiply(m.openState.xform)
 		 		m.openState.xform = xf
 	# add final gap (from end of Blast alignment to end of UniProt sequence)
 	i = 0
 	while i >= 0:
 	 	if Structures[-1-i].template:
 	 		j = -1-i
 		 	break
 	 	i += 1
 	lastgaplength = (Structures[0].end - Structures[j].end) + (totseqlength - Structures[0].uend) - 1
 	g = Gap(lastgaplength, prevxmax + xpadding)
	Gaps.append(g)
	# finally, draw all spheres to represent gaps
 	sphereID = 1000 # a high model id ensure that the spheres are last in the list of open models...	 
	for g in Gaps:
		if g.radius > 0:
			sphereID += 1
			g.drawsphere(sphereID)
 	return Gaps

 	 	

def arrangeModelsY(Boxes, Gaps, hideComplex):

	"""
	Stacks models along Y-axis.
	"""

	ypadding = 10 # adjust for tuning y-placement (in Angstrom)
	import chimera
 	
 	for b in Boxes:

 		# find boundaries
 		def findboundaries(hideComplex, listofstructs):
			from numpy import float32
	 		for s in listofstructs:
	 			if hideComplex:
	 				atoms = [r.findAtom('CA') for r in s.models[0].residues if (r.findAtom('CA') and r.id.chainId == s.chain)]
	 			else:
	 				atoms = [r.findAtom('CA') for r in s.models[0].residues if ( r.findAtom('CA') and ((r.id.chainId == s.chain) or (r.id.chainId in s.ligands)) )]
	 			axyz = chimera.numpyArrayFromAtoms(atoms, xformed=True).astype(float32)
	 			s.xmin = axyz[:,0].min()
	 			s.xmax = axyz[:,0].max()
	 			s.ymin = axyz[:,1].min()	
	 			s.ymax = axyz[:,1].max()
	 			#print 'PDB, Xmin, Xmax, Ymin, Ymax', s.pdb, s.xmin, s.xmax, s.ymin, s.ymax
	 	findboundaries(hideComplex, b.structures)		

		# assigning y-positioning row
		def assignrow(row, listofstructs):
			thresstruct = None
			newrow = False
			coveringstructs = [s for s in listofstructs if s.covering]
			hiddenstructs = [s for s in listofstructs if s.ishiddenunderneath]
			for s in coveringstructs:
				if s.row == row:
					if thresstruct == None:
						thresstruct = s
					elif s.xmin < thresstruct.xmax:
						s.row = row + 1
						newrow = True
					else:
						s.row = row
						thresstruct = s

			for s in hiddenstructs:
				s.row = s.ishiddenunderneath.row			

			if newrow:
				assignrow(row+1, listofstructs)
		assignrow(1, b.structures)					

		# move the center of all structures to y = 0
		def yalign(listofstructs):
			for s in listofstructs:
				# find y-coordinate of center of structure
				curcenter = (s.ymax + s.ymin ) / 2.
				yshift = 0 - curcenter
				# define y translation
				tyf = chimera.Xform.translation(0, yshift, 0)
				# store y-shift if needed later
				s.yshift = yshift 
				# execute
				for m in s.models:
					xf = chimera.Xform()
 		 			xf.premultiply(tyf)
 		 			xf.multiply(m.openState.xform)
		 			m.openState.xform = xf	
		yalign(b.structures)

		# update boundaries
		findboundaries(hideComplex, b.structures)

		# move covering structures (or all if group is false), "down" controls direction (True: downwards or False: upwards)
		def movey(row, listofstructs, down = True):
			shift = False
			coveringstructs = [s for s in listofstructs if s.covering]
			ymax = coveringstructs[0].ymin
			ymin = coveringstructs[0].ymax
			# find extrema
			for s in coveringstructs:
				if s.row == row:
					if s.ymax > ymax:
						ymax = s.ymax
				elif s.row == row + 1:	
					if s.ymin < ymin:
						ymin = s.ymin
			# move			
			for s in coveringstructs:			
				if s.row > row:
					shift = True
					yoverlap = ymax - ymin
					yshift = yoverlap + ypadding
					if down:
						yshift = -yshift
		 		 	# store additional y-shift if needed later
					s.yshift += yshift 
					# define y translation
					tyf = chimera.Xform.translation(0, yshift, 0)
					# execute
					for m in s.models:
						xf = chimera.Xform()
	 		 			xf.premultiply(tyf)
	 		 			xf.multiply(m.openState.xform)
 		 				m.openState.xform = xf			
 		 	# iterate recursively			
 		 	if shift:
 		 		movey(row+1, listofstructs, down)		
 		movey(1, b.structures, down = True)

 		#move hidden structures (or none if group is false):
		def rearrangeHidden(listofstructs):
			import chimera
			hiddenstructs = [s for s in listofstructs[1:] if s.ishiddenunderneath]
			for s in hiddenstructs:
				refstruct = s.ishiddenunderneath
				# the difference of the two shifts is what we need to translate with
				yshift = refstruct.yshift - s.yshift
				tyf = chimera.Xform.translation(0, yshift, 0)
		 		for m in s.models:
		 			xf = chimera.Xform()
			 		xf.premultiply(tyf)
			 		xf.multiply(m.openState.xform)
		 		 	m.openState.xform = xf
		rearrangeHidden(b.structures)


def setAttributes(Structures):
	"""
	Sets attributes for models and residues. These can be used by the 
	Color-by-attributes-tool in Chimera to set custom colors.
	"""
	for s in Structures[1:]:
		for m in s.models:
			for r in m.residues:
				if str(r.id.chainId) not in s.ligands: # only set these attributes for non-ligand chains:
					r.mda_percentid = s.percentid
					r.mda_blastscore = s.score
		for r in s.models[0].residues:
			if str(r.id.chainId) in s.ligands:
				r.mda_alignment = 4.0 # ligand res
			else:
				r.mda_alignment = 3.0 # blast chain res, should be made transparent
		for i,char in enumerate(s.seqobj.ungapped()):
			try:
				r = s.matchmap[i]
			except KeyError:
				continue	
			if i in s.blastresind:
				if char.islower():
					r.mda_alignment = 2.0 # mutation
				else:
					r.mda_alignment = 1.0 # part of blast alignment

	# make sure attributes will get stored in session:
	import chimera
	from SimpleSession.save import registerAttribute
	registerAttribute(chimera.Residue, "mda_percentid")
	registerAttribute(chimera.Residue, "mda_blastscore")
	registerAttribute(chimera.Residue, "mda_alignment")				

			
def colorModels(Structures, coloring= 'mutations', panelcolor = False):
	"""
	Coloring of models, three different options: 'mutations' (default), 'percentid' or 'blastscore'
	"""
	import chimera
	coloring= coloring.lower()
	# define base colors
	mutcolor = "1.0,0.0,0.0,1.0" # Red
	ligcolor = "0.0,0.0,1.0,1.0" # Blue
 	blastcolor = "0.66,0.66,0.66,1.0" # Dark Grey
 	noblastcolor = blastcolor
	# color icons in model panel:
 	if panelcolor:
	 	for s in Structures[1:]:
			if s.percentid == 100:
				for m in s.models:
	 				m.color = chimera.MaterialColor(*[float(x) for x in blastcolor.split(',')])
	 		else:
	 			for m in s.models:
	 				m.color = chimera.MaterialColor(*[float(x) for x in mutcolor.split(',')])
	# coloring by residue
	chimera.runCommand( "rangecolor mda_alignment,r 1 %s 2 %s 3 %s 4 %s" % (blastcolor, mutcolor, noblastcolor, ligcolor) )	
	if coloring in 'percentid' and len(coloring) >= 3:
		chimera.runCommand( "rangecolor mda_percentid,r min %s max %s" % (mutcolor, blastcolor) )
	elif coloring in 'blastscore' and len(coloring) >= 3:
		chimera.runCommand( "rangecolor mda_blastscore,r min %s max %s" % (mutcolor, blastcolor) )
	elif coloring in 'mutations' and len(coloring) >= 3:
		pass
	else:	
		print 'Coloring command "%s" not understood, used option "mutations". (Please enter either "mutations", "blastscore" or "percentid".)' % coloring
	# make residues not aligned in BLAST significantly transparent
	chimera.runCommand( "transparency 80,r :/mda_alignment=3" )
	# color ions like ligands
	chimera.runCommand( "color %s ions" % ligcolor )


def findMAV():
	"""
	Finds MAV instances.
	"""
	from chimera.extension import manager
	from MultAlignViewer.MAViewer import MAViewer
	mavs = [inst for inst in manager.instances if isinstance(inst, MAViewer)]
	return mavs


def openMAV(path, uid, structures):
	"""
	Imports FASTA file generated in processBlast(), does sequence-structure associations.
	"""
	import chimera
	from os.path import join
	from MultAlignViewer.MAViewer import MAViewer
	# open fastafile generated by mda
	filename = join(path, 'MDA_output_%s.fa' % uid)
	mav = MAViewer(filename, autoAssociate=False)
	# loop over structures and make associations
	i = 0
	templateModels = []
	for s in structures[1:]:
		i += 1 # seqs[0] is the query sequence, which we don't want to associate with any model
		mol = s.models[0]
		templateModels.append(mol)
		actualseq = mav.seqs[i]
		mav.prematchedAssocStructure(actualseq, s.structseqobj, s.matchmap, 0, False, False, False) #slower: mav.associate([mol], seq = actualseq, force=True)
	return mav, templateModels


def openMod(path, uid, mav, templateModels, web=False):
	"""
	Opens Modeller window, selects all templates and sets MDA-specific default values 
	for nr. of models, thorough optimization and Output path.
	"""
	from os.path import join, exists
	from os import makedirs
	# default path for Modeller output models
	tempPath = join(path, 'Modeller_%s' % uid)
	if not exists(tempPath):
		makedirs(tempPath)		
	# function for calling the Modeller GUI
	def MODgui():
		# open Modeller dialogue
		mav._showModellerHomologyDialog()
		mod = mav.modellerHomologyDialog
		# default to only one output model
		mod.previousnumModel = 1
		mod.numModelEntry.setvalue(mod.previousnumModel)
		# default to thorough optimization being active
		mod.optimLabel.config(state='active')
		mod.optimVar.set(1)
		mod.optimCheckButton.config(state='active')
		# set Modeller path as specified by MDA
		mod.pathTempOpt.set(tempPath)
		# default to select all templates
		mod.tplTable.select(mod.candidateSeqs)
	MODgui()	

	
	
		
def main(results, uid, path, totseqlength, minscore = 50, includeNative = True, suppressdoubles = False, percentId = 0, group = False, hideSubmodels = True, hideComplex = False, hideAltChain = True, deleteHidden = True, coloring= 'mutations', winnow = '0', limit = '0', keepPDB = '', skipPDB = '', excludeSelected = False, showAlignment = True, noConfirm = False):
	
	"""
	Main mda routine, stepwise processing of different tasks:
	1) filters BLAST results and opens models (see processBlast()...)
	2) deletes or hides unwanted models/chains
	3) arranges models in space
	4) colors models
	5) opens MAV and Modeller
	"""

	import time
	tstart = time.time() # for performance optimization
	import chimera
	from chimera.replyobj import status
	from chimera.tkgui import app
	from chimera import update

	status('Fetching BLAST results completed, now filtering results and loading structures...')
	print('Fetching BLAST results completed, now filtering results and loading structures...')
	app.update()
	try:
		structures = processBlast(results, uid, path, minscore, includeNative, suppressdoubles, percentId, winnow, limit, keepPDB, skipPDB, excludeSelected, deleteHidden, hideSubmodels, noConfirm)
	except chimera.CancelOperation:
		status('MDA aborted by user.')
		print('MDA aborted by user.')
		return			

	status('Now updating model information...')
	print('Now updating model information...')
	update.checkForChanges() # this line is needed due to a Chimera bug that will otherwise let MDA crash since models are destroyed before changes to Python objects are updated
	app.update()

	status('Sorting items in model panel...')
	print('Sorting items in model panel...')
	destroyGroups()		
	groupSubModels()

	status('Now deleting/hiding alternate chains and/or extra submodels in multimodels...')
	print('Now deleting/hiding alternate chains and/or extra submodels in multimodels...')
	app.update()
	chimera.runCommand("modeldisp; ribbon")
	reduceModels(structures, hideSubmodels, hideComplex, hideAltChain, deleteHidden)

	status('Now arranging structures...')
	print('Now arranging structures...')
	app.update()
	boxes = createBoxes(structures)
	hideSimilar(boxes, uid, group) 
	closeSpheres()
	gaps = arrangeModelsX(boxes, structures, uid, totseqlength)
	chimera.runCommand("focus; ~set independent; savepos overlay") # use "reset overlay" to retrieve position where structures are not stacked in Y, before calling Modeller
	arrangeModelsY(boxes, gaps, hideComplex)

	status('Arranging completed, now applying coloring...')
	print('Arranging completed, now applying coloring...')
	app.update()
	setAttributes(structures)
	colorModels(structures, coloring)

	if showAlignment:
		status('Coloring completed, loading sequence alignment...')
		print('Coloring completed, loading sequence alignment...')
		app.update()
		mav, templateModels = openMAV(path, uid, structures)
		status('Now opening Modeller interface...')
		print('Now opening Modeller interface...')
		app.update()
		openMod(path, uid, mav, templateModels)

	chimera.runCommand("setattr p display 0; focus; set independent; savepos stacked; ~show") #~ions")   # use "reset stacked" to retrieve default position
	tend = time.time() # for performance optimization
	status('MDA completed after %d seconds.' % int(tend - tstart))
	print('MDA completed after %d seconds.' % int(tend - tstart))


	
	

def mda(uniprotId, path = '~/Desktop/', minScore = 50, includeNative = False, suppressDoubles = False, percentId = 0, forceBlast = False, group = False, hideSubmodels = True, hideComplex = False, hideAltChain = True, deleteHidden = True, coloring= 'mutations', winnow = '0', limit = '0', keepPDB = '', skipPDB = '', excludeSelected = False, showAlignment = True, noConfirm = False):
	
	"""
	Initial mda function, starts BLAST or reads stored BLAST database, then calls main().
	"""

	from os.path import expanduser, join, exists, isfile, splitext, split
	from os import makedirs
	from OpenSave import osOpen
	from chimera.tkgui import app

	# open reply log (crashes on windows if many models are opened with showAlignment false and reply log hidden)
	OpenReplyLog()
	
	# Convert ~/ to user's home directory for path where output file is stored
	path = expanduser(path)		
	
	# get path to where Chimera files are stored and create MDA folder
	from chimera.fetch import default_fetch_directory
	dbpath = join(default_fetch_directory(), 'MDA')
	dbpath = expanduser(dbpath)	
	if not exists(dbpath):
		makedirs(dbpath)
	if not exists(path):
		makedirs(path)	

	import chimera
	import shelve
	
	filenameblast = join(dbpath, 'MDA_blast')
	filenameseq = join(dbpath, 'MDA_seqs')
	print '\n- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -'
	print 'Starting MDA.'

	# destroy any open MAV instances (which also kills the corresponding Modeller interface)
	mavs = findMAV()
	for mavinst in mavs:
		print "Closing MAV instance."	
		mavinst.destroy()

	# check whether the uniprot ID is an existing file
	fasta = expanduser(uniprotId)
	if isfile(fasta):
		ID = split(splitext(fasta)[0])[1]
		print 'Reading "%s"' % fasta
		fastafile = osOpen(fasta, 'r')
		seq = ''
		seqcount = 0
		for line in fastafile:
			if seqcount > 1:
				print 'Skipping extra sequence(s) in file "%s."' % fasta
				break
			if line[0] != '>':
				seq += line.rstrip()
			else: 
				seqcount += 1
		print 'Query sequence read from fasta file "%s": %s' % (fasta, seq)
		forceBlast = True # ensure that no cached uniprot blasts are retrieved...
		storeblast = False
		print 'Assembling protein with sequence specified in fasta file %s.' % fasta
	elif len(uniprotId) == 6 or len(uniprotId) == 10: # make sure the user didn't just mess up a path or filename...
		storeblast = True
		ID = uniprotId	
		try: # look for stored sequence data
			seqshelf = shelve.open(filenameseq, 'c')
			seq = seqshelf[ID]
			seqshelf.close()
			print 'Reading stored sequence data...'
			print 'Assembling protein with UniProt ID: "%s."' % ID
		except KeyError: # get sequence and protein name from uniprot database
			print 'Fetching sequence data...'
			from SeqAnnotations import uniprotFetch, mapUniprotNameID, InvalidAccessionError
			try:
				Test = mapUniprotNameID(ID)
			except InvalidAccessionError:
				print 'Unknown uniprot ID! MDA aborted.'
				return	
			Protein = uniprotFetch(ID)
			seq = str(Protein[0])
			print 'Storing sequence data...'
			seqshelf[ID] = seq
			seqshelf.close()
	else:
		print '"%s" seems to be neither an existing fasta file nor a uniprot id. MDA aborted.' % uniprotId
		return		

	totseqlength = len(seq)
	if totseqlength >= 5000:
		print 'WARNING: Target protein has a large sequence length of %d aa. MDA might be slow; setting forceBlast = True.' % totseqlength
		app.update()
		forceBlast = True
		storeblast = False

	# callback after BLAST has produced results...
	def cb(params, output, storeblast=storeblast, uid = ID, filen = filenameblast, totseql = totseqlength, winnow = winnow, limit = limit):
		# split cb into cb and main because an additional argument needs to be passed to cb!
		results = (params, output)
		# save results to file
		if storeblast:
			blastshelf = shelve.open(filen, 'c')
			blastshelf[uid+winnow] = results
			blastshelf.close()
		# process the results:
		main(results, uid, path, totseql, minScore, includeNative, suppressDoubles, percentId, group, hideSubmodels, hideComplex, hideAltChain, deleteHidden, coloring, winnow, limit, keepPDB, skipPDB, excludeSelected, showAlignment, noConfirm)
		
	# blast function	
	def startBlast(querySeq = seq, winnow = winnow):		
		
		program = None
		db = "pdb"
		queryName = "MDAquery"
		evalue = "1000"
		matrix = "BLOSUM62"
		params = (program, db, queryName, querySeq, evalue, matrix, winnow)
		print 'Running BLAST using %s matrix...' % matrix

		def failCB():
			print "failed"
		def cancelCB():
			print "cancelled"
		bp29 = MDABlastpService(cb, params=params,
					failCB=failCB, cancelCB=cancelCB)
			
	if not forceBlast:	
		blastshelf = shelve.open(filenameblast, 'c')
		try:
			results = blastshelf[ID+winnow]
			blastshelf.close()
			print 'Reading stored BLAST data...'
		except KeyError:
			blastshelf.close()
			startBlast()
		else:	
			main(results, ID, path, totseqlength, minScore, includeNative, suppressDoubles, percentId, group, hideSubmodels, hideComplex, hideAltChain, deleteHidden, coloring, winnow, limit, keepPDB, skipPDB, excludeSelected, showAlignment, noConfirm)
	else:
		startBlast()	


from blastpdb.ParserBlastP import BlastpService
class MDABlastpService(BlastpService):
	ServiceName = "MDABlastpService"
        def makeArgList(self, *args):
                argList = BlastpService.makeArgList(self, *args)
                winnow = self.params[-1]
                if winnow != '0':
                        argList += " -c %s" % winnow
                return argList

def mdacommand(cmdname, args):
	"""
	Helps registering the command in chimera.
	"""
	from Commands import parse_arguments
	from Commands import string_arg, float_arg, bool_arg, int_arg
	req_args = ( ('uniprotId', string_arg), )
	opt_args = ( ('path', string_arg), )
	kw_args = (	('minScore', float_arg),		
				('includeNative', bool_arg),
				('forceBlast', bool_arg),
				('suppressDoubles', bool_arg),
				('percentId', float_arg), 
				('group', bool_arg), 
				('hideSubmodels', bool_arg),
				('hideComplex', bool_arg), 
				('hideAltChain', bool_arg), 
				('deleteHidden', bool_arg), 
				('coloring', string_arg),
				('winnow', string_arg),
				('limit', string_arg), 
				('keepPDB', string_arg),
				('skipPDB', string_arg),
				('excludeSelected', bool_arg),
				('showAlignment', bool_arg),
				('noConfirm', bool_arg) ) 
	kw = parse_arguments(cmdname, args, req_args, opt_args, kw_args)
	mda(**kw)

# add mda command to chimera				
from Midas.midas_text import addCommand
addCommand('mda', mdacommand, help = True)
