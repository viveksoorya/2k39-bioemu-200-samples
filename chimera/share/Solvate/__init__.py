from chimera import replyobj

ValidSolventShapes = ("cap", "box", "oct", "shell" )

ValidSolventModels = ("CHCL3BOX", "MEOHBOX", "NMABOX", "POL3BOX",
	"QSPCFWBOX", "SPCBOX", "SPCFWBOX",  "TIP3PBOX",
	"TIP3PFBOX", "TIP4PBOX", "TIP4PEWBOX")

def writeLeaprc(tempDir, method, solvent, extent, center, leaprc) :
	import os
	f = open( leaprc, 'w' )

	f.write( "source leaprc.ff03.r1\n" )
	f.write( "tmp = loadmol2 " + os.path.join(tempDir, "sleap.in.mol2\n") )

	if method=="cap" or method=="Cap":
		f.write( "solvatecap tmp " + solvent + " tmp." + center + " "  + extent + "\n" )
	else:
		f.write( "solvate" + method + " tmp " + solvent + " " + extent + "\n" )

	f.write( "savemol2 tmp " + os.path.join(tempDir, "sleap.out.mol2\n") )
	f.write( "quit\n" )




def initiateSolvate(models, method, solvent, extent, center, status):
    import os
    import chimera
    from chimera import replyobj
    from chimera.molEdit import addAtom
    from WriteMol2 import writeMol2
    from tempfile import mkdtemp

    for m in models:
	tempDir = mkdtemp()

	def _clean():
		for fn in os.listdir(tempDir):
			os.unlink(os.path.join(tempDir, fn))
		try:
			os.rmdir(tempDir)
		except WindowsError, v:
			# ignore inexplicable "sharing violation" errors
			# ("file in use by another process")
			if v.winerror != 32:
				raise

	sleapIn = os.path.join(tempDir, "sleap.in.mol2")
	sleapOut= os.path.join(tempDir, "sleap.out.mol2")
	writeMol2([m], sleapIn, status=status, relModel=m, temporary=True)

	leaprc = os.path.join(tempDir, "solvate.cmd")
	writeLeaprc(tempDir, method, solvent, extent, center, leaprc)

	from AmberInfo import amberHome, amberBin
	command = [os.path.join(amberBin, "sleap"), "-f", leaprc]

	if status:
		status("Running sleap" )
	from subprocess import Popen, STDOUT, PIPE
	replyobj.info("Running sleap command: %s\n" % " ".join(command))
	import os
	os.environ["AMBERHOME"]=amberHome
	sleapMessages = Popen(command, stdin=PIPE, stdout=PIPE, stderr=STDOUT,
			cwd=tempDir, bufsize=1).stdout
	while True:
		line = sleapMessages.readline()
		if not line:
			break
		replyobj.status("(solvate) %s" % line, log=True)
	if not os.path.exists(sleapOut):
		_clean()
		from chimera import NonChimeraError
		raise NonChimeraError("Failure running sleap \n"
			"Check reply log for details\n")
	if status:
		status("Reading sleap output")
	from chimera import Mol2io, defaultMol2ioHelper
	mol2io = Mol2io(defaultMol2ioHelper)
	mols = mol2io.readMol2file(sleapOut)
	if not mol2io.ok():
		_clean()
		raise IOError(mol2io.error())
	if not mols:
		_clean()
		raise RuntimeError("No molecules in sleap output")

        assert len(mols)==1

	outm = mols[0]
	natom = len(m.atoms)
	nresd = len(m.residues)
	inAtoms = m.atoms
	outAtoms = outm.atoms
	# sort input atoms into writeMol2 order
	# sort output atoms into input order
	from WriteMol2 import writeMol2Sort
	inAtoms.sort(lambda a1, a2, ri={}: writeMol2Sort(a1, a2, resIndices=ri))
	outSort = lambda a1, a2: cmp(a1.coordIndex, a2.coordIndex)
	outAtoms.sort(outSort)

	if status:
		status("Translating %d atoms" % len(inAtoms))
	for inA, outA in zip(inAtoms, outAtoms[:len(inAtoms)]):
		inA.setCoord(outA.coord())
	
	# added solvent hydrogens may not have been categorized yet, so use
	# this less obvious way of gathering solvent atoms...
	existingSolvent = set()
	from chimera.elements import metals, alkaliMetals
	nonAlkaliMetals = metals - alkaliMetals
	for r in m.residues:
		if len(r.atoms) == 1 and r.atoms[0].element in nonAlkaliMetals:
			continue
		for a in r.atoms:
			if a.surfaceCategory in ["solvent", "ions"]:
				existingSolvent.update(r.atoms)
				break

	# copy mol2 comment which contain the info of the solvent: shape, size, etc
	if hasattr( outm, "mol2comments" ) and len(outm.mol2comments) > 0:
		m.solventInfo = outm.mol2comments[0]


	if existingSolvent:
		solventCharges = {}
		solventTypes = {}
	final = outm.residues[-1]
	for r in outm.residues[nresd:]:
		solventNum = r.id.position - nresd
		if status and solventNum % 1000 == 0:
			status("Creating solvent residue %d " % solventNum )

		atomMap = {}
		nr = m.newResidue(r.type, ' ', solventNum, ' ')
		# mark residue for exclusion by AddCharge...
		nr._solvateCharged = True
		for a in r.atoms:
			na = addAtom(a.name, a.element, nr, a.coord(),
						serialNumber=a.serialNumber)
			na.charge = a.charge
			na.gaffType = a.mol2type
			atomMap[a] = na
			if a.name[0]=="H": na.element = 1
			if a.name[0]=="C": na.element = 6
			if a.name[0]=="N": na.element = 7
			if a.name[0]=="O": na.element = 8
			if a.name[0]=="P": na.element = 15
			if a.name[0]=="S": na.element = 16
			if a.name[0:2] in ["Cl", "CL"]: na.element = 17
			if existingSolvent:
				solventCharges[(r.type, a.name)] = a.charge
				solventTypes[(r.type, a.name)] = a.mol2type
				if r.type == "WAT":
					solventCharges[("HOH", a.name)] = a.charge
					solventTypes[("HOH", a.name)] = a.mol2type


		for a in r.atoms:
			na = atomMap[a]
			for n in a.neighbors:
				assert n.residue == r
				nn = atomMap[n]
				if nn in na.bondsMap:
					continue
				m.newBond(na, nn)

		if status and r == final:
			status("Created %s solvent residues" % solventNum )
	
	if existingSolvent:
		unknowns = set()
		for sa in existingSolvent:
			key = (sa.residue.type, sa.name)
			try:
				sa.charge = solventCharges[key]
				sa.gaffType = solventTypes[key]
			except KeyError:
				unknowns.add(key)
			sa.residue._solvateCharged = True
		if unknowns:
			if solventCharges:
				replyobj.warning("Could not determine charges for"
					" pre-existing solvent/ions from added solvent"
					"/ions for: %s\n" % ", ".join([" ".join(x)
					for x in unknowns]))
			else:
				replyobj.warning("No solvent was added and therefore"
					" couldn't determine charges appropriate to"
					" solvent model to apply to existing solvent.\n")
	_clean()
				
    if models:
	from Midas import window
	window(models)
    else:
    	replyobj.warning("No atoms/models remaining to solvate!")

def test():
	import chimera
	models = chimera.openModels.list()
	method = "Box"
	solvent = "POL3BOX"
	extent = "4"
	center = ""
	status = chimera.replyobj.status
	initiateSolvate(models, method, solvent, extent, center, status)
