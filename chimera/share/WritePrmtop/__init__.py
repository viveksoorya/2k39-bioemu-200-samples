import chimera
from chimera.idatm import typeInfo
from chimera.selection import Selection, ItemizedSelection

def noGaffComplain(noGaff, toolName):
	noGaffByRes = {}
	for a in noGaff:
		noGaffByRes.setdefault(a.residue, []).append(a)
	if chimera.nogui:
		raise ValueError("Cannot determine GAFF type for %s (etc.)" % noGaff[0])
	errMsg = "%s atom%s did not get GAFF atom-type assignments." % (len(noGaff),
		"s" if len(noGaff) > 1 else "")
	if len(noGaffByRes) > 10:
		errMsg += "  They are listed in the reply log."
	else:
		errMsg += "  They are listed below and in the reply log."
	if len(noGaff) == len([a for a in noGaff if a.element.number == 1]):
		errMsg += "  The atoms are all hydrogens, which typically occurs" \
			" when some of the standard residues in your structure are" \
			" incomplete.  One way to remedy this is to use the Dock Prep" \
			" tool (in the Structure Editing category) to complete partial" \
			" side chains.  If main-chain atoms are missing, either deleting" \
			" the entire residue or just the non-standard hydrogens might be" \
			" appropriate, depending on the structure.  Once you have dealt" \
			" with the partial residues then you could re-run %s.\n" % toolName
	else:
		errMsg += "  Some or all of the atoms are heavy (non-hydrogen) atoms." \
			"  If they are in residues that aren't critical to your computation" \
			" you could delete them and then re-run %s.\n" % toolName
	if len(noGaffByRes) <= 10:
		errMsg += "\n"
		for r, atoms in noGaffByRes.items():
			errMsg += "\t%s %s\n" % (r, ", ".join([a.name for a in atoms]))
	from chimera import replyobj
	replyobj.error(errMsg)
	replyobj.info("Residues/atoms missing GAFF types:\n")
	for r, atoms in noGaffByRes.items():
		replyobj.info("\t%s %s\n" % (r, ", ".join([str(a) for a in atoms])))


def writeLeaprc(tempDir, topfile,  parmset, leaprc ) :
	import os, sys
	if sys.platform == "win32":
		# Windows needs special help if 'topfile' contains Unicode
		import codecs
		f = codecs.open( leaprc, 'w', 'utf8' )
	else:
		f = open( leaprc, 'w' )
	from AddCharge import oldChargeModels, oldLeapDir
	if ("AMBER " + parmset) in oldChargeModels:
		loc = oldLeapDir + '/'
	else:
		loc = ""
	f.write( ("source %sleaprc." % loc) + parmset + "\n" )
	f.write( "source leaprc.gaff\n" )
        f.write( "set default rearrangeResidue on\n" )
	f.write( "tmp = loadmol2 " + os.path.join(tempDir, "sleap.in.mol2\n") )
	f.write( "parmchk tmp\n" )
	if topfile.endswith(".prmtop"):
		crdfile = topfile[:-7] + ".inpcrd"
	else:
		crdfile = topfile + ".inpcrd"
	if ' ' in topfile:
		if '"' in topfile:
			topfile = "'" + topfile + "'"
			crdfile = "'" + crdfile + "'"
		else:
			topfile = '"' + topfile + '"'
			crdfile = '"' + crdfile + '"'
	f.write( "saveamberparm tmp " + topfile + " " + crdfile + "\n" )
	f.write( "quit\n" )
	f.close()



def writePrmtop(m, topfile, parmset, unchargedAtoms=None):
	import os
	import chimera
	from chimera import replyobj
	from WriteMol2 import writeMol2
	from tempfile import mkdtemp

	status = replyobj.status

	if unchargedAtoms and parmset.lower().endswith("ua"):
		# united atom
		replyobj.warning("Some uncharged/untyped protons expected due"
			" to use of united-atom force field.\n")
		unchargedHeavy = {}
		skip = []
		for key, uncharged in unchargedAtoms.items():
			for uc in uncharged:
				if uc.element.number == 1:
					skip.append(uc)
				else:
					unchargedHeavy.setdefault(key, []).append(uc)
		unchargedAtoms = unchargedHeavy
	else:
		skip = []
	# some charged atoms can lack GAFF types (e.g. some metal ions)
	noGaff = [a for a in m.atoms if not hasattr(a, 'gaffType') and a not in skip]
	if noGaff:
		noGaffComplain(noGaff, "Write Prmtop")
		return

	tempDir = mkdtemp()
	def _clean():
		# parmchk can generate a .parmchk subdir, so...
		for dirpath, dirnames, filenames in os.walk(tempDir, topdown=False):
			for fn in filenames:
				os.unlink(os.path.join(dirpath, fn))
			os.rmdir(dirpath)

	sleapIn = os.path.join(tempDir, "sleap.in.mol2")
	writeMol2([m], sleapIn, status=status, gaffType=True, skip=skip,
		temporary=True)

	leaprc = os.path.join(tempDir, "solvate.cmd")
	writeLeaprc(tempDir, topfile, parmset, leaprc)

	from AmberInfo import amberBin, amberHome
	command = [os.path.join(amberBin, "sleap"), "-f", leaprc]
	
	print 'command: ', command
	if status:
		status("Running sleap" )
	from subprocess import Popen, STDOUT, PIPE
	replyobj.info("Running sleap command: %s\n" % " ".join(command))
	import os
	os.environ["AMBERHOME"]=amberHome
	#os.environ["ACHOME"]=acHome
	sleapMessages = Popen(command, stdin=PIPE, stdout=PIPE, stderr=STDOUT,
			cwd=tempDir, bufsize=1).stdout
	while True:
		line = sleapMessages.readline()
		if not line:
			break
		replyobj.status("(writeprmtop) %s" % line, log=True)
	if not os.path.exists(topfile):
		from chimera import NonChimeraError
		raise NonChimeraError("Failure running sleap \n"
			"Check reply log for details\n")
	else:
		_clean()
		replyobj.status("Wrote parmtop file %s" % topfile, log=True)

