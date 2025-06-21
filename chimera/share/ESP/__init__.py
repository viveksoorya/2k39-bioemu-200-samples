# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: __init__.py 42286 2021-04-29 15:53:49Z pett $

from chimera import replyobj, LimitationError

defaultVolumeName = "Coulombic ESP"

def colorEsp(surf, colors, vals, dielectric=4.0, distDep=True, surfDist=1.4,
							hisScheme="HID", volumeParams=None, atoms=None):
	from chimera import MaterialColor
	if isinstance(colors[0], MaterialColor):
		colors = [mc.rgba() for mc in colors]
	if len(colors) != len(vals) and len(colors) != len(vals)+2:
		raise ValueError("Number of colors (%d) must be the same as"
			" number of values or number of values +2 (%d, %d)"
			% (len(colors), len(vals), len(vals) + 2))
	# are charges available?
	# don't use checkNoCharges() since that may add hydrogens and
	# therefore change surface
	if atoms is None:
		atoms = surf.atoms    
	if not atoms:
		raise LimitationError("Molecule associated with surface is closed;"
			" cannot compute coulombic potential")
	elif atoms[0].name == "CA" and len(atoms[0].residue.atoms) == 1:
		elements = set([a.element.name for a in atoms])
		if len(elements) == 1 and elements.pop() == "C":
			residues = set([a.residue for a in atoms])
			if len(residues) == len(atoms):
				raise LimitationError("Cannot compute potential for"
					" carbon-alpha-only structure; all heavy atoms must be present")
	
	#Check if charges need to be recomputed:
	numAtoms = len(atoms)
	for a in atoms:
		if getattr(a, '_espParams', (hisScheme, numAtoms)) != (hisScheme, numAtoms):
			# clear charge so that histidines get new charges
			a.charge = None
	try:
		# are charges missing or None?
		[a.charge + 1.0 for a in atoms]
	except (AttributeError, TypeError):
		_chargeAtoms(atoms, hisScheme)
		for a in atoms:
			a._espParams = (hisScheme, numAtoms)
	
	replyobj.status("Computing electrostatics")
	from _multiscale import get_atom_coordinates
	coords = get_atom_coordinates(atoms)
	import numpy
	charges = numpy.array([a.charge for a in atoms])
	from _esp import computeEsp
	for piece in surf.surfacePieces:
		vertices, triangles = piece.geometry
		normals = piece.normals
		potentials = computeEsp(vertices, normals, coords, charges,
			dielectric=dielectric, distDep=distDep, surfDist=surfDist)
		belowColor = colors[0]
		aboveColor = colors[-1]
		if len(colors) == len(vals) + 2:
			colors = colors[1:-1]
		from SurfaceColor import interpolate_colormap
		rgbas = interpolate_colormap(potentials, vals, colors, aboveColor,
								belowColor)
		from Surface import set_coloring_method
		set_coloring_method('ESP coloring', surf, None)
		#replyobj.status("Coloring surface")
		piece.vertexColors = rgbas
		piece.using_surface_coloring = True
	replyobj.status("Surface colored")

	if not volumeParams:
		return
	replyobj.status("Computing volume")
	spacing, padding, mapName = volumeParams
	minXyz = numpy.min(coords, axis=0) - [padding+spacing/2.0]*3
	maxXyz = numpy.max(coords, axis=0) + [padding+spacing/2.0]*3
	xrange = numpy.arange(minXyz[0], maxXyz[0], spacing)
	yrange = numpy.arange(minXyz[1], maxXyz[1], spacing)
	zrange = numpy.arange(minXyz[2], maxXyz[2], spacing)
	mapVertices = numpy.array([(x,y,z)
		for x in xrange for y in yrange for z in zrange])
	mapPotentials = computeEsp(mapVertices, [], coords, charges,
		dielectric=dielectric, distDep=distDep, surfDist=0.0)
	mapPotentials.shape = (len(xrange), len(yrange), len(zrange))

	replyobj.status("Showing volume")
	from VolumeData import Array_Grid_Data
	gd = Array_Grid_Data(mapPotentials.transpose(), minXyz, [spacing]*3)
	gd.polar_values = True # negative value are of interest
	gd.name = mapName
	import VolumeViewer
	dataRegion = VolumeViewer.volume_from_grid_data(gd, show_dialog=True,
													show_data=False)

	from SurfaceColor.gui import show_surface_color_dialog as sscd
	scd = sscd()
	scd.use_electrostatics_colormap()
	scd.surface_menu.setvalue(surf)
	scd.volume_menu.set_volume(dataRegion)

	replyobj.status("Volume shown")

