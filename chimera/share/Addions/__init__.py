from chimera import replyobj

ValidIonTypes = {
	"Ag+": "AG", "Al3+": "AL", "Ag2+": "Ag", "Ba2+": "BA", "Br-": "BR",
	"Be2+": "Be", "Ca2+": "CA", "Cd2+": "CD", "Ce3+": "CE", "Cl-": "CL",
	"Co2+": "CO", "Cr3+": "CR", "Cs+": "CS", "Cu2+": "CU", "Cu+": "CU1",
	"Ce3+": "Ce", "Cr2+": "Cr", "Dy3+": "Dy", "Eu2+": "EU", "Eu3+": "EU3",
	"Er3+": "Er", "F-": "F", "Fe3+": "FE", "Fe2+": "FE2", "Gd3+": "GD3",
	"H3O+": "H3O+", "H+ (HE+)": "HE+", "Hg2+": "HG", "H+ (HZ+)": "HZ+",
	"Hf4+": "Hf", "In3+": "IN", "I-": "IOD", "K+": "K", "La3+": "LA",
	"Li+": "LI", "Lu3+": "LU", "Mg2+": "MG", "Mn2+": "MN", "Na+": "NA",
	#"NH4+": "NH4", sleap doesn't seem to treat as ion, outputs after solvent
	"Ni2+": "NI", "Nd3+": "Nd", "Pb2+": "PB", "Pd2+": "PD",
	"Pr3+": "PR", "Pt2+": "PT", "Pu4+": "Pu", "Rb+": "RB", "Ra2+": "Ra",
	"Sm3+": "SM", "Sr2+": "SR", "Sm2+": "Sm", "Sn2+": "Sn", "Tb3+": "TB",
	"Tl+": "TL", "Th4+": "Th", "Tl3+": "Tl", "Tm3+": "Tm", "U4+": "U4+",
	"V2+": "V2+", "Y3+": "Y", "Yb2+": "YB2", "Zn2+": "ZN", "Zr4+": "Zr"
}

def writeLeaprc(tempDir, iontype, numion, leaprc ) :
	import os
	f = open( leaprc, 'w' )

	#f.write( "source leaprc.ff03.r1\n" )
	f.write( "source oldff/leaprc.ff14SB\n" )
	f.write( "tmp = loadmol2 " + os.path.join(tempDir, "sleap.in.mol2\n") )
      
        if numion=="neutralize":
	    f.write( "addions tmp " + iontype + " 0\n" )
        else:
            f.write( "addions tmp " + iontype + " " + numion + "\n" )

	f.write( "savemol2 tmp " + os.path.join(tempDir, "sleap.out.mol2\n") )
	f.write( "quit\n" )

def is_solvent(r):
	if len(r.atoms) > 5:
		return False
	for a in r.atoms:
		for n in a.neighbors:
			if n.residue !=r:
				return False

	return True

def get_solute_nresd(m):

    i=len(m.residues)-1

    while i>=0 and is_solvent(m.residues[i]):
        i -= 1

    return i+1
    