def _chargeAtoms(atoms, hisScheme):
	# add charges to these atoms w/o adding hydrogens directly to them;
	# probably requires copying

	if len(set(a.molecule for a in atoms)) > 1:
		raise LimitationError("Cannot compute potential for atoms from multiple models")

	replyobj.status("Copying molecule")
	from Combine import combine
	mol = atoms[0].molecule
	atomMap, copyMol = combine([mol], mol, returnMapping=True)
	copied = set()
	numHyds = 0
	for a in atoms:
		if a.element.number == 1:
			numHyds += 1
		copied.add(atomMap[a])

	replyobj.status("Adding hydrogens to copy")
	from chimera.idatm import typeInfo
	exotic = [a for a in atoms if a.idatmType not in typeInfo]
	unknownsInfo = dict.fromkeys(exotic, {'geometry':0, 'substituents': 0})
	from AddH import simpleAddHydrogens, hbondAddHydrogens
	hbfunc = simpleAddHydrogens
	if type(hisScheme) == dict:
		hisInfo = {}
		for origR, handling in hisScheme.items():
			# scheme may include histidines from other molecules, so check
			if origR.molecule != mol:
				continue
			hisInfo[atomMap[origR.atoms[0]].residue] = handling
	elif hisScheme == None:
		hbfunc = hbondAddHydrogens
		hisInfo = None
	else:
		hisInfo = dict.fromkeys([r for r in copyMol.residues
						if r.type == "HIS"], hisScheme)
	if numHyds * 3 < len(atoms):
		hbfunc([copyMol], inIsolation=True, unknownsInfo=unknownsInfo,
			hisScheme=hisInfo)

	replyobj.status ("Adding charges to copy")
	# treat MSEs as MET
	for r in copyMol.residues:
		if r.type != "MSE":
			continue
		for a in r.atoms:
			if a.element.name == "Se":
				a.name = "SD"
				r.type = "MET"
	from AddCharge import addStandardCharges, addNonstandardResCharges, \
						estimateNetCharge, ChargeError
	unchargedResidues, unchargedAtoms = addStandardCharges(models=[copyMol],
				status=replyobj.status, phosphorylation=False)
	for uaList in unchargedAtoms.values():
		for ua in uaList:
			if ua in copied:
				ua.charge = 0.0
	if copied.intersection(unchargedAtoms):
		replyobj.error("Some atoms were not assigned charges.\n"
			"For more accurate results you should run the Add Charge\n"
			"tool and then rerun this tool.\n")

	for resType, residues in unchargedResidues.items():
		residues = [r for r in residues if r.atoms[0] in copied]
		if not residues:
			continue
		try:
			addNonstandardResCharges(residues, estimateNetCharge(
				residues[0].atoms), status=replyobj.status,
				gaffType=False)
		except ChargeError:
			copyMol.destroy()
			raise LimitationError("Cannot automatically determine"
				" charges for residue %s;\nRun AddCharge tool"
				" manually to add charges and then rerun ESP"
				% resType)

	replyobj.status("Mapping copy charges back to original")
	try:
		chargeSum = 0.0
		for oa in atoms:
			ca = atomMap[oa]
			charge = ca.charge
			for nb in ca.neighbors:
				if len(nb.neighbors) == 1 and nb not in copied:
					charge += nb.charge
			oa.charge = charge
			chargeSum += charge
		mol.chargeModel = copyMol.chargeModel
	finally:
		copyMol.destroy()

def cmdColorEsp(cmdName, args):
	from Midas.midas_text import MidasError, parseColorName, getSpecs	
	from Midas import evalSpec
	from chimera.colorTable import getColorByName
	from prefs import defaults, GRID_SPACING, GRID_PADDING
	mode = "keywords"
	colors = []
	values = []
	kw = {'hisScheme': None}
	showKey = False
	insufficientValsError = MidasError(
				"%s: at least two value/color pairs required" % cmdName)
	volumeParams = None
	while mode != "atom spec":
		if mode == "keywords":
			fields = args.split(None, 1)
			if len(fields) < 2:
				raise insufficientValsError
			keyword = fields[0].lower()
			vpPos = None
			if "atoms".startswith(keyword):
				keyword = "atoms"
				def parseatoms(spec):					
					return evalSpec(getSpecs(spec)).atoms()
				vtype = parseatoms
			elif "dielectric".startswith(keyword):
				keyword = "dielectric"
				vtype = float
			elif "distdep".startswith(keyword):
				keyword = "distDep"
				vtype = lambda x: bool(eval(x.capitalize()))
			elif "surfdist".startswith(keyword):
				keyword = "surfDist"
				vtype = float
			elif "hisscheme".startswith(keyword):
				keyword = "hisScheme"
				vtype = str
			elif "key".startswith(keyword):
				showKey = True
				args = fields[1]
				continue
			elif "gspacing".startswith(keyword):
				keyword = "gspacing"
				vpPos = 0
				vtype = float
			elif "gpadding".startswith(keyword):
				keyword = "gpadding"
				vpPos = 1
				vtype = float
			elif "gname".startswith(keyword):
				keyword = "gname"
				vpPos = 2
				vtype = unicode
			else:
				mode = "color values"
				continue
			try:
				valStr, args = fields[1].split(None, 1)
			except ValueError:
				raise MidasError("%s: at least two value/color pairs required"
					% cmdName)
			try:
				val = vtype(valStr)
			except ValueError:
				raise MidasError("Argument for %s (%s) is wrong type" %
					(keyword, valStr))
			except NameError:
				raise
				raise MidasError("Value must be 'true' or 'false'")
			if keyword == "hisScheme":
				uval = val.upper()
				if uval == "NONE":
					val = None
				elif uval in ["HID", "HIE", "HIP"]:
					val = uval
				else:
					raise MidasError("Value for '%s' must be HID, HIE, HIP"
						" or none" % keyword)
			elif vpPos != None:
				if volumeParams == None:
					volumeParams = [defaults[GRID_SPACING],
									defaults[GRID_PADDING], defaultVolumeName]
				volumeParams[vpPos] = val
				continue
			kw[keyword] = val
			continue
		kw["volumeParams"] = volumeParams
		# mode == color values
		try:
			valStr, rem = args.split(None, 1)
		except ValueError:
			if len(values) < 2:
				raise insufficientValsError
			else:
				mode = "atom spec"
				continue
		try:
			val = float(valStr)
		except ValueError:
			if len(values) < 2:
				raise insufficientValsError
			else:
				mode = "atom spec"
				continue
		cn, rem = parseColorName(rem)
		from Midas import convertColor
		try:
			rgba = convertColor(cn).rgba()
		except (RuntimeError, AttributeError):
			if len(values) < 2:
				raise insufficientValsError
			else:
				mode = "atom spec"
				continue
		args = rem
		colors.append(rgba)
		values.append(val)

        # Find specified surfaces and also those associated with specified atoms.
	from chimera import openModels as om, MSMSModel
	from _surface import SurfaceModel
        sel = evalSpec(getSpecs(args))
        msurfs = []
        for m in sel.molecules():
                msurfs.extend(om.list(id = m.id, subid = m.subid, modelTypes = [MSMSModel]))
        atoms = set(sel.atoms())
        surfs = set(s for s in msurfs if not atoms.isdisjoint(s.atoms))
        haveSurfSpec = not (args.strip() == '')
        if haveSurfSpec or 'atoms' in kw:
                surfs.update(m for m in sel.models() if isinstance(m, SurfaceModel))

        # Check if atoms were specified.
	if "atoms" in kw:
		if len(kw["atoms"]) == 0:
			raise MidasError('No atoms specified')
	else:
		for surf in surfs:
			if not hasattr(surf, 'atoms'):
				raise MidasError('Surface has no associated atoms. Please use the "atoms" argument')
	
	# ensure values are in ascending order
	pairs = zip(values, colors)
	pairs.sort()
	values, colors = zip(*pairs)
	coloredSome = False
	for surf in surfs:	
		colorEsp(surf, colors, values, **kw)
		coloredSome = True
	if not coloredSome:
		raise MidasError("No molecular surfaces selected with atom spec '%s'"
						% args)
	if showKey:
		keyData = []
		for val, rgba in zip(values, colors):
			keyData.append((rgba, str(val)))
		from Ilabel.gui import IlabelDialog
		from chimera import dialogs
		d = dialogs.display(IlabelDialog.name)
		d.keyConfigure(keyData)