def initiateAddions(models, iontype, numion, status):
	import os
	import chimera
	from chimera import replyobj
	from chimera.molEdit import addAtom
	from WriteMol2 import writeMol2
	from tempfile import mkdtemp

	for m in models:
		if m.__destroyed__:
			continue

		noGaff = [a for a in m.atoms if not hasattr(a, 'gaffType')]
		if noGaff:
			from WritePrmtop import noGaffComplain
			noGaffComplain(noGaff, "Add Ions")
			continue

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
		writeMol2([m], sleapIn, status=status, gaffType=True, relModel=m,
			temporary=True)

		leaprc = os.path.join(tempDir, "solvate.cmd")
		writeLeaprc(tempDir, iontype, numion, leaprc)

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
			replyobj.status("(addions) %s" % line, log=True)
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
		solute_nresd = get_solute_nresd(m)


		inAtoms = m.atoms
		outAtoms = outm.atoms
		status("Correlating sleap output with Chimera structure")
		# sort input atoms into order they were written to mol2 file...
		from WriteMol2 import writeMol2Sort
		inAtoms.sort(lambda a1, a2, ri={}: writeMol2Sort(a1, a2, resIndices=ri))
		# sort output atoms into order they were read from mol2 file...
		serialSort = lambda a1, a2: cmp(a1.coordIndex, a2.coordIndex)
		outAtoms.sort(serialSort)

		state = "before ions"
		oi = 0
		preserveOut = []
		knockedOutIons = set()
		resTypeInfo = {}
		def findRtype(rname):
			rend = len(rname)
			while rend > 1 and rname[rend-1].isdigit():
				rend -= 1
			if rend < len(rname) and rname[rend-1] == '-':
				# possible for negative sequence number
				# but check possible negative ion...
				from chimera.elements import halides
				if rname[:rend-1].capitalize() not in [e.name for e in halides]:
					rend -= 1
			return rname[:rend], rend
		for inAtom in inAtoms:
			try:
				outAtom = outAtoms[oi]
			except IndexError:
				if state in ["water", "old ions"]:
					# adding ions may have deleted waters and/or pre-existing ions
					preserveOut += [None] * (len(inAtoms) - len(preserveOut))
					break
				raise
			rtypes = []
			for rname in (inAtom.residue.type, outAtom.residue.type):
				rtype, rend = findRtype(rname)
				rtypes.append(rtype)
			if rend < len(rname):
				resTypeInfo[outAtom] = (rtypes[-1], int(rname[rend:]))
			same = inAtom.name == outAtom.name and rtypes[0] == rtypes[1]
			if state == "before ions":
				if same:
					preserveOut.append(outAtom)
					oi += 1
					continue
				ionCheck = iontype.lower()
				while len(ionCheck) > 1 and not ionCheck.isalpha():
					ionCheck = ionCheck[-1]
				state = "new ions"
			if state == "new ions":
				#while outAtom.name[-1] in "+-":
				while outAtom.name.lower().startswith(ionCheck):
					oi += 1
					outAtom = outAtoms[oi]
				state = "old ions"
				rname = outAtom.residue.type
				rtype, rend = findRtype(rname)
				rtypes[1] = rtype
				if rend < len(rname):
					resTypeInfo[outAtom] = (rtype, int(rname[rend:]))
				same = inAtom.name == outAtom.name and rtypes[0] == rtypes[1]
			if state == "old ions":
				# sometimes old ions not in ions surface category;
				# assume ion if res name starts with same string as atom name
				# and has no other alphabetic characters
				if inAtom.residue.type.startswith(inAtom.name) \
				and len([c for c in inAtom.residue.type[len(inAtom.name):]]) == 0:
					if same:
						preserveOut.append(outAtom)
						oi += 1
						continue
					else:
						# pre-existing ions can be knocked out by new ones
						knockedOutIons.add(inAtom.residue)
						continue
				state = "water"
				rname = outAtom.residue.type
				rtype, rend = findRtype(rname)
				rtypes[1] = rtype
				if rend < len(rname):
					resTypeInfo[outAtom] = (rtype, int(rname[rend:]))
				same = inAtom.name == outAtom.name and rtypes[0] == rtypes[1]
			if state == "water":
				if rtypes[0] in ("HOH", "WAT"):
					if same:
						oi += 1
					preserveOut.append(None)
					continue
				state = "hydrogens"
			if state == "hydrogens":
				if not same:
					if inAtom.name[0].isdigit() \
					and inAtom.name[1:] + inAtom.name[0] == outAtom.name:
						same = rtypes[0] == rtypes[1]
				if same:
					if rtypes[1] in ("HOH", "WAT"):
						preserveOut.append(None)
					else:
						preserveOut.append(outAtom)
					oi += 1
					continue
				if rtypes[0] == "HOH":
					preserveOut.append(None)
					continue
				raise ValueError("Cannot match sleap output with Chimera structure")
		assert(len(inAtoms) == len(preserveOut))

		# sleap repositions solute...
		if status:
			status("Translating %d atoms" % len(inAtoms))
		for inA, outA in zip(inAtoms, preserveOut):
			if outA == None:
				continue
			inA.setCoord(outA.coord())

		if status:
			status( "Deleting old solvents" )
		while len(m.residues) > solute_nresd:
			m.deleteResidue( m.residues[solute_nresd] )

		if knockedOutIons:
			if status:
				status("Removing %d pre-existing ion residues knocked out by new ions"
					% len(knockedOutIons))
			for ko in knockedOutIons:
				m.deleteResidue(ko)

		from AddCharge import ionTypes
		final = outm.residues[-1]
		for r in outm.residues[solute_nresd:]:
			solvIonNum = r.id.position - solute_nresd
			if status and solvIonNum % 1000 == 0:
				status("Creating ion/solvent residue %d " % solvIonNum)

			atomMap = {}
			if r.atoms[0] in resTypeInfo:
				rtype, pos = resTypeInfo[r.atoms[0]]
				nr = m.newResidue(rtype, ' ', pos, ' ')
			else:
				nr = m.newResidue(r.type, ' ', 1, ' ')
			for a in r.atoms:
				na = addAtom(a.name, a.element, nr, a.coord(),
							serialNumber=a.serialNumber)
				na.charge = a.charge

				if len(a.neighbors)==0:
					na.drawMode = chimera.Atom.Sphere

				atomMap[a] = na

				from chimera import elements
				for elementName in [a.name[:2].capitalize(), a.name[0]]:
					if hasattr(elements, elementName):
						na.element = getattr(elements, elementName)
						break
				else:
					if a.name == "EPW":
						na.element = elements.LP
					else:
						raise ValueError("Cannot determine atomic element from atom name '%s'"
							% a.name)
				if na.element.name in ionTypes:
					na.gaffType = ionTypes[na.element.name]
				else:
					na.gaffType = a.mol2type

			for a in r.atoms:
				na = atomMap[a]
				for n in a.neighbors:
					assert n.residue == r
					nn = atomMap[n]
					if nn in na.bondsMap:
						continue
					m.newBond(na, nn)

			if status and r == final:
				status("Created %d ion/solvent residues" % solvIonNum)
		_clean()

def test():
	import chimera
	models = chimera.openModels.list()
	iontype = "Cl-"
	numion = "4"
	status = chimera.replyobj.status
	initiateAddions(models, method, solvent, extent, center, status)
