# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: __init__.py 42135 2020-04-28 18:11:41Z goddard $

""" Emulate UCSF Midas command set """

import sys
import math
import tempfile
import os

import chimera
if not chimera.nogui:
	import chimera.tkgui
from chimera import selection, dialogs
from chimera import elements
from chimera import replyobj
from chimera import misc
from chimera.colorTable import getColorByName
from StructMeasure import DistMonitor

ADD_POSITIONS = "add positions"
REMOVE_POSITIONS = "remove positions"
chimera.triggers.addTrigger(ADD_POSITIONS)
chimera.triggers.addTrigger(REMOVE_POSITIONS)

class MidasError(Exception):
	pass

def _showStatus(s, **kw):
	if "log" not in kw:
		kw['log'] = True
	replyobj.status('%s' % s, **kw)

def evalSpec(spec):
	try:
		from chimera import specifier
		return specifier.evalSpec(spec)
	except:
		raise MidasError, "mangled atom specifier"

#
# Internal functions that return items of interest
#
def _selectedModels(sel, modType=chimera.Molecule):
	if isinstance(sel, basestring):
		sel = evalSpec(sel)
	elif isinstance(sel, (list, tuple, set)):
		return sel
	graphs = sel.graphs()
	if modType:
		return filter(lambda g, t=modType: isinstance(g, t), graphs)
	return graphs

def _selectedResidues(sel):
	if isinstance(sel, basestring):
		sel = evalSpec(sel)
	elif isinstance(sel, (list, tuple)):
		if sel:
			if isinstance(sel[0], chimera.Molecule):
				nsel = []
				for m in sel:
					nsel.extend(m.residues)
				sel = nsel
			elif isinstance(sel[0], chimera.Atom):
				residues = set()
				for a in sel:
					residues.add(a.residue)
				sel = list(residues)
		return sel
	elif isinstance(sel, set):
		return sel
	return sel.residues()

def _selectedAtoms(sel, ordered=False, asDict=False):
	if isinstance(sel, basestring):
		sel = evalSpec(sel)
	elif isinstance(sel, (list, tuple)):
		if sel and isinstance(sel[0],
					(chimera.Molecule, chimera.Residue)):
			nsel = []
			for m in sel:
				nsel.extend(m.atoms)
			sel = nsel
		if asDict:
			return dict.fromkeys(sel)
		return sel
	elif isinstance(sel, set):
		return sel
	if isinstance(sel, selection.ItemizedSelection):
		return sel.atoms(ordered=ordered, asDict=asDict)
	return sel.atoms(asDict=asDict)

def _selectedBonds(sel, internal=True):
	bonds = misc.bonds(_selectedAtoms(sel), internal=internal)
	if isinstance(sel, basestring):
		sel = evalSpec(sel)
	if isinstance(sel, selection.ItemizedSelection):
		for b in sel.bonds():
			bonds.add(b)
	return bonds

def _selectedPseudobonds(sel):
	seenOnce = set()
	seenTwice = set()
	for a in _selectedAtoms(sel):
		pbs = set(a.pseudoBonds)
		seenTwice |= (seenOnce & pbs)
		seenOnce |= pbs
	return seenTwice

def _selectedPseudobondGroups(sel):
	groups = set()
	for pb in _selectedPseudobonds(sel):
		groups.add(pb.pseudoBondGroup)
	return groups

def _selectedSurfacePieces(sel):
	if isinstance(sel, (list, tuple, set)):
		nsel = []
		from _surface import SurfacePiece, SurfaceModel
		for s in sel:
			if isinstance(s, SurfacePiece):
				nsel.append(s)
			elif isinstance(s, SurfaceModel):
				nsel.extend(s.surfacePieces)
		return nsel
	if isinstance(sel, basestring):
		sel = evalSpec(sel)
	if isinstance(sel, selection.Selection):
		import Surface
		return Surface.selected_surface_pieces(sel)
	return []

#
# Internal functions that operate on given selection
#
def _editAtom(sel, funcs):
	atoms = _selectedAtoms(sel)
	if isinstance(funcs, (list, tuple)):
		for a in atoms:
			for f in funcs:
				f(a)
	else:
		for a in atoms:
			funcs(a)
	return atoms

def _editBond(sel, funcs):
	bonds = _selectedBonds(sel)
	if isinstance(funcs, (list, tuple)):
		for b in bonds:
			for f in funcs:
				f(b)
	else:
		for b in bonds:
			funcs(b)
	return bonds

def _editAtomBond(sel, aFunc, bFunc, internal=False):
	atoms = _selectedAtoms(sel)
	if aFunc:
		for a in atoms:
			aFunc(a)
	if bFunc:
		for b in misc.bonds(atoms, internal=internal):
			bFunc(b)

def _editResidue(sel, func):
	residues = _selectedResidues(sel)
	for res in residues:
		func(res)

def _editMolecule(sel, func):
	graphs = _selectedModels(sel)
	for g in graphs:
		func(g)

def _editModel(sel, func):
	graphs = _selectedModels(sel, modType=object)
	for g in graphs:
		func(g)

#
# Internal functions that support motion commands
#
_motionHandlers = []
def _addMotionHandler(func, param):
	if not isinstance(param['frames'], int):
		raise MidasError("'frames' must be an integer")
	h = chimera.triggers.addHandler('new frame', func, param)
	param['handler'] = h
	_motionHandlers.append(param)

def _removeMotionHandler(param):
	try:
		_motionHandlers.remove(param)
		chimera.triggers.deleteHandler('new frame', param['handler'])
		param['handler'] = None  # break cycle
	except KeyError:
		pass

def _clearMotionHandlers():
	global _motionHandlers
	for param in _motionHandlers:
		chimera.triggers.deleteHandler('new frame', param['handler'])
		param['handler'] = None  # break cycle
	_motionHandlers = []

def _motionRemaining():
	frames = 0
	for param in _motionHandlers:
		f = param['frames']
		if f > 0 and f > frames:
			frames = f
	import Fly
	frames = max(frames, Fly.frames_left())
	return frames

def _tickMotionHandler(param):
	if param['frames'] > 0:
		param['frames'] = param['frames'] - 1
		if param['frames'] == 0:
			if param.has_key('removalHandler'):
				param['removalHandler'](param)
			else:
				_removeMotionHandler(param)
	elif not chimera.openModels.list():
		if param.has_key('removalHandler'):
			param['removalHandler'](param)
		else:
			_removeMotionHandler(param)

def _movement(trigger, param, triggerData):
	if trigger:
		_tickMotionHandler(param)
	if not _moveModels(param['xform'],
			   param.get('coordinateSystem', None),
			   param.get('models', None),
			   param.get('center', None),
			   param.get('precessionAxis', None),
			   param.get('precessionStep', None)):
		if param.has_key('removalHandler'):
			param['removalHandler'](param)
		else:
			_removeMotionHandler(param)

def _flight(trigger, param, triggerData):
	if trigger:
		_tickMotionHandler(param)
	counter = param['counter']
	xfList = param['xformList']
	if not _moveModels(xfList[counter], param.get('coordinateSystem', None),
			   param.get('models', None), param.get('center', None)):
		if param.has_key('removalHandler'):
			param['removalHandler'](param)
		else:
			_removeMotionHandler(param)
		return
	counter = counter + param['direction']
	if counter < 0 or counter >= len(xfList):
		mode = param['mode']
		if mode == 'cycle':
			counter = 0
		elif mode == 'bounce':
			if counter < 0:
				counter = 1
				param['direction'] = 1
			else:
				counter = len(xfList) - 2
				param['direction'] = -1
		else:
			if param.has_key('removalHandler'):
				param['removalHandler'](param)
			else:
				_removeMotionHandler(param)
	param['counter'] = counter

def _moveModels(xf, coordsys_open_state, models, center,
		precessionAxis = None, precessionStep = None):
	if not precessionAxis is None:
		from chimera import Xform
		xfp = Xform.identity()
		xfp.premultiply(xf)
		pa = xf.apply(precessionAxis)
		xfp.premultiply(Xform.rotation(precessionAxis, precessionStep))
		precessionAxis.x = pa.x
		precessionAxis.y = pa.y
		precessionAxis.z = pa.z
		xf = xfp
	if coordsys_open_state:
		if coordsys_open_state.__destroyed__:
			return False
		cxf = coordsys_open_state.xform
		from chimera import Xform
		rxf = Xform.translation(-cxf.getTranslation())
		rxf.multiply(cxf)
		axf = Xform()
		for x in (rxf, xf, rxf.inverse()):
			axf.multiply(x)
		# Reorthogonalize for stability when coordinate frame rotating
		axf.makeOrthogonal(True)
		xf = axf
		if center:
			center = cxf.apply(center)
	from chimera import openModels as om
	if models is None and center is None:
		om.applyXform(xf)
	else:
		if models is None:
			models = [m for m in om.list() if m.openState.active]
		for os in set([m.openState for m in models
			       if not m.__destroyed__]):
			_moveOpenState(os, xf, center)
	return True

def _moveOpenState(os, xf, center):
	# Adjust transform to act about center of rotation.
	from chimera import openModels as om, Xform
	if center:
		c = center
	elif om.cofrMethod == om.Independent:
		c = os.xform.apply(os.cofr)
	else:
		c = om.cofr
	cxf = Xform.translation(c.x, c.y, c.z)
	cxf.multiply(xf)
	cxf.multiply(Xform.translation(-c.x, -c.y, -c.z))
	os.globalXform(cxf)

def _clip(trigger, param, triggerData):
	if trigger:
		_tickMotionHandler(param)
	delta = param['delta']
	v = chimera.viewer
	camera = v.camera
	near, far = camera.nearFar
        absolute = param.get('from_center', False)
        if absolute:
                cofr_z = chimera.openModels.cofr[2]
                fn = param['frames']
                f = 1 if fn is None else 1.0 / (fn + 1)
        plane = param['plane'][0]
	if  plane == 'h':
                near = f*(cofr_z+delta)+(1-f)*near if absolute else near + delta
                if near <= far:
                        far = near - 0.01
	elif plane == 'y':
                far = f*(cofr_z+delta)+(1-f)*far if absolute else far + delta
	        if near <= far:
                        near = far + 0.01
	elif plane == 't':
                near += delta
                far -= delta
                if near <= far:
                        nf = 0.5 * (near + far)
                        near, far = nf + 0.005, nf - 0.005
	elif plane == 's':
                near += delta
                far += delta
                if near <= far:
                        far = near - 0.01
	v.clipping = True
	camera.nearFar = (near, far)

def _rotation(trigger, param, triggerData):
	if trigger:
		_tickMotionHandler(param)
	rot = param['rot']
	if rot.bondRot.__destroyed__:
		return
	rot.increment(param['adjust'])

def _scale(trigger, param, triggerData):
	if trigger:
		_tickMotionHandler(param)
	viewer = chimera.viewer
	try:
		viewer.scaleFactor = viewer.scaleFactor * param['scaleFactor']
	except ValueError:
		raise chimera.LimitationError("refocus to continue scaling")

def _wait(trigger, param, triggerData):
	_tickMotionHandler(param)

def _degrees(a):
	return a / math.pi * 180

def _axis(a):
	if isinstance(a, basestring):
		if a == 'x':
			return chimera.Vector(1, 0, 0)
		elif a == 'y':
			return chimera.Vector(0, 1, 0)
		elif a == 'z':
			return chimera.Vector(0, 0, 1)
	elif isinstance(a, (list, tuple)):
		if len(a) == 3:
			return chimera.Vector(a[0], a[1], a[2])
	return a

#
# Miscellaneous internal functions
#

def _centerOf(aList):
	pts = [a.xformCoord() for a in aList]
	valid, sph = chimera.find_bounding_sphere(pts)
	return sph.center

def _crossProduct(a, b):
	x = a[1] * b[2] - a[2] * b[1]
	y = a[2] * b[0] - a[0] * b[2]
	z = a[0] * b[1] - a[1] * b[0]
	return [x, y, z]

def _dotProduct(a, b):
	return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

def _normalize(a):
	l = _dotProduct(a, a)
	if l > 0:
		l = math.sqrt(l)
		a[0] = a[0] / l
		a[1] = a[1] / l
		a[2] = a[2] / l

_labelInfo = "name"
_rlabelInfo = '%(type)s %(id)s'

_colorEditorSynonyms = ['colorpanel', 'fromeditor', 'editor']
def convertColor(color, noneOkay=True):
	if isinstance(color, basestring):
		if color in _colorEditorSynonyms:
			from CGLtk.color import ColorWell
			if not ColorWell._colorPanel:
				from chimera import UserError
				dialogs.display("color editor")
				raise UserError('Choose color in panel first')
			c = chimera.MaterialColor()
			rgba = ColorWell.colorPanel().rgba
			c.ambientDiffuse = rgba[:-1]
			c.opacity = rgba[-1]
		elif color.lower() == "none":
			if not noneOkay:
				raise MidasError('none not allowed')
			c = None
		elif color.lower() in ['byatom', 'byelement', 'byhet', 'byhetero']:
			raise MidasError('Group color (%s) not allowed' % color)
		else:
			try:
				# Chimera color name.
				c = getColorByName(color)
			except KeyError:
				try:
					# Tk color name.
					if chimera.nogui:
						# won't get X11 names, oh well...
						if not color.startswith('#') or len(color) == 1 or (len(color)-1) % 3 != 0:
							raise ValueError("Not Tk rgb color")
						colorDigits = (len(color)-1) / 3
						divisor = (16 ** colorDigits) - 1.0
						rgb = []
						index = 1
						lowerColor = color.lower()
						for component in range(3):
							val = 0
							for place in range(colorDigits):
								digit = lowerColor[index]
								ascii = ord(digit)
								if digit.isdigit():
									val = 16*val + ascii - ord('0')
								elif ord('a') <= ascii <= ord('f'):
									val = 16*val + ascii - ord('a') + 10
								else:
									raise ValueError("Non-hex digit in Tk color")
								index += 1
							rgb.append(val/divisor)
					else:
						from chimera.tkgui import app
						rgb16 = app.winfo_rgb(color)
						rgb = [c / 65535.0 for c in rgb16]
					c = chimera.MaterialColor(*rgb)
				except:
					try:
						# Comma separated list of rgb or rgba float values.
						rgba = [float(c) for c in color.split(',')]
						c = chimera.MaterialColor(*rgba)
					except:
						from chimera import UserError
						raise UserError('Color "%s" is undefined'
								% color)
	elif color is None or isinstance(color, chimera.Color):
		if color is None and not noneOkay:
			raise MidasError('none not allowed')
		c = color
	elif isinstance(color, (list, tuple)):
		try:
			c = chimera.MaterialColor(*tuple(color))
		except:
			from chimera import UserError
			raise UserError('Color "%s" is undefined' % str(color))
	else:
		raise RuntimeError, 'need a color'
	return c

ColorSuffixes = (',a', ',b', ',r', ',f', ',s', ',v', ',l', ',la', ',al', ',lr', ',rl')

def _colorSplit(color):
	ci = min([color.find(r) for r in ColorSuffixes if r in color] + [len(color)])
	cname = color[:ci]
	if color[ci + 1:]:
		citems = color[ci + 1:].split(",")
	else:
		citems = []
	atomItems, bondItems, resItems = _colorItems(citems)
	return cname, atomItems, bondItems, resItems

def _colorItems(parts):
	if not parts:
		return (["color", "labelColor", "vdwColor", "surfaceColor"],
			["labelColor"],
			["labelColor", "ribbonColor", "fillColor"])

	atomItems = []
	bondItems = []
	resItems = []
	for itemChar in parts:
		if itemChar == "s":
			atomItems.append("surfaceColor")
		elif itemChar == "l":
			atomItems.append("labelColor")
			resItems.append("labelColor")
		elif itemChar in "a":
			atomItems.append("color")
		elif itemChar == "b":
			bondItems.append("color")
		elif itemChar == "v":
			atomItems.append("vdwColor")
		elif itemChar == "r":
			resItems.append("ribbonColor")
		elif itemChar == "f":
			resItems.append("fillColor")
		elif itemChar in ["al", "la"]:
			atomItems.append("labelColor")
		elif itemChar in ["bl", "lb"]:
			bondItems.append("labelColor")
		elif itemChar in ["rl", "lr"]:
			resItems.append("labelColor")
		elif itemChar == "c":
			raise MidasError(
				'Color wheel interpolations not supported')
		else:
			raise MidasError('Unknown color specifier "%s"'
						' encountered' % itemChar)
	return atomItems, bondItems, resItems

def convertGradient(gradient, interpolation):
	"""convert gradient spec to 1D texture"""
	from chimera import palettes
	if isinstance(gradient, palettes.Palette):
		if (interpolation is not None
		and gradient.interpolation != interpolation):
			gradient = palettes.Palette(None, gradient.rgbas,
								interpolation)
		return gradient
	if isinstance(gradient, basestring):
		if gradient == 'none':
			return None
		if gradient == 'current':
			palette = chimera.viewer.backgroundGradient[0]
			if palette is None:
				raise ValueError("no current gradient")
		else:
			palette = palettes.getPaletteByName(gradient)
			if palette is None:
				raise ValueError("unknown palette name: %s" % gradient)
		if (interpolation is not None
		and palette.interpolation != interpolation):
			palette = palettes.Palette(None, palette.rgbas,
								interpolation)
		return palette

	colors = [convertColor(c, noneOkay=False) for c in gradient]
	rgbas = [c.rgba() for c in colors]
	if len(rgbas) <= 1:
		raise ValueError('need at least two colors')
	if interpolation is None:
		interpolation = palettes.HLS
	p = palettes.Palette(None, rgbas, interpolation)
	return p

def convertImage(image):
	"""convert argument to a PIL Image"""
	from PIL import Image
	if isinstance(image, Image.Image):
		# already an image
		pass
	elif isinstance(image, basestring):
		if image == 'none':
			return None
		if image == 'current':
			return chimera.viewer.backgroundImage[0]
		try:
			image = Image.open(image)
		except (IOError, ValueError), e:
			raise ValueError(
				"Unable to open image file: '%s'" % image)
	else:
		raise ValueError("expected an image or filename of an image")
	return image


def _savePosition(default = False):
	from chimera import openModels as om, viewer, Xform
	xforms = {}
	for molId in om.listIds():
		xforms[molId] = Xform() if default else om.openState(*molId).xform
	from chimera.misc import KludgeWeakWrappyDict
	clips = KludgeWeakWrappyDict("Model")
	for m in om.list():
		clips[m] = (m.useClipPlane, m.clipPlane, m.useClipThickness,
							m.clipThickness)
	if om.cofrMethod == om.Independent:
		cofr = (0, 0, 0)
	else:
		cofr = tuple(om.cofr)
	cam = viewer.camera
	return (
		viewer.scaleFactor,
		viewer.viewSize,
		cam.center,
		cam.nearFar,
		cam.focal,
		xforms,
		clips,
		om.cofrMethod,
		cofr,
		viewer.clipping,
		cam.fieldOfView,
	)

def _restorePosition(trigger, param, triggerData):
	if trigger:
		_tickMotionHandler(param)
	pos = param['position']
	cofrMethod = None
	cofr = None
	clips = {}
	clipping = True
	fov = chimera.viewer.camera.fieldOfView
	if len(pos) == 11:
		scale, view, center, nearFar, focal, xforms, clips, \
					cofrMethod, cofr, clipping, fov = pos
	elif len(pos) == 10:
		scale, view, center, nearFar, focal, xforms, clips, \
					cofrMethod, cofr, clipping = pos
	elif len(pos) == 9:
		scale, view, center, nearFar, focal, xforms, clips, \
					cofrMethod, cofr = pos
	elif len(pos) == 7:
		scale, view, center, nearFar, focal, xforms, clips = pos
	else:
		scale, view, center, nearFar, focal, xforms = pos

	_addMissingModelXforms(xforms)

	mode = param['mode']
	if param['frames'] == 0:
		rate = 1
	elif mode == 'geometric':
		# TODO: revise so we don't over/under shoot 1
		duration = param['duration']
		rate = .5 / pow(duration, 1. / duration)
	elif mode == 'halfstep':
		rate = .5
	else:
		# mode == 'linear' (default)
		rate = 1.0 / (param['frames'] + 1)

	hold = param.get('holdSteady')
	if hold is None:
		_updateCamera(cofrMethod, cofr, scale, view, center,
			      nearFar, focal, fov, clipping, rate)
	move = param.get('moveModels')
	_updatePerModelClipPlanes(clips, move, rate)
	_moveModelsPartWay(xforms, hold, move, rate)

def _addMissingModelXforms(xforms):
	from chimera import openModels as om
	# have currently open models not in the position keep their
	# orientation relative to the lowest open model...
	missing = []
	fromXF = toXF = lowID = None
	for molID in om.listIds():
		if molID in xforms:
			if lowID == None or molID < lowID:
				lowID = molID
				fromXF = om.openState(*molID).xform
				toXF = xforms[molID]
		else:
			missing.append(molID)
	if missing and fromXF:
		for molID in missing:
			xf = om.openState(*molID).xform
			xf.premultiply(fromXF.inverse())
			xf.premultiply(toXF)
			xforms[molID] = xf

def _updateCamera(cofrMethod, cofr, scale, view, center,
		  nearFar, focal, fov, clipping, rate):
	from chimera import openModels as om
	v = chimera.viewer
	cam = v.camera
	if rate == 1:
		if cofrMethod != None:
			om.cofrMethod = cofrMethod
			if om.cofrMethod == chimera.OpenModels.Independent:
				om.cofr = chimera.Point(*cofr)
		v.setViewSizeAndScaleFactor(view, scale)
		v.clipping = clipping
		cam.fieldOfView = fov
		cam.center = center
		cam.nearFar = nearFar
		cam.focal = focal
		return
	if cofrMethod == om.cofrMethod \
	and om.cofrMethod != chimera.OpenModels.Independent:
		cofrPoint = chimera.Point(*cofr)
		curCofr = om.cofr
		newCofr = curCofr + (cofrPoint - curCofr) * rate
		om.cofr = chimera.Point(*newCofr)
	v.scaleFactor += (scale - v.scaleFactor) * rate
	v.viewSize += (view - v.viewSize) * rate
	curfov = cam.fieldOfView
	cam.fieldOfView = curfov + (fov - curfov) * rate
	curCenter = chimera.Point(*cam.center)
	center = chimera.Point(*center)
	newCenter = curCenter + (center - curCenter) * rate
	cam.center = tuple(newCenter)
	if v.clipping or clipping:
		v.clipping = True
		near, far = cam.nearFar
		cam.nearFar = near + (nearFar[0] - near) * rate, \
					far + (nearFar[1] - far) * rate
	cam.focal += (focal - cam.focal) * rate

def _updatePerModelClipPlanes(clips, move, rate):
	for m, clipInfo in clips.items():
		if not move is None and not m in move:
			continue
		useClip, plane, useThickness, thickness = clipInfo
		if useClip and m.useClipPlane and rate != 1:
			# avoid modifying copy of clip plane...
			curPlane = m.clipPlane
			curPlane.origin += (plane.origin - curPlane.origin) * rate
			curPlane.normal += (plane.normal - curPlane.normal) * rate
			m.clipPlane = curPlane
			if m.useClipThickness == useThickness:
				m.clipThickness += (thickness
						- m.clipThickness) * rate
			else:
				m.useClipThickness = useThickness
				m.clipThickness = thickness
		else:
			m.useClipPlane = useClip
			m.clipPlane = plane
			m.useClipThickness = useThickness
			m.clipThickness = thickness

def _moveModelsPartWay(xforms, hold, move, rate):
	osxf = {}
	from chimera import openModels as om, Xform
	for molId, xf in xforms.items():
		try:
			osxf[om.openState(*molId)] = xf
		except ValueError:
			# model's gone, oh well...
			continue

	if hold and hold in osxf:
		rxf = osxf[hold].inverse()
		rxf.premultiply(hold.xform)
		for os,xf in osxf.items():
			xfc = Xform()		# Copy xform
			xfc.premultiply(osxf[os])
			xfc.premultiply(rxf)
			osxf[os] = xfc

	if not move is None:
		mos = set(m.openState for m in move)
		osxf = dict((os,xf) for os,xf in osxf.items() if os in mos)

	interpolateOpenStates(osxf, rate)

def interpolateOpenStates(osxf, rate):
	# Used (at least) by Animate
	if rate == 1:
		for os,xf in osxf.items():
			os.xform = xf
		return

	for openState, xform, c in _motionCenters(osxf):
		# Determine translation
		xf = openState.xform
		r = xf.inverse()
		r.premultiply(xform)
		curCofr = c
		finalCofr = r.apply(c)
		wantCofr = curCofr + (finalCofr - curCofr) * rate
		td = chimera.Xform.translation(wantCofr - curCofr)

		# Determine rotation
		axis, angle = r.getRotation()
		rd = chimera.Xform.rotation(axis, angle * rate)

		cv = chimera.Xform.translation(curCofr - chimera.Point())
		cvi = chimera.Xform.translation(chimera.Point() - curCofr)

		nextXf = chimera.Xform.identity()
		nextXf.multiply(xf)	# Apply start transform
		nextXf.premultiply(cvi)	# Shift to put cofr at origin
		nextXf.premultiply(rd)	# Apply fractional rotation
		nextXf.premultiply(cv)	# Shift cofr back
		nextXf.premultiply(td)	# Apply fractional translation

		openState.xform = nextXf

#
# Group openStates that require the same xform to get to their destination.
# Compute center of bounding sphere for each group.
#
def _motionCenters(osxf):
	xox = {}
	xflist = []
	oxc = []
	for os, xform in osxf.items():
		xf = os.xform.inverse()
		xf.premultiply(xform)
		cxf = _closeXform(xf, xflist)
		if cxf is None:
			xflist.append(xf)
			xox[id(xf)] = [(os, xform)]
		else:
			xox[id(cxf)].append((os, xform))
	for osxlist in xox.values():
		gs = None
		for os, xform in osxlist:
			have, s = os.bsphere()
			if have:
				s.xform(os.xform)
				if gs is None:
					gs = s
				else:
					gs.merge(s)
		if not gs is None:
			c = gs.center
			oxc.extend([(os, xform, c) for os, xform in osxlist])
	return oxc

def _closeXform(xf, xflist):
	for x in xflist:
		if _closeXforms(x, xf):
			return x

	return None

def _closeXforms(xf1, xf2, angleTol=1.0, shiftTol=1.0):
	xf = chimera.Xform()
	xf.premultiply(xf1)
	xf.premultiply(xf2.inverse())
	axis, angle = xf.getRotation()
	close = (xf.getTranslation().length <= shiftTol and
		 angle <= angleTol)
	return close

#
# Actual exported functions (in alphabetical order)
#

def addaa(args):
	"""add an amino acid to the last residue in a chain"""
	import addAA
	from addAA import addAA, AddAAError

	arg_list = args.split(" ", 1)

	if not len(arg_list) == 2:
		raise MidasError, "Invalid number of arguments."

	rest_of_args = arg_list[0]

	## atom spec of residue to which new residue will be appended
	res_spec = arg_list[1]
	residues = _selectedResidues(res_spec)
	if len(residues) != 1:
		raise MidasError, "Exactly one residue must be selected. " \
		      "'%s' specifies %d residues." % (res_spec, len(residues))

	else:
		(last_residue,) = residues

	some_args = rest_of_args.split(",")
	if len(some_args) < 2:
		raise MidasError, "Not enough arguments. " \
		      "Require at least 'residue type' and 'residue sequence'"

	else:
		if not some_args[0].isalpha():
			raise MidasError, "Missing residue type argument"
		else:
			res_type = str(some_args[0])

		res_seq = some_args[1]
		if not res_seq or res_seq.isalpha():
			raise MidasError, "Missing residue sequence argument"

		if len(some_args) == 2:
			conf = None
		elif len(some_args) == 3:
			conf = some_args[2]
		elif len(some_args) == 4:
			phi, psi = some_args[2:4]
			if (phi.isalpha() or psi.isalpha()):
				raise MidasError, "Require either both phi and psi arguments or neither"
			conf = (phi, psi)
		elif len(some_args) > 4:
			raise MidasError, "Too many arguments"

	try:
		addAA(res_type, res_seq, last_residue, conformation=conf)
	except AddAAError, what:
		raise MidasError, "%s" % what
	else:
		_showStatus("Successfully added new amino acid \"%s\"" % res_type)


def align(sel=None, sel2=None, objID=None):
	if objID:
		from StructMeasure.Geometry import geomManager
		items = geomManager.items
		try:
			obj = [item for item in items if item.id == objID][0]
		except IndexError:
			raise MidasError("No such object: %s" % objID)
		from StructMeasure.Axes import Axis
		from StructMeasure.Planes import Plane
		if isinstance(obj, Axis):
			frontPt = obj.center + obj.direction
			backPt = obj.center - obj.direction
		elif isinstance(obj, Plane):
			frontPt = obj.plane.origin + obj.plane.normal
			backPt = obj.plane.origin
		else:
			raise MidasError("'align' for %s objects is not supported"
				% obj.__class__.__name__.lower())
		centering = [frontPt, backPt]
		centeringFunc = lambda pt, os = obj.model.openState: os.xform.apply(pt)
		frontPt = obj.model.openState.xform.apply(frontPt)
		backPt = obj.model.openState.xform.apply(backPt)
	else:
		centeringFunc = lambda a: a.xformCoord()
		if sel2 == None:
			try:
				atoms = _selectedAtoms(sel, ordered=True)
			except MidasError:
				# sel might be two specs instead of one...
				if sel.count(' ') == 1:
					sel1, sel2 = sel.split(' ')
				else:
					atoms = []
			else:
				if len(atoms) == 2:
					frontPt = atoms[0].xformCoord()
					backPt = atoms[1].xformCoord()
					centering = atoms[:1]
				elif sel.count(' ') == 1:
					sel1, sel2 = sel.split(' ')
			if sel2 == None and len(atoms) != 2:
				raise MidasError('Exactly two atoms must be selected'
					' by atom spec or two atom specs provided.')
		else:
			sel1 = sel
		if sel2 != None:
			atoms1 = _selectedAtoms(sel1)
			atoms2 = _selectedAtoms(sel2)
			if not atoms1:
				raise MidasError("Left atom spec (%s) selects no atoms"
									% sel1)
			if not atoms2:
				raise MidasError("Right atom spec (%s) selects no atoms"
									% sel2)
			frontPt = chimera.Point([a.xformCoord() for a in atoms1])
			backPt = chimera.Point([a.xformCoord() for a in atoms2])
			centering = atoms1
	xf = chimera.Xform.zAlign(backPt, frontPt)
	for molId in chimera.openModels.listIds():
		openState = chimera.openModels.openState(*molId)
		if openState.active:
			openState.globalXform(xf)
	cp = chimera.Point([centeringFunc(c) for c in centering])
	chimera.viewer.camera.center = (cp.x, cp.y, cp.z)

def angle(sel='sel', objIDs=None, dihedral=True):
	"""Report angle between three or four atoms, or two objects"""
	if objIDs:
		from StructMeasure.Geometry import geomManager
		items = geomManager.items
		objs = []
		for objID in objIDs:
			try:
				objs.append([item for item in items if item.id == objID][0])
			except IndexError:
				raise MidasError("No such object: %s" % objID)

		val = geomManager.angle(objs)
		name1, name2 = [obj.id for obj in objs]
		_showStatus("Angle between %s and %s is %.3f" % (name1, name2, val))
		return val
	atoms = _selectedAtoms(sel, ordered=True)
	osl = ' '.join(map(lambda a: a.oslIdent(), atoms))
	points = tuple(a.xformCoord() for a in atoms)
	if len(points) == 3:
		from chimera import angle
		val = angle(*points)
		_showStatus("Angle %s: %g" % (osl, val))
		return val
	if len(points) == 4:
		if dihedral:
			val = chimera.dihedral(*points)
			_showStatus("Dihedral %s: %g" % (osl, val))
		else:
			p3 = points[0] + (points[3]-points[2])
			val = chimera.angle(points[1], points[0], p3)
			_showStatus("Angle %s: %g" % (osl, val))
		return val
	raise MidasError('Three or four atoms must be selected.  You '
			'selected %d.' % len(atoms))

def aromatic(style=None, sel='sel'):
	molecules = _selectedModels(sel)
	if style is None:
		for m in molecules:
			m.aromaticDisplay = True
		return
	if style == 'off':
		return unaromatic(sel)
	if style == 'circle':
		mode = chimera.Molecule.Circle
	elif style == 'disk':
		mode = chimera.Molecule.Disk
	elif style not in (chimera.Molecule.Circle, chimera.Molecule.Disk):
		raise MidasError('unknown aromatic representation ("%s")' % style)
	for m in molecules:
		m.aromaticDisplay = True
		m.aromaticMode = mode

def unaromatic(sel='sel'):
	molecules = _selectedModels(sel)
	for m in molecules:
		m.aromaticDisplay = False

def _attrSelFunc(level):
	if level[0] == 'a':
		return _selectedAtoms
	elif level[0] == 'r':
		return _selectedResidues
	elif level[0] == 's':
		from chimera import MSMSModel
		return lambda sel, mt = MSMSModel: _selectedModels(sel, modType=mt)
	elif level[0] == 'm':
		return _selectedModels
	elif level[0] == 'M':
		return lambda sel: _selectedModels(sel, modType=None)
	elif level[0] == 'b':
		return _selectedBonds
	elif level[0] == 'p':
		return _selectedPseudobonds
	elif level[0] == 'g':
		return _selectedPseudobondGroups
	raise MidasError("Attribute level must be [a]tom, [r]esidue,"
			" [m]olecule, [b]ond, [s]urface, [p]seudobond,"
			" or [g]roup")

def background(color=(), gradient=None, interpolation=None, image=None, scale=1, tiling= -1, angle=0, offset=0, opacity=1, setMethod=True):
	method = None
	if color is not ():
		if color != "current":
			# None is legal
			try:
				color = convertColor(color)
			except RuntimeError, e:
				raise MidasError(e)
			chimera.viewer.background = color
		if not isinstance(chimera.viewer, chimera.LensViewer):
			return
		method = chimera.viewer.Solid
	elif gradient is not None:
		if not isinstance(chimera.viewer, chimera.LensViewer):
			raise MidasError("not supported by current viewer")
		try:
			palette = convertGradient(gradient, interpolation)
		except ValueError, e:
			raise MidasError(e)
		chimera.viewer.backgroundGradient = palette, opacity, angle, offset
		if palette is not None:
			method = chimera.viewer.Gradient
		else:
			method = chimera.viewer.Solid
	elif image is not None:
		if not isinstance(chimera.viewer, chimera.LensViewer):
			raise MidasError("not supported by current viewer")
		try:
			image = convertImage(image)
		except ValueError, e:
			raise MidasError(e)
		if tiling == -1:
			tiling = chimera.viewer.Zoomed
		chimera.viewer.backgroundImage = image, scale, tiling, opacity, angle, offset
		if image is not None:
			method = chimera.viewer.Image
		else:
			method = chimera.viewer.Solid
	if setMethod and method is not None:
		chimera.viewer.backgroundMethod = method

def bond(sel='sel'):
	bonded = _selectedAtoms(sel)
	if len(bonded) != 2:
		raise MidasError("Choose only 2 atoms to bond (%d chosen)"
								% len(bonded))
	from chimera.molEdit import addBond
	return addBond(*bonded)

def bondcolor(color, sel='sel'):
	try:
		c = convertColor(color)
	except RuntimeError, e:
		raise MidasError(e)
	atoms = _selectedAtoms(sel)
	for b in misc.bonds(atoms, internal=True):
		b.color = c
		b.halfbond = False
bondcolour = bondcolor

def bonddisplay(mode, sel='sel'):
	atoms = _selectedAtoms(sel)
	for b in misc.bonds(atoms, internal=True):
		b.display = mode

def bondrepr(style, sel='sel'):
	if style == "stick":
		bondMode = chimera.Bond.Stick
	elif style == "wire":
		bondMode = chimera.Bond.Wire
	else:
		raise MidasError('Unknown representation style "%s"' % style)
	atoms = _selectedAtoms(sel)
	for b in misc.bonds(atoms, internal=True):
		b.drawMode = bondMode

def _centerCamera(trigger, param, triggerData):
	if trigger:
		_tickMotionHandler(param)
	cam = chimera.viewer.camera
	c = chimera.Point(*cam.center)
	f = 1.0 / (param['frames'] + 1)
	cam.center = chimera.lerp(c, param['center'], f).data()

def center(sel='sel', frames=None):
	c = None
	aList = _selectedAtoms(sel)
	if aList:
		c = _centerOf(aList)
	else:
		sList = _selectedSurfacePieces(sel)
		if sList:
			import Surface
			s = Surface.surface_sphere(sList)
			if s:
				c = s.center
	if c is None:
		raise MidasError('No atoms or surfaces selected')
	if frames is None:
		chimera.viewer.camera.center = c.data()
	else:
		_addMotionHandler(_centerCamera, {'center':c, 'frames':frames})
	return c
centre = center

def chimeraSelect(sel='sel'):
	if sel in ['up', 'down']:
		from chimera.selection.upDown import selUp, selDown
		if sel == 'up':
			selUp()
		else:
			selDown()
		return
	if sel.startswith("invert"):
		from chimera.selection import invertCurrent
		if sel.endswith("sel"):
			invertCurrent(allModels=False)
		else:
			invertCurrent(allModels=True)
		return
	if not isinstance(sel, selection.Selection):
		sel = evalSpec(sel)
	if not hasattr(sel, 'addImplied'):
		newSel = selection.ItemizedSelection()
		newSel.merge(selection.REPLACE, sel)
		sel = newSel
	sel.addImplied(vertices=0)
	from chimera import selectionOperation
	selectionOperation(sel)

def chirality(sel='sel'):
	import chiral
	class ChiralError(ValueError, MidasError):
		pass
	chiralities = []
	for a in _selectedAtoms(sel):
		try:
			start = chimera.idatm.typeInfo[a.idatmType]
		except KeyError:
			raise ChiralError(
				"Unknown hybridization state for atom %s"
								% a.oslIdent())
		if start.geometry != 4:
			raise ChiralError("%s is not tetrahedral"
								% a.oslIdent())
		if start.substituents != 4:
			raise ChiralError("%s bonds to less than 4 atoms"
								% a.oslIdent())
		chirality = chiral.init(a)
		chirMsg = chirality
		if chirality is None:
			chirMsg = "no"
		else:
			chirMsg = chirality
		_showStatus('%s has %s chirality' % (a.oslIdent(), chirMsg))
		chiralities.append(chirality)
	if not chiralities:
		raise ChiralError("No atoms specified")
	return chiralities

def enableClipping(enable):
	chimera.viewer.clipping = enable

def clip(plane, delta, frames=None, from_center = False):
	param = {'command':'clip', 'plane':plane,
                 'delta':delta, 'frames':frames,
                 'from_center':from_center}
	if frames is None:
		_clip(None, param, None)
	else:
		_addMotionHandler(_clip, param)

def close(model):
	if model == "all":
		models = chimera.openModels.list()
	elif model == "session":
		chimera.closeSession()
		return
	else:
		models = list(model)
	chimera.openModels.close(models)

def cofr(where='report'):
	from chimera import openModels as om
	methods = { 'view': om.CenterOfView,
		    'front': om.FrontCenter,
		    'models': om.CenterOfModels,
		    'independent': om.Independent,
		    'fixed':om.Fixed}
	if where in methods:
		om.cofrMethod = methods[where]
	elif isinstance(where, chimera.Point):
		om.cofr = where
		om.cofrMethod = om.Fixed
	elif where != 'report':
		box = boundingBox(where)
		if box is None:
			raise MidasError('No atoms or surfaces selected')
		om.cofr = box.center()
		om.cofrMethod = om.Fixed
	if om.cofrMethod != om.Independent:
		_showStatus('Center of rotation: ' + str(om.cofr))

def color(colorSpec, sel='sel'):
	"""Change atom color"""
	color, atomItems, bondItems, resItems = _colorSplit(colorSpec)

	colorFunc = None
	if color in ['byatom', 'byelement']:
		# always atom-level only
		bondItems = resItems = []
		def _colorByAtom(a, items):
			c = elementColor(a.element)
			for item in items:
				setattr(a, item, c)
		colorFunc = _colorByAtom
	elif color in ['byhet', 'byhetero']:
		# always atom-level only
		bondItems = resItems = []
		def _colorByHet(a, items):
			if a.element.number == elements.C.number:
				return
			c = elementColor(a.element)
			for item in items:
				setattr(a, item, c)
		colorFunc = _colorByHet
	else:
		try:
			c = convertColor(color)
		except RuntimeError, e:
			raise MidasError(e)

	singleColor = (colorFunc is None)
	if singleColor:
		def _color(thing, items, color=c):
			for item in items:
				setattr(thing, item, color)
		colorFunc = _color

	if atomItems:
		# change surfaces from custom coloring if appropriate...
		if 'surfaceColor' in atomItems:
			from chimera import MSMSModel
			mols = {}
			for m in _selectedModels(sel):
				mols[m] = None
			for surf in chimera.openModels.list(
							modelTypes=[MSMSModel]):
				if surf.colorMode != MSMSModel.Custom:
					continue
				if surf.molecule in mols:
					surf.colorMode = MSMSModel.ByAtom

		_editAtom(sel, lambda a, items=atomItems: colorFunc(a, items))

	if bondItems:
		if 'color' in bondItems:
			def bcFunc(b, items=bondItems):
				b.halfbond = False
				colorFunc(b, items)
		else:
			def bcFunc(b, items=bondItems):
				colorFunc(b, items)

		_editBond(sel, bcFunc)

	colorAll = (colorSpec.find(',') == -1)
	if colorAll:
		_editBond(sel, lambda b: setattr(b, 'halfbond', True))

	if resItems:
		_editResidue(sel, lambda a, items=resItems: colorFunc(a, items))

	if 'surfaceColor' in atomItems and singleColor and not c is None:
		from chimera import MSMSModel
		plist = [p for p in _selectedSurfacePieces(sel)
			 if (not isinstance(p.model, MSMSModel)
			     or p.model.molecule is None)]
		import Surface
		for m in set(p.model for p in plist):
			Surface.set_coloring_method('set color', m)
		rgba = c.rgba()
		for p in plist:
			p.color = rgba
			p.vertexColors = None
colour = color

def colordef(color, target):
	"""Define RGB(A) color"""
	if isinstance(color, basestring):
		if color in _colorEditorSynonyms:
			raise MidasError("Cannot define a color named '%s'"
								% color)
		if color == "list":
			from chimera import colorTable, elements, _savedColors
			elementNames = set(elements.name)
                        colorNames = [c.name() for c in _savedColors]
			userDefined = [cn for cn in colorNames
				if cn not in elementNames and cn not in colorTable.colors]
			if not userDefined:
				_showStatus("No user-defined colors", color="red", log=False)
			else:
				userDefined.sort()
				replyobj.info("List of user-defined color names:\n\t%s\n" %
					"\n\t".join(userDefined))
				_showStatus("Color definitions listed in reply log", log=False)
			return
		c = chimera.Color.lookup(color)
		if c is None:
			if target is None:
				raise MidasError("Unknown color named '%s'"
								% color)
			c = chimera.MaterialColor()
			c.save(color)
		if target is None:
			_showStatus('color %s is %g %g %g %g' % ((color,) + c.rgba()))
			return
	else:
		c = color
		if target is None:
			raise MidasError("print it out yourself!")

	if isinstance(target, tuple):
		# argument is RGB or RGBA tuple
		c.ambientDiffuse = target[:3]
		if len(target) > 3:
			c.opacity = target[-1]
		else:
			c.opacity = 1.0
	else:
		# argument is other color
		try:
			nc = convertColor(target, noneOkay=False)
		except:
			raise MidasError('Color "%s" is undefined' % target)
		c.ambientDiffuse = tuple(nc.ambientDiffuse)
		c.opacity = nc.opacity
colourdef = colordef

def copy(printer=None, file=None, format=None, supersample=None,
			raytrace=False, rtwait=None, rtclean=None,
			width=None, height=None, dpi=None, units='pixels'):
	import chimera.printer as cp
	if raytrace:
		format = 'PNG'
	if not format:
		if file:
			format = deduceFileFormat(file, cp.FilenameFilters)
			if not format:
				format = deduceFileFormat(file,
						cp.StereoFilenameFilters)
		if not format:
			format = 'PS'
	printMode = None
	if format in (f[0] for f in cp.StereoFilenameFilters):
		printMode = 'stereo pair'
	if not printer and not file:
		if chimera.nogui:
			raise MidasError('need filename in nogui mode')
		file = '-'
	if printer and not file:
		saveFile = tempfile.mktemp()
		format = 'TIFF'
	elif file and file != '-':
		from OpenSave import tildeExpand
		saveFile = tildeExpand(file)
	else:
		saveFile = None
	if rtclean is None:
		keepInput = None
	else:
		keepInput = not rtclean
	if width is not None and height is None:
		w, h = chimera.viewer.windowSize
		scale = float(width) / w
		height = h * scale
		if units == 'pixels':
			height = int(height + .5)
	elif width is None and height is not None:
		w, h = chimera.viewer.windowSize
		scale = float(height) / h
		width = w * scale
		if units == 'pixels':
			width = int(width + .5)
	image = cp.saveImage(saveFile, format=format, supersample=supersample,
				raytrace=raytrace, raytraceWait=rtwait,
				raytraceKeepInput=keepInput,
				width=width, height=height, dpi=dpi,
				units=units, printMode=printMode)

	if printer is None:
		return

	if raytrace:
		from PIL import Image
		image = Image.open(saveFile)

	if not saveFile or format not in ('TIFF', 'TIFF-fast'):
		printSource = tempfile.mktemp()
		image.save(printSource, 'TIFF')
	else:
		printSource = saveFile


	if printer != "-":
		printArg = "-P" + printer
	else:
		printArg = ""

	itops = os.path.join(os.environ["CHIMERA"], "bin", "itops")
	os.system('"' + itops + '" -a -r %s | lpr %s' % (printSource, printArg))
	if file and format not in ('TIFF', 'TIFF-fast'):
		os.unlink(printSource)

def define(geom, sel='sel', **kw):
	name = kw.pop("name", geom)
	raiseTool = kw.pop("raiseTool", True)
	if raiseTool and not chimera.nogui:
		from StructMeasure.gui import StructMeasure
		dialogs.display(StructMeasure.name)
		from StructMeasure.Geometry import geomManager
		geomManager.showInterface()
	if geom == "axis":
		plural = "Axes"
		if kw.pop("perHelix", False):
			if 'helicalCorrection' not in kw:
				kw['helicalCorrection'] = True
			if kw['helicalCorrection'] and kw.get("massWeighting", False):
				raise MidasError("Helical correction combined with mass"
					" weighting is not supported")
			from StructMeasure.Axes import createHelices
			axes = []
			for m in _selectedModels(sel):
				axes.extend(createHelices(m, **kw))
			return axes
		else:
			if 'helicalCorrection' not in kw:
				kw['helicalCorrection'] = False
			elif kw['helicalCorrection'] and kw.get("massWeighting", False):
				raise MidasError("Helical correction combined with mass"
					" weighting is not supported")
		kw['centroids'] = centroids = []
		kw['plane'] = None
		atomSpecItems = []
		for si in sel.split():
			if si[0].lower() == 'c' and si[1:].isdigit():
				from StructMeasure.Centroids import centroidManager
				for centroid in centroidManager.centroids:
					if centroid.id == si:
						centroids.append(centroid)
						break
				else:
					raise MidasError("No centroid with ID '%s'" % si)
			elif si[0].lower() == 'p' and si[1:].isdigit():
				from StructMeasure.Planes import planeManager
				for plane in planeManager.planes:
					if plane.id == si:
						if kw['plane'] == None:
							kw['plane'] = plane
						else:
							raise MidasError("For making a plane-normal axis,"
								" specify only a single plane ID")
						break
				else:
					raise MidasError("No plane with ID '%s'" % si)
			else:
				atomSpecItems.append(si)
		if atomSpecItems:
			spec = " ".join(atomSpecItems)
			sel = evalSpec(spec)
			if isinstance(sel, selection.ItemizedSelection):
				atoms = sel.atoms()
				from StructMeasure.Centroids import centroidManager
				for centroid in centroidManager.centroids:
					for model in sel.models():
						if centroid.model == model:
							centroids.append(centroid)
			else:
				atoms = _selectedAtoms(" ".join(atomSpecItems))
		else:
			atoms = []
		if kw['plane'] != None:
			if atoms or centroids:
				raise MidasError("Cannot specify atoms/centroids in addition"
					" to a plane ID")
		elif len(atoms) + len(centroids) < 2:
			raise MidasError("Must specifiy at least two atoms/centroids to"
				" define an axis")
	else:
		plural = geom.capitalize() + "s"
		atoms = _selectedAtoms(sel)
		if not atoms:
			raise MidasError("No atoms in atom spec")
	exec("from StructMeasure.%s import %sManager as mgr" % (plural, geom))
	return eval("mgr.create%s(name, atoms, **kw)" % geom.capitalize())

def undefine(geomIDs, axes=False, planes=False, centroids=False):
	if axes:
		from StructMeasure.Axes import axisManager
		geomIDs.extend([a.id for a in axisManager.axes])
	if planes:
		from StructMeasure.Planes import planeManager
		geomIDs.extend([p.id for p in planeManager.planes])
	if centroids:
		from StructMeasure.Centroids import centroidManager
		geomIDs.extend([c.id for c in centroidManager.centroids])
	lookup = set(geomIDs)
	from StructMeasure.Geometry import geomManager
	geomManager.removeItems([i for i in geomManager.items if i.id in lookup])

def delete(sel='sel'):
	"""Delete atoms"""
	deleteAtomsBonds(_selectedAtoms(sel))

def display(sel='sel'):
	"""Display atoms

	Atoms specification may come from either a selection or
	an osl string.  If no atom specification is supplied,
	the current selection is displayed."""
	def _atomDisplay(atom):
		atom.display = 1
	_editAtomBond(sel, _atomDisplay, None)

def distance(sel='sel', objIDs=[], **kw):
	"""Monitor distance between exactly two items"""
	from StructMeasure.Geometry import geomManager
	if len(objIDs) < 2:
		atoms = _selectedAtoms(sel)
		import _surface
		selModels = _selectedModels(sel, modType=_surface.SurfaceModel)
		objs = [item for item in geomManager.items if item.model in selModels]
	else:
		atoms = []
		objs = []
	numSelected = len(atoms) + len(objIDs) + len(objs)
	if numSelected != 2:
		raise MidasError('Exactly two atoms/axes/planes must be selected.'
			'  You selected %d.' % numSelected)
	if len(atoms) == 2:
		try:
			DistMonitor.addDistance(atoms[0], atoms[1])
		except ValueError, s:
			raise MidasError('Error adding distance: %s.' % s)
		return atoms[0].xformCoord().distance(atoms[1].xformCoord())

	items = geomManager.items
	for objID in objIDs:
		try:
			objs.append([item for item in items if item.id == objID][0])
		except IndexError:
			raise MidasError("No such object: %s" % objID)

	signedErrMsg = "'signed' keyword only supported for" \
					" atom/centroid-to-plane distances"
	if len(atoms) == 1:
		try:
			dist = objs[0].pointDistances([atom.xformCoord()
				for atom in atoms], **kw)[0]
		except TypeError:
			if 'signed' in kw:
				raise MidasError(signedErrMsg)
			raise
		name1 = str(atoms[0])
		name2 = objs[0].id
	else:
		try:
			dist = geomManager.distance(objs, **kw)
		except TypeError:
			if 'signed' in kw:
				raise MidasError(signedErrMsg)
			raise
		name1, name2 = [obj.id for obj in objs]
	_showStatus("Distance from %s to %s is %.3f" % (name1, name2, dist))
	return dist

def export(filename=None, format=None, list=False):
	DEFAULT_FORMAT = 'X3D'
	from chimera import exports
	exportInfo = exports.getFilterInfo()
	if list:
		_showStatus("Export formats: " + ", ".join([x[0] for x in exportInfo]))
		return

	if format:
		for name, glob, suffix in exportInfo:
			if name.lower() == format.lower():
				format = name
				break
		else:
			raise MidasError('Unknown export format: %s' % format)

	if not filename:
		if chimera.nogui:
			raise MidasError(
			"Cannot use argless 'export' command in nogui mode")
		from chimera import exportDialog
		d = dialogs.display(exportDialog.name)
		if d and format:
			d.setFilter(format)
		return

	from OpenSave import compressSuffixes
	compress = False
	for cs in compressSuffixes:
		if filename.endswith(cs):
			compress = True
			break
	if compress:
		replyobj.warning("file not saved: compressed files are not supported yet\n")
		return

	if not format:
		format = deduceFileFormat(filename, exportInfo)
		if not format:
			format = DEFAULT_FORMAT

	from OpenSave import tildeExpand
	filename = tildeExpand(filename)

	exports.doExportCommand(format, filename)

def focus(sel='sel'):
	"""Window/cofr about displayed part of selection"""
	if sel == '#':
		dsel = sel
	else:
		disped = [a for a in _selectedAtoms(sel) if a.shown()]
		for p in _selectedSurfacePieces(sel):
			if p.display and p.model.display and p.triangleCount > 0:
				if isinstance(p.model, chimera.MSMSModel):
					disped.extend([a for a in p.model.atoms
							if a.surfaceDisplay])
				else:
					disped.append(p)
		if not disped:
			raise MidasError("No displayed atoms/ribbons/surfaces specified")

		from chimera.selection import ItemizedSelection
		dsel = ItemizedSelection()
		dsel.add(disped)
	window(dsel)
	from chimera import openModels as om
	if om.cofrMethod != om.Independent:
		if sel == '#':
			from chimera import viewing
			om.cofrMethod = viewing.defaultCofrMethod
		else:
			om.cofrMethod = om.CenterOfView
			cofr('report')

def unfocus(sel='sel'):
	"""Window/cofr about all displayed models"""
	focus('#')

def freeze():
	"""Stop all motion"""
	_clearMotionHandlers()
	if not chimera.nogui:
		chimera.tkgui.stopSpinning()

def getcrd(sel='sel', xformed=False):
	"""Print the coordinates of selected atoms"""
	if xformed:
		def _getcrd(a):
			_showStatus('Atom %s   %s' % (a.oslIdent(),
					'%.3f %.3f %.3f' % a.xformCoord().data()))
	else:
		def _getcrd(a):
			_showStatus('Atom %s   %s' % (a.oslIdent(),
					'%.3f %.3f %.3f' % a.coord().data()))
	_editAtom(sel, _getcrd)

def ksdssp(sel='sel', energy=None, helixLen=None, strandLen=None, verbose=False):
	kw = {}
	reportEnergy = reportHelix = reportStrand = "<default>"
	if energy is not None:
		kw['energyCutoff'] = energy
		reportEnergy = "%g" % energy
	if helixLen is not None:
		kw['minHelixLength'] = helixLen
		reportHelix = "%g" % helixLen
	if strandLen is not None:
		kw['minStrandLength'] = strandLen
		reportStrand = "%g" % strandLen
	if verbose:
		import StringIO
		kw['info'] = StringIO.StringIO()

	mols = _selectedModels(sel)
	if mols:
		replyobj.info(
"""Computing secondary structure assignments for model(s) %s
using ksdssp (Kabsch and Sander Define Secondary Structure
of Proteins) with the parameters:
  energy cutoff %s
  minimum helix length %s
  minimum strand length %s
""" % (", ".join([m.oslIdent() for m in mols]), reportEnergy, reportHelix, reportStrand))
		for mol in mols:
			mol.computeSecondaryStructure(**kw)
			if verbose:
				replyobj.info("\nKsdssp summary for %s:\n%s"
					% (mol, kw['info'].getvalue()))
				kw['info'].close()
				kw['info'] = StringIO.StringIO()
			mol.updateRibbonData()
		if verbose:
			kw['info'].close()
			replyobj.status("ksdssp summary reported in reply log")

class AtomAttrDict:
	retrieveDict = {
		"name": lambda a: a.oslIdent(chimera.SelAtom)[1:],
		"idatm": lambda a: a.idatmType,
		# element works already
	}
	def __init__(self, atom):
		self.atom = atom

	def __getitem__(self, item):
		return getattr(self.atom, item)

def label(sel='sel', offset=None, warnLarge=False):
	"""Add label to selected atoms"""
	if offset == 'default':
		offset = chimera.Vector(chimera.Molecule.DefaultOffset, 0, 0)
	def _label(a, offset=offset):
		if offset is not None:
			a.labelOffset = offset
		if _labelInfo in AtomAttrDict.retrieveDict:
			a.label = str(AtomAttrDict.retrieveDict[_labelInfo](a))
		else:
			try:
				val = getattr(a, _labelInfo)
				if val is None:
					a.label = ""
				else:
					a.label = str(val)
			except AttributeError:
				import midas_text
				try:
					a.label = _labelInfo % AtomAttrDict(a)
				except TypeError:
					midas_text.error("Bad label format;"
						" use 'help labelopt' for formatting info")
				except AttributeError:
					midas_text.error("No such attribute")
				else:
					if a.label == _labelInfo and _labelInfo.isalnum():
						a.label = ""
						midas_text.error("No such attribute")
	if warnLarge and not chimera.nogui:
		numAffected = len([a for a in _selectedAtoms(sel) if a.display])
		if numAffected > 100:
			# is it also more than one label per residue?
			# (use 1.5 per residue to allow for alt atom locs)
			if numAffected > 1.5 * len(_selectedResidues(sel)):
				from chimera.tkgui import LabelWarningDialog
				LabelWarningDialog(numAffected,
							lambda : label(sel))
				return
	_editAtom(sel, _label)

def labelopt(opt, value):
	"""change label display options"""
	if opt == "info":
		global _labelInfo
		_labelInfo = value
	elif opt == "resinfo":
		global _rlabelInfo
		_rlabelInfo = value

def linewidth(width, sel='sel'):
	models = _selectedModels(sel)
	for model in models:
		model.lineWidth = width

def longbond(ratio=2.5, length=None, sel='sel'):
	from chimera import LONGBOND_PBG_NAME
	from chimera.misc import getPseudoBondGroup
	pbg = getPseudoBondGroup(LONGBOND_PBG_NAME)
	if pbg.display:
		raise MidasError("Missing segments already shown."
				" Use ~longbond to hide them.")
	pbg.display = True

class TooFewAtomsError(MidasError):
	pass

def match(f, t, selected=False, iterate=None, minPoints=1, showMatrix=False,
														move='molecules'):
	"""Superposition the two specified sets of atoms ("from" and "to")

	   if 'selected' is True, transform all active models, not just
	   the 'from' model.

	   if 'iterate' is not None, the matching will iterate
	   (pruning poorly-matching atom pairs at each pass) until no pair
	   distance exceeds the value assigned to 'iterate'

	   'minPoints' is the minimum number of points from each model to
	   match.  If fewer are specified (or, due to 'iterate', you go
	   below the number), then TooFewAtomsError is raised.

	   if 'showMatrix' is True, report the transformation matrix to
	   the Reply Log.

	   if 'move' is 'molecules', superimpose the models.  If it is 'atoms',
	   'residues' or 'chains' move just those atoms.  If move is False
	   move nothing or True move molecules.  If move is a tuple, list or
	   set of atoms then move those.
	"""
	mobileAtoms, refAtoms = _atomSpecErrorCheck(f, t)

	xform, rmsd, fullRmsd, matchedRefAtoms, matchedMobileAtoms = \
		matchXform(refAtoms, mobileAtoms, iterate, minPoints)

	if showMatrix:
		import Matrix as M
		matf = M.xform_matrix(xform)
		mmol = mobileAtoms[0].molecule
		mxf = mmol.openState.xform
		mtf = M.xform_matrix(mxf)
		rmol = refAtoms[0].molecule
		rxf = rmol.openState.xform
		rtf = M.xform_matrix(rxf)
		rtfinv = M.xform_matrix(rxf.inverse())
		rrtf = M.multiply_matrices(rtfinv, matf, rtf)
		tl = M.transformation_description(rrtf)
		msg = ('Motion of %s in %s coordinate system\n%s'
		       % (mmol.oslIdent(), rmol.oslIdent(), tl))
		if mxf != rxf:
			mrtf = M.multiply_matrices(rtfinv, matf, mtf)
			tf = M.transformation_description(mrtf)
			msg += ('Motion of %s original coordinates in %s coordinate system\n%s'
				% (mmol.oslIdent(), rmol.oslIdent(), tf))
		replyobj.info(msg)
	if iterate is None:
		_showStatus('RMSD between %d atom pairs is %.3f angstroms'
							% (len(matchedRefAtoms), rmsd))
	else:
		_showStatus('RMSD between %d pruned atom pairs is %.3f angstroms;'
			' (across all %d pairs: %.3f)' % (len(matchedRefAtoms), rmsd, len(refAtoms), fullRmsd))

	moveMatch(mobileAtoms, refAtoms, xform, move, selected)

	return matchedMobileAtoms, matchedRefAtoms, rmsd, fullRmsd

def matchXform(refAtoms, mobileAtoms, iterate=None, minPoints=1):

	mArray = chimera.numpyArrayFromAtoms(mobileAtoms, xformed=True)
	fArray = chimera.numpyArrayFromAtoms(refAtoms, xformed=True)
	import numpy
	subset = numpy.arange(len(refAtoms))
	from Matrix import apply_matrix, xform_matrix
	from chimera.match import matchPositions
	while 1:
		if len(subset) < minPoints:
			raise TooFewAtomsError("Too few corresponding atoms"
				" (%d) to match models\n" % len(refAtoms))

		fxyz, mxyz = fArray[subset], mArray[subset]
		xform, rmsd = matchPositions(fxyz, mxyz)
		if iterate is None:
			break
		elif iterate <= 0.0:
			raise MidasError("Iteration cutoff must be positive")

		dxyz = apply_matrix(xform_matrix(xform), mxyz) - fxyz
		d2 = (dxyz * dxyz).sum(axis=1)
		i = d2.argsort()
		if d2[i[-1]] <= iterate * iterate:
			break

		# cull 10% or...
		index1 = int(len(d2) * 0.9)
		# cull half the long pairings
		index2 = int(((d2 <= iterate * iterate).sum() + len(d2)) / 2)
		# whichever is fewer
		index = max(index1, index2)

		subset = subset[i[:index]]

	if len(subset) < 3:
		replyobj.warning("This superposition uses less than 3 pairs of"
			" atoms is therefore not unique.\n")

	if iterate is None:
		fullRmsd = rmsd
	else:
		dxyz = apply_matrix(xform_matrix(xform), mArray) - fArray
		d2 = (dxyz * dxyz).sum(axis=1)
		fullRmsd = math.sqrt(d2.sum() / len(d2))

	matchedRefAtoms = numpy.take(refAtoms, subset)
	matchedMobileAtoms = numpy.take(mobileAtoms, subset)

	return xform, rmsd, fullRmsd, matchedRefAtoms, matchedMobileAtoms

def moveMatch(mobileAtoms, refAtoms, xform, move, allActive):

	if move == 'molecules' or move is True:
		mOSs = set(a.molecule.openState for a in mobileAtoms)
		for mOS in mOSs:
			mOS.globalXform(xform)
	else:
		if move == 'atoms':
			atoms = mobileAtoms
		elif move == 'residues':
			residues = set(a.residue for a in mobileAtoms)
			atoms = sum((r.atoms for r in residues), [])
		elif move == 'chains':
			cids = set((a.molecule, a.residue.id.chainId)
				   for a in mobileAtoms)
			molecules = set(a.molecule for a in mobileAtoms)
			matoms = sum((m.atoms for m in molecules), [])
			atoms = [a for a in matoms
				 if (a.molecule, a.residue.id.chainId) in cids]
		elif isinstance(move, (tuple, list, set)):
			atoms = move
		else:
			return	# Move nothing
		for a in atoms:
			xyz = xform.apply(a.xformCoord())
			axyz = a.molecule.openState.xform.inverse().apply(xyz)
			a.setCoord(axyz)

	if allActive:
		# transform all active models
		fos = set(a.molecule.openState for a in mobileAtoms)
		fos.update(a.molecule.openState for a in refAtoms)
		aos = set(m.openState for m in chimera.openModels.list())
		for os in aos:
			if os.active and os not in fos:
				os.globalXform(xform)

#
# Copies the f model transform to the t models.
#
# If the moving argument is provided (a list of models) then those
# models are carried along by the transform that takes f to t and the
# t model(s) are not changed (unless they are in the moving list).
#
def matrixcopy(f, t, moving=None):

	if isinstance(f, chimera.Model):
		srcs = [f.openState]
	elif isinstance(f, (list, tuple)) and len(f) > 0 and isinstance(f[0], chimera.Model):
		srcs = [m.openState for m in f]
	else:
		srcs = [m.openState for m in _getModelsFromId(f)]
	if len(srcs) == 0:
		raise MidasError('No source models selected.')

	if isinstance(t, chimera.Model):
		dests = [t.openState]
	elif isinstance(t, (list, tuple)) and len(t) > 0 and isinstance(t[0], chimera.Model):
		dests = [m.openState for m in t]
	else:
		dests = [x.openState for x in _getModelsFromId(t)]
	if len(dests) == 0:
		raise MidasError('No destination model(s) selected.')

	# Remove duplicate openStates.
	srcs = unique_items(srcs)
	dests = unique_items(dests)

	if moving is None:
		if len(srcs) == 1:
			for dest in dests:
				dest.xform = srcs[0].xform
		elif len(dests) == len(srcs):
			for s,d in zip(srcs, dests):
				d.xform = s.xform
		else:
			raise MidasError('Different numbers of source and target models.')
	elif len(srcs) > 1 or len(dests) > 1:
		raise MidasError('Moving option used with multiple source or target models.')
	else:
		xform = srcs[0].xform
		xform.multiply(dests[0].xform.inverse())
		for os in set([m.openState for m in moving]):
			os.globalXform(xform)

def unique_items(list):
	found = set()
	u = []
	for e in list:
		if not e in found:
			found.add(e)
			u.append(e)
	return u

def matrixget(fileName):
	if fileName == "-":
		f = sys.stdout
	else:
		f = file(fileName, 'w')
	for mid in chimera.openModels.listIds():
		print >> f, "Model %d.%d" % mid
		os = chimera.openModels.openState(*mid)
		xform = os.xform
		lines = str(xform).strip().split("\n")
		print >> f, "\t" + "\n\t".join(lines)
	if fileName != "-":
		f.close()

def matrixset(fileName):
	try:
		f = file(fileName, "r")
	except IOError, v:
		raise MidasError(v)
	lines = f.readlines()
	f.close()
	if len(lines) % 4 != 0:
		raise MidasError("Matrixset file not composed of 4-line groups"
			" (model numbers each with a 3x4 matrix)")
	for i in range(0, len(lines), 4):
		fields = lines[i].strip().split()
		raiseError = False
		if len(fields) != 2 or fields[0] != "Model" \
		or '.' not in fields[1]:
			raiseError = True
		else:
			mid = fields[1].split('.')
			if len(mid) != 2 or not mid[0].isdigit() \
			or not mid[1].isdigit():
				raiseError = True
			else:
				mid = map(int, mid)
		if raiseError:
			raise MidasError("Matrixset 'Model' line %d not of the"
					" form: Model number.number" % (i + 1))
		nums = []
		for j in range(i + 1, i + 4):
			fields = lines[j].strip().split()
			if len(fields) != 4:
				raiseError = True
			else:
				try:
					nums.extend(map(float, fields))
				except ValueError:
					raiseError = True
			if raiseError:
				raise MidasError("Matrixset 3x4 matrix line %d"
						" is not 4 numbers" % (j + 1))
		args = nums + [True]
		xform = chimera.Xform.xform(*args)
		try:
			openState = chimera.openModels.openState(*mid)
		except ValueError:
			replyobj.warning("Ignoring matrix for non-existent"
					" model %d.%d\n" % tuple(mid))
			continue
		openState.xform = xform

def modelcolor(color, sel='sel'):
	"""Change model color"""

	try:
		color = convertColor(color)
	except RuntimeError, e:
		raise MidasError(e)
	def _color(thing):
		thing.color = color
	_editMolecule(sel, _color)
modelcolour = modelcolor

def modeldisplay(sel='sel'):
	def _modeldisplay(thing):
		thing.display = 1
	_editModel(sel, _modeldisplay)

def move(x=0, y=0, z=0, frames=None, coordinateSystem=None, models=None):
	v = chimera.Vector(x, y, z)
	param = {'command':'move',
		 'xform':chimera.Xform.translation(v),
		 'frames':frames,
		 'coordinateSystem':coordinateSystem,
		 'models':models}
	if frames is None:
		_movement(None, param, None)
	else:
		_addMotionHandler(_movement, param)

def namesel(selName=None):
	from chimera.selection import saveSel, savedSels
	if not selName:
		selNames = savedSels.keys()
		if not selNames:
			_showStatus("No saved selections")
		else:
			_showStatus("Saved selections: %s" %
							', '.join(selNames))
		return
	saveSel(selName)

def objdisplay(sel='sel'):
	def _objdisplay(thing):
		if not isinstance(thing, chimera.Molecule)\
		and not isinstance(thing, chimera.MSMSModel):
			thing.display = 1
	_editModel(sel, _objdisplay)

def open(filename, filetype=None, model=chimera.OpenModels.Default,
		noprefs=False):
	if filetype in ['model', 'pdb', 'PDB']:
		filetype = 'PDB'
	elif filetype in ['mol2', 'Mol2']:
		filetype = 'Mol2'
	elif filetype in ['obj', 'OBJ', 'vrml', 'VRML']:
		filetype = 'VRML'
	try:
		mList = chimera.openModels.open(filename,
						type=filetype,
						defaultType="PDB",
						baseId=model,
						prefixableType=1,
						noprefs=noprefs)
	except IOError, s:
		try:
			code, msg = s
		except:
			msg = s
		raise MidasError('%s' % msg)
	else:
		if len(mList) == 1:
			from ModelPanel.base import readableName
			_showStatus('%s opened' % readableName(mList[0]))
		elif len(mList) > 1:
			_showStatus('%d models opened' % len(mList))
	return mList

def pause(end=False):
	if chimera.nogui:
		return
	from chimera import CancelOperation
	if end:
		raise CancelOperation("cancel script")
	import Pmw
	cancel = [False]
	def waitForKey(event, cancel=cancel):
		chimera.tkgui.deleteKeyboardFunc(waitForKey)
		Pmw.popgrab(chimera.tkgui.app.graphics)
		chimera.tkgui.app.graphics.quit()
		replyobj.status("")
		if event.keysym in ["End", "Escape"]:
			cancel[0] = True
	chimera.tkgui.addKeyboardFunc(waitForKey)
	replyobj.status("Script paused; Hit Escape or End to abort, any"
		" other key to continue", color="blue", blankAfter=0)
	Pmw.pushgrab(chimera.tkgui.app.graphics, False, lambda: None)
	chimera.tkgui.app.graphics.mainloop()
	if cancel[0]:
		raise CancelOperation("cancel script")

def pdbrun(cmd, all=0, conect=0, nouser=0, noobj=0, nowait=0, surface=0,
							mark=None, viewer=None):
	# any marks specified should be a sequence

	if viewer == None:
		viewer = chimera.viewer

	# wrappy isn't smart enough to provide the arguments that the
	# full-fledged pdbrun requires, so ignore marks for now
	if sys.platform == 'win32':
		# need to double up backslashes
		cmd = cmd.replace('\\', '\\\\')
	chimera.pdbrunNoMarks(all, conect, nouser, surface, nowait, viewer, cmd)

_perFrameHandlers = []
def perFrame(command, frames, interval=1, valueRanges=[], zeroPadWidth=None,
	     showCommands=False):
	tdata = { 'command': command,
		  'frames': frames,
		  'interval': interval,
		  'skip': 0,
		  'valueRanges': valueRanges,
		  'zeroPadWidth': zeroPadWidth,
		  'showCommands': showCommands,
		  'frameNum': 1,
		  }
	h = chimera.triggers.addHandler('new frame', _perFrameCallback, tdata)
	tdata['handler'] = h
	global _perFrameHandlers
	_perFrameHandlers.append(h)

def _perFrameCallback(trigName, myData, trigData):
	if myData['interval'] > 1:
		if myData['skip'] > 0:
			myData['skip'] -= 1
			return
		else:
			myData['skip'] = myData['interval'] - 1
	command = myData['command']
	frames = myData['frames']
	valueRanges = myData['valueRanges']
	zeroPadWidth = myData['zeroPadWidth']
	showCommands = myData['showCommands']
	frameNum = myData['frameNum']
	handler = myData['handler']
	exe, stop = _perFrameCommand(command, frameNum, frames, valueRanges,
				     zeroPadWidth)
	if showCommands:
		from chimera import replyobj
		replyobj.info('perframe %d: %s\n' % (frameNum, exe))
	from midas_text import makeCommand
	try:
		makeCommand(exe, reportAliasExpansion=False)
	except:
		stopPerFrame(handler)
		from midas_text import scripting
		if scripting:
			from chimera.replyobj import reportException
			reportException(description="Error executing per-frame command '%s'" % exe)
		else:
			import sys
			from midas_text import error
			error("Error executing per-frame command '%s': %s"
					% (exe, sys.exc_info()[1]))
		return
	if stop or (not frames is None and frameNum >= frames):
		stopPerFrame(handler)
	else:
		myData['frameNum'] = frameNum + 1

def _perFrameCommand(command, frameNum, frames, valueRanges, zeroPadWidth):
	alias = command if command[0] == "^" else "^" + command
	from midas_text import aliases
	if alias in aliases:
		for i in range(max(len(valueRanges), 1)):
			v = "$%d" % (i+1,)
			if v in aliases[alias]:
				command += ' ' + v
	args, stop = _perFrameArgs(frameNum, frames, valueRanges, zeroPadWidth)
	for i, arg in enumerate(args):
		var = '$%d' % (i + 1)
		command = command.replace(var, arg)
	return command, stop

def _perFrameArgs(frameNum, frames, valueRanges, zeroPadWidth):
	args = []
	stop = False
	if valueRanges:
		fmt = '%%0%dg' % zeroPadWidth if zeroPadWidth else '%g'
		for vr in valueRanges:
			r0, r1 = vr[:2]
			explicit_rstep = (len(vr) == 3)
			if frames is None or explicit_rstep:
				rstep = (vr[2] if explicit_rstep
					 else (1 if r1 >= r0 else -1))
				v = r0 + rstep * (frameNum - 1)
				v = min(r1, v) if r1 >= r0 else max(r1, v)
				if frames is None and v == r1:
					stop = True
			else:
				f = (float(frameNum - 1) / (frames - 1) if frames > 1
				     else 1.0)
				v = r0 * (1 - f) + r1 * f
			args.append(fmt % v)
	else:
		fmt = '%%0%dd' % zeroPadWidth if zeroPadWidth else '%d'
		args.append(fmt % frameNum)
	return args, stop

def stopPerFrame(handler=None):
	global _perFrameHandlers
	if not _perFrameHandlers:
		raise MidasError("No per-frame command active")
	if handler is None:
		for h in _perFrameHandlers:
			chimera.triggers.deleteHandler('new frame', h)
		_perFrameHandlers = []
	else:
		chimera.triggers.deleteHandler('new frame', handler)
		_perFrameHandlers.remove(handler)

def rainbow(sel='sel', **kw):
	"""Color selected models in rainbow pattern"""
	import midas_rainbow
	models = []
	_editMolecule(sel, lambda m, ms=models: ms.append(m))
	if 'colors' in kw:
		kw['colors'] = [convertColor(c, noneOkay=False) for c in kw['colors']]
	midas_rainbow.rainbowModels(models, **kw)

def _prepRangeColor(attrName, wayPoints, noValue, sel):
	atoms = _selectedAtoms(sel)
	if not atoms:
		raise MidasError("No atoms specified")

	residues = _selectedResidues(sel)
	if '.' in attrName:
		level, attrName = attrName.split('.', 1)
		if level == "atom":
			isAtomAttr = True
		elif level[:3] == "res":
			isAtomAttr = False
		else:
			raise MidasError("attribute qualifier must be"
							" 'residue' or 'atom'")
	else:
		isAtomAttr = True
		for r in residues:
			if hasattr(r, attrName):
				isAtomAttr = False
				break
	if isAtomAttr:
		items = atoms
	else:
		items = residues

	needSurvey = False
	for value, color in wayPoints:
		if isinstance(value, basestring):
			needSurvey = True
			break

	if needSurvey:
		minVal = maxVal = None
		for i in items:
			try:
				val = getattr(i, attrName)
			except AttributeError:
				continue
			if val is None:
				continue
			if minVal is None or val < minVal:
				minVal = val
			if maxVal is None or val > maxVal:
				maxVal = val
		if minVal is None:
			raise MidasError("No items had attribute '%s'"
								% attrName)
		else:
			midVal = (minVal + maxVal) / 2.0
			_showStatus("%s min/mid/max: %g / %g / %g" %
				(attrName, minVal, midVal, maxVal))

	finalWayPoints = []
	for val, color in wayPoints:
		try:
			index = ["min", "mid", "max"].index(val)
		except ValueError:
			if isinstance(val, basestring):
				raise MidasError("non-numeric attribute value "
					"must be min, mid, max, or novalue")
		else:
			val = [minVal, midVal, maxVal][index]
		try:
			color = convertColor(color, noneOkay=False)
		except RuntimeError, e:
			raise MidasError(e)
		finalWayPoints.append((val, color.rgba()))
	finalWayPoints.sort()
	noValueColor = convertColor(noValue)
	if noValueColor is not None:
		noValueRgba = noValueColor.rgba()
	else:
		noValueRgba = None
	return isAtomAttr, items, residues, finalWayPoints, noValueRgba

def _doRangeColor(items, attrFunc, attrName, colorFunc, finalWayPoints,
							noValue, noValueRgba):
	colorCache = {}
	for i in items:
		prevWP = None
		try:
			val = attrFunc(i, attrName)
		except AttributeError:
			val = None
		if val is None:
			if noValue is None:
				continue
			else:
				rgba = noValueRgba
		else:
			for wpVal, rgba in finalWayPoints:
				if val < wpVal:
					break
				prevWP = (wpVal, rgba)
			else:
				wpVal = None
			if prevWP is None:
				rgba = finalWayPoints[0][1]
			elif wpVal is None:
				rgba = finalWayPoints[-1][1]
			else:
				lval, lrgba = prevWP
				pos = (val - lval) / float(wpVal - lval)
				rgba = tuple(map(lambda l, r:
					l * (1 - pos) + r * pos, lrgba, rgba))
		if rgba:
			try:
				color = colorCache[rgba]
			except KeyError:
				color = chimera.MaterialColor(*rgba)
				colorCache[rgba] = color
		else:
			color = rgba

		colorFunc(i, color)

def rangeColor(attrName, colorItems, wayPoints, noValue,
						sel='#', showKey=False):
	"""color atom parts by attribute

	   'attrName' is a residue or atom attribute name.  It can be 
	   prepended with 'atom.' or 'residue.' to resolve ambiguity if
	   necessary.  Otherwise, residue-level attributes win "ties".
	   
	   'colorItems' is a comma-separated string of items to color (labels,
	   surfaces, etc., as per the 'color' command) or an empty string
	   (color everything).  In addition to the color command characters,
	   the character 'r' means to color ribbons.

	   'wayPoints' is a sequence of value/color tuples describing the color
	   range layout.  The values can be 'max', 'min', 'mid' or numeric.

	   'noValue' is the color to apply to items missing the attribute.
	   A value of None means to leave them unchanged.

	   If 'showKey' is True, bring up the Color Key tool with the
	   appropriate values filled in.
	"""

	isAtomAttr, items, residues, finalWayPoints, noValueRgba = \
			_prepRangeColor(attrName, wayPoints, noValue, sel)
	if showKey:
		keyData = []
		for val, rgba in finalWayPoints:
			keyData.append((rgba, str(val)))
		from Ilabel.gui import IlabelDialog
		d = dialogs.display(IlabelDialog.name)
		print "key data:", keyData
		d.keyConfigure(keyData)

	cinames = [ci for ci in colorItems.split(',') if ci]
	atomItems, bondItems, resItems = _colorItems(cinames)
	if atomItems:
		# change surfaces from custom coloring if appropriate...
		if 'surfaceColor' in atomItems:
			from chimera import MSMSModel
			mols = {}
			for m in _selectedModels(sel):
				mols[m] = None
			for surf in chimera.openModels.list(
							modelTypes=[MSMSModel]):
				if surf.colorMode != MSMSModel.Custom:
					continue
				if surf.molecule in mols:
					surf.colorMode = MSMSModel.ByAtom
		def doColorItems(i, c, isAtomAttr=isAtomAttr,
						colorItems=atomItems):
			if isAtomAttr:
				for ci in colorItems:
					setattr(i, ci, c)
			else:
				for a in i.oslChildren():
					for ci in colorItems:
						setattr(a, ci, c)

		_doRangeColor(items, getattr, attrName, doColorItems,
					finalWayPoints, noValue, noValueRgba)
	if resItems:
		valCache = {}
		def getVal(residue, attrName):
			try:
				val = valCache[residue]
			except KeyError:
				tot = None
				atoms = residue.oslChildren()
				for a in atoms:
					try:
						val = getattr(a, attrName)
					except AttributeError:
						continue
					if val is None:
						continue
					if tot is None:
						tot = 0
					tot += val
				if tot is None:
					val = None
				else:
					val = tot / float(len(atoms))
				valCache[residue] = val
			return val

		if isAtomAttr:
			attrFunc = getVal
		else:
			attrFunc = getattr

		def colorItem(i, c, colorItems=resItems):
			for ci in colorItems:
				setattr(i, ci, c)

		_doRangeColor(residues, attrFunc, attrName, colorItem,
					finalWayPoints, noValue, noValueRgba)
rangeColour = rangeColor

def represent(style, sel='sel'):
	if style == "bs" or style == "b+s":
		# ball-and-stick
		atomMode = chimera.Atom.Ball
		bondMode = chimera.Bond.Stick
	elif style == "stick":
		atomMode = chimera.Atom.EndCap
		bondMode = chimera.Bond.Stick
	elif style == "wire":
		atomMode = chimera.Atom.Dot
		bondMode = chimera.Bond.Wire
	elif style == "cpk" or style == "sphere":
		atomMode = chimera.Atom.Sphere
		bondMode = chimera.Bond.Wire
	else:
		raise MidasError('Unknown representation style "%s"' % style)
	atoms = _selectedAtoms(sel)
	for a in atoms:
		a.drawMode = atomMode
	for b in misc.bonds(atoms, internal=True):
		b.drawMode = bondMode

def reset(name='default', frames=None, mode='linear', holdSteady=None, moveModels=None):
	if name == "list":
		pnames = list(positions.keys())
		pnames.sort()
		statStr = 'Saved positions: ' + ', '.join(pnames)
		_showStatus(statStr)
		return

	pos = positions.get(name)
	if pos is None:
		if name == 'default':
			if holdSteady is None and moveModels is None and frames is None:
				chimera.viewer.resetView()
				window('#')
				uncofr()
				return
			else:
				pos = _savePosition(default = True)
		else:
			raise MidasError("No saved position named '%s'" % name)
	
	if frames is not None and frames < 1:
		raise MidasError("frame count must be positive")
	if not moveModels is None:
		moveModels = set(moveModels)
	param = {'command':'reset',
		 'position':pos,
		 'mode':mode,
		 'holdSteady':holdSteady,	# OpenState
		 'moveModels':moveModels,	# Models
		 'frames':frames,
		 'duration':frames}
	if frames is None:
		param.update({'frames':0})
		_restorePosition(None, param, None)
	else:
		_addMotionHandler(_restorePosition, param)

def ribbackbone(sel='sel'):
	def _ribbackbone(thing):
		thing.ribbonHidesMainchain = 0
	_editMolecule(sel, _ribbackbone)

def ribbon(sel='sel'):
	"""Display residue as ribbon"""
	def _residuedisplay(thing):
		thing.ribbonDisplay = 1
	_editResidue(sel, _residuedisplay)
	anyRibbon = False
	for m in _selectedModels(sel):
		if m.updateRibbonData():
			anyRibbon = True
	if not anyRibbon:
		replyobj.warning("no residues with ribbons found\n")

def ribclass(name, sel='sel'):
	if name.lower() == "none":
		def _residueclass(thing):
			thing.ribbonResidueClass = None
		_editResidue(sel, _residueclass)
	else:
		from RibbonStyleEditor import atoms
		rrc = atoms.findRRC(name)
		if rrc is None:
			raise MidasError('Unknown ribbon class "%s"' % name)
		def _residueclass(thing, rrc=rrc):
			rrc.setResidue(thing)
		_editResidue(sel, _residueclass)

def ribinsidecolor(color, sel='sel'):
	"""Change inside ribbon color"""
	try:
		color = convertColor(color)
	except RuntimeError, e:
		raise MidasError(e)
	def _color(thing):
		thing.ribbonInsideColor = color
	_editMolecule(sel, _color)
ribinsidecolour = ribinsidecolor

def ribrepr(style, sel='sel'):
	if style == "flat" or style == "ribbon":
		# ball-and-stick
		mode = chimera.Residue.Ribbon_2D
	elif style == "sharp" or style == "edged":
		mode = chimera.Residue.Ribbon_Edged
	elif style == "smooth" or style == "rounded" or style == "round":
		mode = chimera.Residue.Ribbon_Round
	else:
		from RibbonStyleEditor import xsection
		exs = xsection.findXSection(style)
		if exs is None:
			raise MidasError('Unknown representation style "%s"'
								% style)
		xs = exs.getXS()
		mode = chimera.Residue.Ribbon_Custom
	def _residuestyle(thing):
		thing.ribbonDrawMode = mode
		if mode == chimera.Residue.Ribbon_Custom:
			thing.ribbonXSection = xs
	_editResidue(sel, _residuestyle)

def ribscale(name, sel='sel'):
	from RibbonStyleEditor import scaling
	if name == scaling.SystemDefault:
		def _residuestyle(thing):
			thing.ribbonStyle = None
		_editResidue(sel, _residuestyle)
	else:
		sc = scaling.findScaling(name)
		if sc is None:
			raise MidasError('Unknown ribbon scaling "%s"' % name)
		def _residuestyle(thing, sc=sc):
			sc.setResidue(thing)
		_editResidue(sel, _residuestyle)

def ribspline(stype, stiffness=0.8, smoothing="none", models=None):
	from chimera import Molecule
	if models is None:
		models = chimera.openModels.list(modelTypes=[Molecule])
	rt = stype.lower()
	if "default".startswith(rt) or "bspline".startswith(rt):
		for m in models:
			m.ribbonType = Molecule.RT_BSPLINE
	elif "cardinal".startswith(rt):
		smoothing = smoothing.lower()
		if "strand".startswith(smoothing):
			sm = Molecule.RSM_STRAND
		elif "coil".startswith(smoothing):
			sm = Molecule.RSM_COIL
		elif "both".startswith(smoothing):
			sm = Molecule.RSM_STRAND | Molecule.RSM_COIL
		elif "all".startswith(smoothing):
			sm = Molecule.RSM_STRAND | Molecule.RSM_COIL
		else:
			sm = 0
		for m in models:
			m.ribbonType = Molecule.RT_CARDINAL
			m.ribbonStiffness = stiffness
			m.ribbonSmoothing = sm
	else:
		raise MidasError("unknown ribbon spline type \"%s\"" % stype)

def fillring(style=None, sel='sel'):
	if style is None:
		def _filldisplay(thing):
			thing.fillDisplay = True
		_editResidue(sel, _filldisplay)
		return
	if style in ('unfilled', 'off'):
		return unfillring(sel)
	elif style == 'thin':
		mode = chimera.Residue.Thin
	elif style == 'thick':
		mode = chimera.Residue.Thick
	elif style not in (chimera.Residue.Thin, chimera.Residue.Thick):
		raise MidasError('unknown representation type ("%s")' % style)
	def _fillstyle(thing):
		thing.fillDisplay = True
		thing.fillMode = mode
	_editResidue(sel, _fillstyle)

def r3to1(rType):
	from chimera.resCode import res3to1
	l = res3to1(rType)
	if l == 'X':
		return rType
	return l

class ResAttrDict:
	retrieveDict = {
		"name": lambda r: r.type,
		"1-letter code": lambda r, r321 = r3to1: r321(r.type),
		"specifier": lambda r: str(r.id),
		"number": lambda r: r.id.position,
		"insertion code": lambda r: r.id.insertionCode.strip(),
		"chain": lambda r: r.id.chainId.strip()
	}
	def __init__(self, res, errClass):
		self.res = res
		self.errClass = errClass

	def __getitem__(self, item):
		try:
			return self.retrieveDict[item](self.res)
		except KeyError:
			try:
				return getattr(self.res, item)
			except AttributeError:
				raise self.errClass("No such attribute")
		return f(self.res)

def rlabel(sel='sel', offset=None, warnLarge=False):
	"""Display residue information as part of one atom label"""
	if offset == 'default':
		offset = chimera.Vector(chimera.Molecule.DefaultOffset, 0, 0)
	def _rlabel(r, offset=offset):
		if _rlabelInfo in ResAttrDict.retrieveDict:
			r.label = str(ResAttrDict.retrieveDict[_rlabelInfo](r))
		else:
			try:
				val = getattr(r, _rlabelInfo)
				if val is None:
					r.label = ""
				else:
					r.label = str(val)
			except AttributeError:
				try:
					r.label = _rlabelInfo % ResAttrDict(r, MidasError)
				except TypeError:
					raise MidasError("Bad label format;"
						" use 'help labelopt' for formatting info")
				if r.label == _rlabelInfo and _rlabelInfo.isalnum():
					r.label = ""
					raise MidasError("No such attribute")
		if offset is not None:
			r.labelOffset = offset
	_editResidue(sel, _rlabel)

def rmsd(f, t, log=True):
	import math
	fAtoms, tAtoms = _atomSpecErrorCheck(f, t)
	dSqrSum = 0
	for i in range(len(fAtoms)):
		dSqrSum += fAtoms[i].xformCoord().sqdistance(
							tAtoms[i].xformCoord())
	sol = dSqrSum / len(fAtoms)
	final = math.sqrt(sol)
	_showStatus('RMSD between %d atom pairs is %.3f angstroms'
						% (len(fAtoms), final), log=log)
	return final

def rock(axis, magnitude=90, frequency=60, frames= -1, coordinateSystem=None,
	 models=None, center=None):
	param = rockParam(axis, magnitude, frequency, frames, coordinateSystem,
		models, center)
	_addMotionHandler(_flight, param)

def rockParam(axis, magnitude=90, frequency=60, frames= -1, coordinateSystem=None,
	 models=None, center=None):
	'''construct and return parameters for rock command'''
	angles = []
	maximum = float(frequency - 1)
	for i in range(frequency):
		a = i / maximum * math.pi
		angles.append(magnitude * math.sin(a))
	v = _axis(axis)
	xformList = []
	for i in range(len(angles) - 1):
		delta = angles[i + 1] - angles[i]
		xformList.append(chimera.Xform.rotation(v, delta))
	param = {'command':'rock',
		'xformList':xformList,
		'counter':0,
		'direction':1,
		'mode':'bounce',
		'frames':frames,
		'coordinateSystem': coordinateSystem,
		'models': models,
		'center':center}
	return param

def roll(axis, angle=1.5, frames= -1, coordinateSystem=None, models=None,
	 center=None, precessionTilt=None):
	turn(axis, angle, frames, coordinateSystem, models,
	     center, precessionTilt)

def rotation(sel='sel', rotID=None, reverse=False, adjust=None, frames=None):
	from BondRotMgr import bondRotMgr
	if adjust is not None:
		if rotID is None:
			raise MidasError("Must specify rotation ID to adjust")
		from BondRotMgr import bondRotMgr
		if rotID not in bondRotMgr.rotations:
			raise MidasError("Bond rotation '%d' does not exist!"
				% rotID)
		rot = bondRotMgr.rotations[rotID]
		param = {
			'command': 'rotation',
			'adjust':adjust,
			'rot': rot,
			'frames': frames
		}
		if frames is None:
			_rotation(None, param, None)
		else:
			_addMotionHandler(_rotation, param)
		return rot
	atoms = _selectedAtoms(sel, ordered=True)
	if len(atoms) != 2:
		raise MidasError('Only two atoms must be selected.'
					'  You selected %d.' % len(atoms))
	bond = atoms[0].findBond(atoms[1])
	if bond == None:
		raise MidasError('Selected atoms are not connected'
						' with a covalent bond')
	from chimera import UserError
	try:
		br = bondRotMgr.rotationForBond(bond, requestedID=rotID)
	except UserError, v:
		raise MidasError(str(v))
	if reverse:
		br.anchorSide = br.SMALLER
	return br

def save(filename):
	from OpenSave import compressSuffixes
	for cs in compressSuffixes:
		if filename.endswith(cs):
			break
	else:
		if not filename.endswith(".py"):
			filename += ".py"
	from SimpleSession import saveSession
	saveSession(filename)

def savepos(name='default'):
	if name == "list":
		_showStatus("Saved positions: " + ", ".join(positions.keys()))
		return

	positions[name] = _savePosition()
	chimera.triggers.activateTrigger(ADD_POSITIONS, [name])

def scale(s, frames=None):
	updateZoomDepth()
	param = {'command':'scale', 'scaleFactor':s, 'frames':frames}
	if frames is None:
		_scale(None, param, None)
	else:
		_addMotionHandler(_scale, param)

def updateZoomDepth(viewer=None):
	if viewer is None:
		viewer = chimera.viewer
	from chimera import openModels
	try:
		cr = openModels.cofr
	except:
		return	# Indep rotation mode or no displayed/active models.
	zd = cr.z

	# Avoid setting zoom depth closer to eye than 1/10 model size.
	# This keeps zooming and translation with the mouse responsive.
	c = viewer.camera
	ze = c.eyePos(0)[2]
	have_box, bbox = openModels.bbox()
	if have_box:
		bsize = max(bbox.urb - bbox.llf)
		zd = min(zd, ze - bsize * 0.1)

	# Adjust view center.
	cc = c.center
	c.center = (cc[0], cc[1], zd)

	# Adjust view size for new center depth.
	# This applies to orthographic projection too because of the bizarre
	# way the Camera determines width of view in orthographic mode.
	dz = cc[2] - zd
	from math import pi, tan
	fov = c.fieldOfView * pi / 180
	try:
		dvs = tan(0.5 * fov) * dz * viewer.scaleFactor
	except:
		return	# Illegal field of view = 180 degrees.
	vsize = dvs + viewer.viewSize
	if vsize > 0:
		# If center of rotation is behind eye get vsize < 0.
		viewer.viewSize = vsize

def section(delta, frames=None):
	param = {'command':'section', 'plane':'section', 'delta':delta,
							'frames':frames}
	if frames is None:
		_clip(None, param, None)
	else:
		_addMotionHandler(_clip, param)

def select(sel='sel'):
	"""Make selected models active"""
	def _select(thing):
		thing.openState.active = 1
	_editModel(sel, _select)

def setAutoColor():
	from chimera import preferences
	from chimera.initprefs import MOLECULE_DEFAULT, MOL_AUTOCOLOR
	preferences.set(MOLECULE_DEFAULT, MOL_AUTOCOLOR, 1, asSaved=1)
	preferences.save()
setAutocolor = setAutocolour = setAutoColor	# Historical names

def setBgColor(color):
	background(color=color)
setBg_color = setBg_colour = setBgColor		# Historical names

def setBgTransparency():
	from chimera import printer
	printer.setTransparentBackground(True, updateGUI=True)

def setDepthCue():
	chimera.viewer.depthCue = True
setDepth_cue = setDepthCue			# Historical name

def setDcColor(color):
	try:
		chimera.viewer.depthCueColor = convertColor(color)
	except RuntimeError, e:
		raise MidasError(e)
setDc_color = setDc_colour = setDcColor		# Historical names

def setDcStart(s):
	v = chimera.viewer
	cs, ce = v.depthCueRange
	try:
		v.depthCueRange = float(s), ce
	except ValueError, e:
		raise MidasError(e)
setDc_start = setDcStart			# Historical name

def setDcEnd(e):
	v = chimera.viewer
	cs, ce = v.depthCueRange
	try:
		v.depthCueRange = cs, float(e)
	except ValueError, e:
		raise MidasError(e)
setDc_end = setDcEnd				# Historical name

_echoCommands = False
def setEcho():
        global _echoCommands
        _echoCommands = True
def unsetEcho():
        global _echoCommands
        _echoCommands = False
def echoCommands():
        return _echoCommands

def setEyeSeparation(sep_mm):
	from chimera import viewer, viewing
	viewing.setCameraEyeSeparation(float(sep_mm), viewer)
        
def setFullscreen():
	from chimera.tkgui import _setFullscreen
	class Tmp(object): pass
	o = Tmp()
	o.get = lambda: 1
	_setFullscreen(o)

def setIndependent():
	chimera.openModels.cofrMethod = chimera.OpenModels.Independent

def setLightQuality(q):
	pass					# Retired command
setLight_quality = setLightQuality		# Historical name

def setMaxFrameRate(rate):
	try:
		r = float(rate)
	except ValueError:
		raise MidasError('Maximum frame rate must be a number, '
				 'got %s' % str(rate))
	if r > 0:
		from chimera import update
		update.setMaximumFrameRate(r)

def setSingleLayer():
	chimera.viewer.singleLayerTransparency = True
setSingle = setSinglelayer = setSingleLayer	# Historical name

def setFlatTransparency():
	chimera.viewer.angleDependentTransparency = False

def setProjection(mode):
	ortho = mode.lower().startswith('o')
	chimera.viewer.camera.ortho = ortho

def setFieldOfView(degrees):
	try:
		a = float(degrees)
	except ValueError:
		raise MidasError('Field of view must be a number (degrees), '
				 'got %s' % str(degrees))
	if a <= 0 or a >= 180:
		raise MidasError('Field of view must be greater than 0 '
				 'and less than 180 degrees, got %s'
				 % str(degrees))
	chimera.viewer.camera.fieldOfView = a

def setScreenDistance(distance_mm):
	from chimera import viewer, viewing
	viewing.setCameraScreenDistance(float(distance_mm), viewer)

def setScreenWidth(width_mm):
	from chimera import viewer, viewing
	viewing.setScreenWidth(float(width_mm), viewer)

def setShadows():
	try:
		chimera.viewer.showShadows = True
	except chimera.error, what:
		raise MidasError("Unable to turn on shadows (%s)." % what)

def setShowCofR():
	chimera.viewer.showCofR = True

def unsetShowCofR():
	chimera.viewer.showCofR = False

def setSilhouette():
	chimera.viewer.showSilhouette = True

def setSilhouetteColor(color):
	try:
		chimera.viewer.silhouetteColor = convertColor(color)
	except RuntimeError, e:
		raise MidasError(e)
setSilhouette_color = setSilhouetteColor	# Historical name

def setSilhouetteWidth(width):
	try:
		w = float(width)
	except ValueError, e:
		raise MidasError(e)
	if w <= 0:
		raise MidasError('Silhouette width must be > 0, got %s' % width)
	chimera.viewer.silhouetteWidth = w
setSilhouette_width = setSilhouetteWidth	# Historical name

def setSubdivision(s):
	lod = chimera.LODControl.get()
	try:
		lod.quality = float(s)
	except ValueError, e:
		raise MidasError(e)

def setSubdivisionPixels(p):
	try:
		ppu = float(p)
	except ValueError, e:
		raise MidasError(e)
	lod = chimera.LODControl.get()
	if ppu > 0:
		lod.dynamicSubdivision = False
		lod.pixelsPerUnit = ppu
	else:
		unsetSubdivision_pixels()
setSubdivision_pixels = setSubdivisionPixels	# Historical name

def setAttr(level, name, val, sel='sel'):
	selFunc = _attrSelFunc(level)
	classTracking = {}
	from chimera import TrackChanges
	track = TrackChanges.get()
	reason = name + " changed"
	for item in selFunc(sel):
		setattr(item, name, val)
		klass = item.__class__
		needTrack = classTracking.get(klass, None)
		if needTrack == None:
			# Python layer attrs need explicit change tracking
			classTracking[klass] = needTrack = not hasattr(klass, name)
		if needTrack:
			track.addModified(item, reason)

def show(sel='sel', asChain=0):
	models = _selectedModels(sel)
	aDict = _selectedAtoms(sel, asDict=True)
	for m in models:
		if not hasattr(m, 'atoms'):
			continue
		if asChain:
			m.autochain = 1
		for a in m.atoms:
			a.display = a in aDict

def chain(*args, **kw):
	kw["asChain"] = 1
	show(*args, **kw)

def stereo(mode, domeTiltAngle=None, domeParallaxAngle=None):
	try:
		mode = chimera.StereoKwMap[mode]
	except KeyError:
		raise MidasError("Unknown stereo mode: %s" % mode)
	tilt = (not domeTiltAngle is None)
	if tilt:
		import _dome
		_dome.setDomeTiltAngle(domeTiltAngle)
	parallax = (not domeParallaxAngle is None)
	if parallax:
		import _dome
		_dome.setDomeParallaxAngle(domeParallaxAngle)
	if (tilt or parallax) and mode == 'dome':
		# Force redisplay for new parallax angle.
		v = chimera.viewer
		if v.camera.mode() == 'dome':
			v.postRedisplay()
	from chimera.viewing import setCameraMode
	return setCameraMode(mode, chimera.viewer)

surfaceMethods = {
	"msms":		chimera.MSMSModel,
}
def registerSurfaceMethod(name, func):
	surfaceMethods[name] = func

def surfaceNew(category, sel='sel', models=None, method=None,
	       probeRadius = None, vertexDensity = None, allComponents = None,
	       grid = None):
	if category in ['ions', 'solvent']:
		_showStatus("Surfacing ions/solvent not yet supported;"
			" skipping those.", log=False, color='red')
		return []
	modelClass = chimera.MSMSModel
	if method:
		try:
			modelClass = surfaceMethods[method]
		except KeyError:
			raise MidasError("Unknown surface method: %s" % method)
	if models is None:
		models = _selectedModels(sel)

	from chimera.initprefs import (
		SURFACE_DEFAULT, SURF_REPR, SURF_PROBE_RADIUS,
		SURF_DENSITY, SURF_LINEWIDTH, SURF_DOTSIZE,
		SURF_DISJOINT)
	from chimera.preferences import get as prefget
	if probeRadius is None:
		probeRadius = prefget(SURFACE_DEFAULT, SURF_PROBE_RADIUS)
	if vertexDensity is None:
		vertexDensity = prefget(SURFACE_DEFAULT, SURF_DENSITY)
	if allComponents is None:
		allComponents = prefget(SURFACE_DEFAULT, SURF_DISJOINT)
	allComponents = bool(allComponents)

	if not grid is None:
		from Surface import gridsurf
		surfs = []
		for m in models:
			atoms = tuple(a for a in m.primaryAtoms() if a.surfaceCategory == category)
			if atoms:
				s = gridsurf.ses_surface(atoms, probeRadius, grid_spacing = grid,
							 name = '%s SES %s surface' % (m.name, category))
				surfs.append(s)
		return surfs

	surfs = []
	for m in models:
		surf = None
		surfModels = chimera.openModels.list(m.id,
					modelTypes=[modelClass])
		for s in surfModels:
			if s.subid == m.subid and s.category == category:
				s.update_parameters(probeRadius,
						    vertexDensity,
						    allComponents)
				surfs.append(s)
				break
		else:
			surf = modelClass(m, category, probeRadius,
					  allComponents, vertexDensity)
			surf.drawMode = prefget(SURFACE_DEFAULT, SURF_REPR)
			surf.lineWidth = prefget(SURFACE_DEFAULT, SURF_LINEWIDTH)
			surf.pointSize = prefget(SURFACE_DEFAULT, SURF_DOTSIZE)
			surf.display = m.display # if model hidden, so is surface
			if m.name:
				catname = category
				surf.name = "MSMS %s surface of %s" % (catname,
									m.name)
			if not getattr(surf, 'calculationFailed', False):
				chimera.openModels.add([surf], sameAs=m)
				surfs.append(surf)
	return surfs

def surfaceDelete(category, sel='sel'):
	models = _selectedModels(sel, chimera.MSMSModel)
	models = filter(lambda m, c=category: m.category == c, models)
	chimera.openModels.close(models)

def surface(atomSpec='sel', category='main', warnLarge=False,
	    visiblePatches=None, **kw):
	def _surfaceDisplay(thing):
		thing.surfaceDisplay = 1

	if warnLarge and not chimera.nogui:
		numAffected = len(_selectedModels(atomSpec))
		if numAffected > 20:
			from chimera.tkgui import SurfaceWarningDialog
			SurfaceWarningDialog(numAffected,
					     lambda : surface(atomSpec, category,
                                                              visiblePatches = visiblePatches,
                                                              **kw))
			return
	if category != "all categories":
		surfs = surfaceNew(category, atomSpec, **kw)
		if 'grid' in kw:
			return
		aSpec = "%s & @/surfaceCategory=%s" % (atomSpec, category)
		atoms = _editAtom(aSpec, _surfaceDisplay)
	else:
		surfs = []
		categories = {}
		selAtoms = _selectedAtoms(atomSpec)
		for atom in selAtoms:
			categories.setdefault(atom.surfaceCategory, set()).add(
								atom.molecule)
		for category, models in categories.items():
			if category in ['ions', 'solvent']:
				continue
			surfs.extend(surfaceNew(category, models=models, **kw))
		atoms = _editAtom(atomSpec, _surfaceDisplay)
	surfaceVisibilityByAtom(atoms)
	if not visiblePatches is None:
		import HideDust
		for s in set(surfs):
			s.update_visibility()
			HideDust.show_only_largest_blobs(s.surface_piece, True,
							 visiblePatches,
							 'area rank')


def surfaceVisibilityByAtom(atoms):
	for s in atomMSMSModels(atoms).keys():
		s.visibilityMode = s.ByAtom

def atomMSMSModels(atoms):
	molcat = {}
	from chimera import MSMSModel
	for surf in chimera.openModels.list(modelTypes=[MSMSModel]):
		molcat[(surf.molecule, surf.category)] = surf
	surfatoms = {}
	for a in atoms:
		amc = (a.molecule, a.surfaceCategory)
		if amc in molcat:
			surf = molcat[amc]
			surfatoms.setdefault(surf, []).append(a)
	return surfatoms

def surfaceCategory(category, sel='sel'):
	def _category(thing, c):
		thing.surfaceCategory = c
	_editAtom(sel, lambda t, c=category, f=_category: f(t, c))

def surfacecolormode(style, sel='sel'):
	mode = None
	if style == "bymodel":
		mode = chimera.MSMSModel.ByMolecule
	elif style == "byatom":
		mode = chimera.MSMSModel.ByAtom
	elif style == "custom":
		mode = chimera.MSMSModel.Custom
	else:
		raise MidasError('Unknown surface color mode "%s"' % style)
	models = _selectedModels(sel, chimera.MSMSModel)
	for m in models:
		m.colorMode = mode
surfacecolourmode = surfacecolormode

def surfacerepresent(style, sel='sel'):
	mode = None
	if style == "filled" or style == "solid":
		mode = chimera.MSMSModel.Filled
	elif style == "mesh":
		mode = chimera.MSMSModel.Mesh
	elif style == "dot":
		mode = chimera.MSMSModel.Dot
	else:
		raise MidasError('Unknown surface representation style "%s"'
								% style)
	models = _selectedModels(sel, chimera.MSMSModel)
	for m in models:
		m.drawMode = mode

def surfacetransparency(val, sel='sel', frames=None):
	if not val is None:
		val = (100.0 - val) / 100.0
	atoms = _selectedAtoms(sel)
	plist = _selectedSurfacePieces(sel)
	if frames is None or frames < 2:
		_surftransp(val, atoms, plist)
	else:
		def cb(frac, val=val, atoms=atoms, plist=plist):
			_surftransp(val, atoms, plist, frac)
		fracs = [(1.0 / n,) for n in range(frames, 0, -1)]
		fracs[-1] = (1,)
		addNewFrameCallback(cb, fracs)

def addNewFrameCallback(func, fargs):
	def call(tname, cdata, fnum):
		f, fargs, h = cdata
		if len(fargs) == 0:
			chimera.triggers.deleteHandler('new frame', h)
		else:
			args = fargs[0]
			params[1] = fargs[1:]
			f(*args)
	params = [func, fargs, None]
	params[2] = chimera.triggers.addHandler('new frame', call, params)

def _surftransp(opac, atoms, plist, frac=1):

	from chimera import actions
	actions.adjustAtomsSurfaceOpacity(atoms, opac, frac)
	if opac is None:
		opac = 1.0
	for p in plist:
		s = p.model
		msurf = (isinstance(s, chimera.MSMSModel) and s.molecule
			 and p == s.surface_piece)
		if msurf:
			actions.adjustMSMSTransparency(s, atoms, opac, frac=frac)
		else:
			actions.adjustSurfacePieceTransparency(p, opac, frac)

def swapres(newRes, sel='sel', preserve=False, bfactor=None):
	from SwapRes import swap, SwapResError
	newRes = newRes.upper()
	selResidues = _selectedResidues(sel)
	if not selResidues:
		raise MidasError("No residues specified for swapping")
	for res in selResidues:
		try:
			swap(res, newRes, preserve=preserve, bfactor=bfactor)
		except SwapResError, v:
			raise MidasError(v)
		if res.label:
			res.label = '%s %s' % (res.type, res.id)
swapna = swapres
# swapaa now implemented by Rotamers module

def tColor(index, sel='sel'):
	if not currentTexture:
		textureNew('default')

	index, atomItems, bondItems, resItems = _colorSplit(index)

	if index in ['byatom', 'byelement', 'byhet', 'byhetero']:
		raise MidasError('Cannot texture color byatom/byhet'
					' (too many colors required)')
	try:
		color = currentTexture.color(index)
	except KeyError:
		from chimera import UserError
		raise UserError('Texture color "%s" is undefined' % index)

	if atomItems:
		def _color(thing, items=atomItems, color=color):
			for item in atomItems:
				setattr(thing, item, color)
		_editAtom(sel, _color)

	if bondItems:
		def _color(thing, items=bondItems, color=color):
			for item in bondItems:
				setattr(thing, item, color)
		_editBond(sel, _color)

	if resItems:
		def _color(thing, items=resItems, color=color):
			for item in items:
				setattr(thing, item, color)
		_editResidue(sel, _color)

def textureColor(index, color):
	if not currentTexture:
		textureNew('default')

	currentTexture.setColor(index, color)
textureColour = textureColor

def textureMap(**kw):
	if not currentTexture:
		textureNew('default')

	for key in kw.keys():
		if key[:5] != "color":
			raise MidasError, "Unexpected keyword argument: " + key
		try:
			index = int(key[5:])
		except ValueError:
			raise MidasError, "Unexpected keyword argument: " + key

		if index < 1 or index > len(currentTexture.textureColors):
			raise MidasError, \
			  "Index (%d) out of bounds for current texture" % index
		currentTexture.mapName(index, kw[key])

		# if the name is a color name, set the index to that color
		c = chimera.Color.lookup(kw[key])
		if c is not None:
			currentTexture.setColor(index, c)


def textureNew(name, numColors=5):
	import Texturer
	global currentTexture

	if textures.has_key(name):
		raise MidasError, "Texture named " + name + " already exists"

	if numColors == 5:
		currentTexture = Texturer.FiveColorTexture()
	elif numColors == 4:
		currentTexture = Texturer.FourColorTexture()
	else:
		raise MidasError, "Number of colors for texture must be 4 or 5"

	# allow for integer strings to be used as indices
	for i in range(1, len(currentTexture.textureColors) + 1):
		currentTexture.mapName(i, str(i))
	textures[name] = currentTexture

def textureUse(name):
	global currentTexture
	if not currentTexture:
		textureNew('default')

	try:
		currentTexture = textures[name]
	except KeyError:
		raise MidasError, "No texture named '" + name + "' exists"

def thickness(delta, frames=None):
	param = {'command':'thickness', 'plane':'thickness', 'delta':delta / 2.0,
							'frames':frames}
	if frames is None:
		_clip(None, param, None)
	else:
		_addMotionHandler(_clip, param)

def transparency(trans, sel='sel', items=None, frames=None):
	alpha = (100.0 - trans) / 100.0
	atomItems, bondItems, resItems = _colorItems(items)
	atoms = _selectedAtoms(sel) if atomItems else []
	bonds = _selectedBonds(sel) if bondItems else []
	residues = _selectedResidues(sel) if resItems else []
	plist = _selectedSurfacePieces(sel) if 'surfaceColor' in atomItems else []
	if frames is None or frames < 2:
		_transp(alpha, atomItems, atoms, bondItems, bonds,
			resItems, residues, plist)
	else:
		def cb(frac, alpha=alpha, atomItems=atomItems, atoms=atoms,
		       bondItems=bondItems, bonds=bonds,
		       resItems=resItems, residues=residues, plist=plist):
			_transp(alpha, atomItems, atoms, bondItems, bonds,
				resItems, residues, plist, frac)
		fracs = [(1.0 / n,) for n in range(frames, 0, -1)]
		fracs[-1] = (1,)
		addNewFrameCallback(cb, fracs)

def _transp(alpha, atomItems, atoms, bondItems, bonds,
	    resItems, residues, plist, frac=1):
	if 'surfaceColor' in atomItems:
		_surftransp(alpha, atoms, plist, frac)
		atomItems = list(atomItems)
		atomItems.remove('surfaceColor')
	_transpItems(atoms, atomItems, alpha, frac)
	_transpItems(bonds, bondItems, alpha, frac)
	_transpItems(residues, resItems, alpha, frac)

def _transpItems(objects, attributes, alpha, frac):
	from chimera import Color, MaterialColor
	for attr in attributes:
		for o in objects:
			c = getattr(o, attr)
			if c is None:
				c = (o.shownColor() if hasattr(o, 'shownColor')
				     else o.molecule.color)
			r, g, b, a = c.rgba()
			af = frac * alpha + (1 - frac) * a
			setattr(o, attr, MaterialColor(r, g, b, af))

def turn(axis, angle=1.5, frames=None, coordinateSystem=None, models=None,
	 center=None, precessionTilt=None):
	param = turnParam(axis, angle, frames, coordinateSystem, models,
			  center, precessionTilt)
	param['removalHandler'] = _removeMotionHandler
	if frames is None:
		_movement(None, param, None)
	else:
		_addMotionHandler(_movement, param)

def turnParam(axis, angle=1.5, frames=None, coordinateSystem=None, models=None,
	      center=None, precessionTilt=None):
	v = _axis(axis)
	param = {'command':'turn',
		 'xform':chimera.Xform.rotation(v, angle),
		 'frames':frames,
		 'coordinateSystem':coordinateSystem,
		 'models':models,
		 'center':center}
	if not precessionTilt is None:
		import Matrix
		x,y,z = Matrix.orthonormal_frame(v.data())
		from math import sin, cos, pi
		a = precessionTilt*pi/180
		pa = Matrix.linear_combination(cos(a), z, -sin(a), y)
		param['precessionAxis'] = chimera.Vector(*pa)
		param['precessionStep'] = -angle
	return param

def unbond(sel='sel'):
	atoms = _selectedAtoms(sel, asDict=True)
	for a1 in atoms:
		for a2, b in a1.bondsMap.items():
			if a2 in atoms:
				a1.molecule.deleteBond(b)

def unbondcolor(sel='sel'):
	atoms = _selectedAtoms(sel)
	for b in misc.bonds(atoms, internal=True):
		b.color = None
		b.halfbond = True
unbondcolour = unbondcolor

def unchimeraSelect(sel='sel'):
	if not isinstance(sel, selection.Selection):
		sel = evalSpec(sel)
	if not hasattr(sel, 'addImplied'):
		newSel = selection.ItemizedSelection()
		newSel.merge(selection.REPLACE, sel)
		sel = newSel
	sel.addImplied(vertices=0)
	# ~select implies removal, regardless of selection mode
	selection.mergeCurrent(selection.REMOVE, sel)

def unclip(plane):
	for mh in _motionHandlers[:]:
		if mh['command'] == 'clip' and mh['plane'] == plane:
			_removeMotionHandler(mh)

def uncofr():
	from chimera import viewing
	chimera.openModels.cofrMethod = viewing.defaultCofrMethod

def uncolor(which, sel='sel'):
	"""Clear atom color"""
	atomItems, bondItems, resItems = _colorItems(which)
	if atomItems:
		def _uncolor(atom, items=atomItems):
			for item in items:
				setattr(atom, item, None)
		_editAtom(sel, _uncolor)
	if bondItems:
		def _uncolor(bond, items=bondItems):
			for item in items:
				setattr(bond, item, None)
			bond.halfbond = True
		_editBond(sel, _uncolor)
	if resItems:
		def _uncolor(residue, items=resItems):
			for item in items:
				setattr(residue, item, None)
		_editResidue(sel, _uncolor)
uncolour = uncolor

def undisplay(sel='sel'):
	"""Undisplay atoms

	Atoms specification may come from either a selection or
	an osl string.  If no atom specification is supplied,
	the current selection is undisplayed."""
	def _undisplay(thing):
		thing.display = 0
	_editAtomBond(sel, _undisplay, None)

def undistance(sel='sel'):
	"""Remove distance monitor"""
	if isinstance(sel, basestring):
		if sel == "all":
			for b in DistMonitor.distanceMonitor.pseudoBonds:
				DistMonitor.removeDistance(b)
			return
		sel = evalSpec(sel)
	atoms = sel.atoms()
	if len(atoms) != 2:
		raise MidasError('Exactly two atoms must be selected.  You '
				'selected %d.' % len(atoms))
	try:
		DistMonitor.removeDistance(atoms[0], atoms[1])
	except ValueError, s:
		raise MidasError('Error removing distance: %s.' % s)

def unfillring(sel='sel'):
	"""turn off ring filling"""
	def _fillstyle(thing):
		thing.fillDisplay = False
	_editResidue(sel, _fillstyle)

def unlabel(sel='sel'):
	"""Add label to selected atoms"""
	def _unlabel(thing):
		thing.label = ''
	_editAtom(sel, _unlabel)

def unlongbond():
	from chimera import LONGBOND_PBG_NAME
	from chimera.misc import getPseudoBondGroup
	pbg = getPseudoBondGroup(LONGBOND_PBG_NAME)
	if not pbg.display:
		raise MidasError("Missing segments already hidden."
				" Use longbond to show them.")
	pbg.display = False

def unmodeldisplay(sel='sel'):
	def _unmodeldisplay(thing):
		thing.display = 0
	_editModel(sel, _unmodeldisplay)

def unnamesel(selName):
	from chimera.selection import delNamedSel, savedSels
	if selName in savedSels:
		delNamedSel(selName)
	else:
		raise MidasError("No selection named '%s'" % selName)

def unobjdisplay(sel):
	def _unobjdisplay(thing):
		if not isinstance(thing, chimera.Molecule) \
		and not isinstance(thing, chimera.MSMSModel):
			thing.display = 0
	_editModel(sel, _unobjdisplay)

def unribinsidecolor(which, sel='sel'):
	"""Clear inside ribbon color"""
	def _uncolor(thing):
		thing.ribbonInsideColor = None
	_editMolecule(sel, _uncolor)
unribinsidecolour = unribinsidecolor

def unribbon(sel='sel'):
	def _undisplay(thing):
		thing.ribbonDisplay = 0
	_editResidue(sel, _undisplay)

def unribbackbone(sel='sel'):
	def _unribbackbone(thing):
		thing.ribbonHidesMainchain = 1
	_editMolecule(sel, _unribbackbone)

def unfilldisplay(sel='sel'):
	def _undisplay(thing):
		thing.fillDisplay = False
	_editResidue(sel, _undisplay)

def unrlabel(sel='sel'):
	"""Do not display residue information as part of any atom label"""
	def _residuedisplay(r):
		r.label = ""
	_editResidue(sel, _residuedisplay)

def unrotation(rotID):
	from BondRotMgr import bondRotMgr
	try:
		br = bondRotMgr.rotations[rotID]
	except KeyError:
		raise MidasError("No such bond rotation")
	br.destroy()

def unsavepos(name):
	try:
		del positions[name]
	except KeyError:
		raise MidasError("No position named '%s'" % name)
	chimera.triggers.activateTrigger(REMOVE_POSITIONS, [name])

def removeAllSavedPositions():
	positionNames = positions.keys()
	positions.clear()
	chimera.triggers.activateTrigger(REMOVE_POSITIONS, positionNames)

def unscale():
	for mh in _motionHandlers[:]:
		if mh['command'] == 'scale':
			_removeMotionHandler(mh)

def unselect(sel='sel'):
	"""Make selected models inactive"""
	def _unselect(thing):
		thing.openState.active = 0
	_editModel(sel, _unselect)

def unsetAutoColor():
	from chimera import preferences
	from chimera.initprefs import MOLECULE_DEFAULT, MOL_AUTOCOLOR
	preferences.set(MOLECULE_DEFAULT, MOL_AUTOCOLOR, 0, asSaved=1)
	preferences.save()
unsetAutocolour = unsetAutocolor = unsetAutoColor	# Historical name

def unsetBgTransparency():
	from chimera import printer
	printer.setTransparentBackground(False, updateGUI=True)

def unsetDepthCue():
	chimera.viewer.depthCue = False
unsetDepth_cue = unsetDepthCue			# Historical name

def unsetFullscreen():
	from chimera.tkgui import _setFullscreen
	class Tmp(object): pass
	o = Tmp()
	o.get = lambda: 0
	_setFullscreen(o)

def unsetIndependent():
	from chimera import viewing
	chimera.openModels.cofrMethod = viewing.defaultCofrMethod

def unsetSingleLayer():
	chimera.viewer.singleLayerTransparency = False
unsetSingle = unsetSinglelayer = unsetSingleLayer	# Historical name

def unsetFlatTransparency():
	chimera.viewer.angleDependentTransparency = True

def unsetShadows():
	chimera.viewer.showShadows = False

def unsetSilhouette():
	chimera.viewer.showSilhouette = False

def unsetSubdivisionPixels():
	lod = chimera.LODControl.get()
	if not lod.dynamicSubdivision:
		lod.dynamicSubdivision = True
		c = chimera.viewer.camera
		w0, w1 = c.window(0)[:2]
		lod.pixelsPerUnit = (c.urx() - c.llx()) / (w1 - w0)
unsetSubdivision_pixels = unsetSubdivisionPixels	# Historical name

def unsetAttr(level, name):
	selFunc = _attrSelFunc(level)
	classTracking = {}
	from chimera import TrackChanges
	track = TrackChanges.get()
	reason = name + " changed"
	someMissing = someWrong = False
	for item in selFunc("#"):
		try:
			delattr(item, name)
		except TypeError:
			someWrong = True
			continue
		except AttributeError:
			someMissing = True
			continue
		klass = item.__class__
		needTrack = classTracking.get(klass, None)
		if needTrack == None:
			# Python layer attrs need explicit change tracking
			classTracking[klass] = needTrack = not hasattr(klass, name)
		if needTrack:
			track.addModified(item, reason)
	if someWrong:
		raise MidasError("Cannot delete attribute '%s'" % name)
	if someMissing:
		_showStatus("Some objects had no '%s' attribute" % name, color="red", log=False)

unshow = undisplay

def unsurface(sel='sel'):
	def _surfaceDisplay(thing):
		thing.surfaceDisplay = 0
	atoms = _editAtom(sel, _surfaceDisplay)
	surfaceVisibilityByAtom(atoms)
	orphan_surfaces = [s for s in _selectedModels(sel, chimera.MSMSModel)
			   if s.molecule is None]
	chimera.openModels.close(orphan_surfaces)

def unvdw(sel='sel'):
	"""Hide point vdw surface of atoms

	Atoms specification may come from either a selection or
	an osl string.  If no atom specification is supplied,
	the current selection is displayed."""
	def _unvdw(thing):
		thing.vdw = 0
	_editAtom(sel, _unvdw)

def unvdwdefine(sel='sel'):
	"""Revert to default VDW radii"""
	def _revertVDW(thing):
		thing.revertDefaultRadius()
	_editAtom(sel, _revertVDW)

def vdw(sel='sel'):
	"""Display point vdw surface of atoms

	Atoms specification may come from either a selection or
	an osl string.  If no atom specification is supplied,
	the current selection is displayed."""
	def _vdw(thing):
		thing.vdw = 1
	_editAtom(sel, _vdw)

def vdwdefine(radius, sel='sel', increment=False):
	"""Change vdw radius"""
	errors = []
	def _vdwdefine(a, radius=radius, increment=increment, errors=errors):
		r = a.residue
		if increment:
			rad = a.radius
			rad += radius
			if rad <= 0.0:
				errors.append(1)
				rad = 0.1
			a.radius = rad
		else:
			a.radius = radius
	_editAtom(sel, _vdwdefine)
	if errors:
		replyobj.error(
			"Some radii too small to decrement; set to 0.1\n")

def vdwdensity(density, sel='sel'):
	"""Change vdw surface point density"""
	def _vdwdensity(thing, density=density):
		thing.vdwDensity = density
	_editMolecule(sel, _vdwdensity)

def version():
	if not chimera.nogui:
		dialogs.display(chimera.tkgui._OnVersionDialog.name)
	else:
		import platform
		bits = "64" if sys.maxsize > 2 ** 32 else ""
		plat = '%s%s' % (platform.system(), bits)
		from chimera import version
		print "UCSF Chimera:", version.version
		print "Platform:", plat

def _waiting(param):
	return param['frames'] > 0

def wait(frames= -1):
	if frames < 0:
		frames = _motionRemaining()
	if frames <= 0:
		return
	param = {'command':'wait', 'frames':frames}
	_addMotionHandler(_wait, param)
	import chimera.update
	if chimera.nogui:
		app = None
	else:
		app = chimera.tkgui.app
	chimera.update.wait(lambda p=param: _waiting(p), app)

def window(sel='sel'):
	"""Recompute window parameters"""
	if sel == '#':
		chimera.viewer.viewAll(resetCofrMethod=False)
		return
	# mimic chimera.viewer.viewAll with the current selection
	box = boundingBox(sel)
	if box is None:
		raise MidasError("Nothing to window")
	v = chimera.viewer
	llf = box.llf
	urb = box.urb
	b = chimera.openModels.bbox()[1]
	width, height = v.windowSize
	winAspect = float(width) / float(height)
	modAspect = (urb[0] - llf[0]) / (urb[1] - llf[1])
	if winAspect >= modAspect:
		viewSize = (urb[1] - llf[1]) / 2 * winAspect
	else:
		viewSize = (urb[0] - llf[0]) / 2
	adjust = 0
	if viewSize > 0:
		adjust = viewSize * 0.01	# 2% slop (1% above and below)
	if adjust < 2.1:
		adjust = 2.1;			# minimum (elements P, CL)
	viewSize += adjust;
	v.setViewSizeAndScaleFactor(viewSize, 1.0)
	camera = v.camera
	camera.center = box.center().data()
	v.clipping = True
	focal = box.center()[2]
	camera.nearFar = focal + viewSize, focal - viewSize
	camera.focal = focal

def boundingSphere(sel):
	'Return a bounding sphere for the selection'
	s = None
	atoms = _selectedAtoms(sel)
	if atoms:
		pts = [a.xformCoord() for a in atoms]
		valid, s = chimera.find_bounding_sphere(pts)
		assert(valid)
	plist = _selectedSurfacePieces(sel)
	if plist:
		import Surface
		ps = Surface.surface_sphere(plist)
		if ps:
			if s:
				s.merge(ps)
			else:
				s = ps
	return s

def boundingBox(sel):
	'Return a bounding box for the selection'
	box = None
	atoms = _selectedAtoms(sel)
	if atoms:
		for a in atoms:
			p = a.xformCoord()
			r = a.radius
			rv = chimera.Vector(r, r, r)
			if box:
				box.add(p - rv)
				box.add(p + rv)
			else:
				box = chimera.BBox()
				box.llf = p - rv
				box.urb = p + rv
	plist = _selectedSurfacePieces(sel)
	if plist:
		import Surface
		pb = Surface.surface_box(plist)
		if pb:
			if box:
				box.merge(pb)
			else:
				box = pb
	return box

def windoworigin(xy=None):
	"Return the window origin if no arguments, or set it to (x, y)"
	if chimera.nogui:
		return
	top = chimera.tkgui.app.winfo_toplevel()
	geom = top.wm_geometry()
	parts = geom.split('+')
	if xy is None:
		_showStatus("window origin is %s, %s" % tuple(parts[1:3]))
		return
	new_geom = parts[0] + "+%d+%d" % xy

	top.wm_geometry(new_geom)
	chimera.tkgui.update_windows()
	top.wm_geometry('')

def windowsize(wh=None):
	"Return the window size if no arguments, or set it to (width, height)"
	v = chimera.viewer
	if wh is None:
		_showStatus("window size is %dx%d" % v.windowSize)
		return
	width, height = wh
	if chimera.nogui or chimera.fullscreen:
		v.windowSize = width, height
		return
	from chimera.tkgui import app
	graphics, rapidAccess = app.graphics, app.rapidAccess
	from midas_text import scripting
	showRA = app.toolbar.work == rapidAccess and not scripting
	if v.windowSize == wh and not showRA:
		return

	# to restore very small windows (narrower than status line etc.)
	# these contortions seem to be necessary...
	if app.toolbar.work == rapidAccess:
		# way too hairy to get this to work with rapidAccess up!
		app.toolbar.work = graphics
	app.allowResize = False
	top = app.winfo_toplevel()
	top.wm_geometry('')
	graphics.grid_configure(sticky='')
	s = v.pixelScale
	graphics.config(width=width/s, height=height/s)
	app.updateBackground(False)
	top.update_idletasks()
	parent = graphics.winfo_parent()
	if isinstance(parent, str):
		parent = graphics._nametowidget(parent)
	info = graphics.grid_info()
	def cleanUp(showRA=showRA, row=info['row'], col=info['column'], parent=parent, app=app,
			ra=rapidAccess):
		xywh = parent.grid_bbox(row, col)
		ra.config(width=xywh[2], height=xywh[3])
		if showRA:
			app.toolbar.work = ra
		app.allowResize = True
	app.after(500, lambda cleanUp=cleanUp, *args: cleanUp())

def unwindowsize():
	if chimera.nogui:
		return
	chimera.tkgui.app.graphics.grid_configure(sticky='news')

def write(writeModel, relModel, filename, allFrames=False, dispOnly=False,
				selOnly=False, format="pdb", resNum=True,
				atomTypes="sybyl", temporary=False, serialNumbering='h36'):
	"""write a PDB or Mol2 file
	
	   write coordinates relative to relModel position.  If relModel
	   is None, write current coordinates.

	   allFrames controls whether all frames of a trajectory are 
	   written out or just the current frame

	   dispOnly, if true, means to write only displayed atoms

	   selOnly, if true, means to write only selected atoms

	   format should be "pdb" or "mol2"

	   if format is mol2, resNum controls whether residue sequence
	   numbers are included in substructure names.  Ignored if format
	   is pdb. Similarly, if format is mol2, write Sybyl atom types if
	   atomTypes is "sybyl", Amber/GAFF atom types if atomTypes is "gaff"
	   or "amber".

	   If serialNumbering is 'h36', then large structures that would overflow
	   PDB serial number fields (>=100,000 atoms) will use "hybrid-36" numbering
	   to stay within the field size.  If serialNumbering is "amber", then
	   the 6th column of the ATOM record will be "stolen" to provide an additional
	   digit.  The latter approach doesn't help for structures that also overflow
	   the residue number field (>999 residues in a chain).
	"""
	if relModel is None:
		xform = chimera.Xform.identity()
	else:
		try:
			xform = relModel.openState.xform
		except AttributeError:
			mList = _getModelsFromId(relModel)
			if len(mList) != 1:
				id, subid = relModel
				if subid is None:
					s = str(id)
				else:
					s = "%d.%d" % (id, subid)
				raise MidasError, "%d model ids match \"%s\"" \
							% (len(mList), s)
			relModel = mList[0]
			xform = relModel.openState.xform
		xform.invert()
	if isinstance(writeModel, list):
		mList = writeModel
	elif isinstance(writeModel, tuple):
		mList = _getModelsFromId(writeModel,
					modelTypes=[chimera.Molecule])
	else:
		mList = [writeModel]
	fmt = format.lower()
	if fmt == "pdb" or fmt == "pqr":
		import PDBmatrices
		for m in mList:
			try:
				m.openState
			except ValueError:
				# Do not bother with transformations for
				# models that are not in openModels list
				pass
			else:
				PDBmatrices.transform_pdb_biomt_remarks(m, xform)
		from OpenSave import osOpen
		from chimera import pdbWrite, viewer
		try:
			f = osOpen(filename, 'w')
			pdbWrite(mList, xform, f,
				 allFrames=allFrames,
				 displayedOnly=dispOnly,
				 selectedOnly=selOnly,
				 selectionSet=set(selection.currentAtoms()),
				 asPQR=(fmt == "pqr"),
				 h36=(serialNumbering=="h36"))
		except IOError, v:
			raise MidasError(v)
		finally:
			for m in mList:
				PDBmatrices.restore_pdb_biomt_remarks(m)
		f.close()
		if not temporary:
			from chimera import triggers
			triggers.activateTrigger('file save', (filename, 'PDB'))
	elif fmt == "mol2":
		if allFrames:
			raise MidasError("Trajectories cannot be written in"
							" Mol2 format")
		if (dispOnly or selOnly) and not isinstance(mList,
							selection.Selection):
			ml = selection.ItemizedSelection()
			ml.add(mList)
			mList = ml
		if dispOnly:
			ml = selection.ItemizedSelection()
			ml.add([a for a in mList.atoms() if a.display])
			mList = ml
		if selOnly:
			mList.merge(selection.INTERSECT,
						selection.copyCurrent())
		writeGaff = atomTypes in ["gaff", "amber"]
		from WriteMol2 import writeMol2
		try:
			writeMol2(mList, filename, relModel=relModel, resNum=resNum,
						gaffType=writeGaff, gaffFailError=MidasError,
						temporary=temporary)
		except IOError, v:
			raise MidasError(v)
	elif fmt == "sph":
		try:
			import sphgen
		except ImportError:
			raise MidasError("unknown output format \"%s\"" % format)
		from OpenSave import osOpen
		try:
			f = osOpen(filename, 'w')
		except IOError, v:
			raise MidasError(v)
		try:
			sphgen.writeSphgen(mList, xform, f,
						displayedOnly=dispOnly,
						selectedOnly=selOnly)
		except IOError, v:
			raise MidasError(v)
		finally:
			f.close()
	else:
		raise MidasError("unknown output format \"%s\"" % format)
	import os
	from os.path import isabs
	if isabs(filename):
		replyobj.status("Wrote %s" % filename, log=True)
	else:
		replyobj.status("Wrote %s into %s" % (filename, os.getcwd()),
								log=True)

def _getModelsFromId(mid, **kw):
	id, subid = mid
	kw['id'] = id
	if subid is not None:
		kw['subid'] = subid
	mList = chimera.openModels.list(**kw)
	if not mList:
		if subid is None:
			s = str(id)
		else:
			s = "%d.%d" % (id, subid)
		raise MidasError, "no model ids match \"%s\"" % s
	return mList

#
# General utility functions
#
def deleteAtomsBonds(atoms=[], bonds=[]):
	# also called from tkgui/Build Structure
	residues = set()
	for b in set(bonds):
		b.atoms[0].molecule.deleteBond(b)
	for a in set(atoms):
		residues.add(a.residue)
		a.molecule.deleteAtom(a)
	mols = set()
	for r in residues:
		if len(r.atoms) == 0:
			mols.add(r.molecule)
			r.molecule.deleteResidue(r)
	nullModels = []
	for m in mols:
		if len(m.atoms) == 0:
			nullModels.append(m)
	if nullModels:
		chimera.openModels.close(nullModels)

def model(n):
	if isinstance(n, basestring):
		mList = _selectedModels[0]
	else:
		mList = chimera.openModels.list(n)
	if len(mList) == 1:
		(m,) = mList
		return m
	return mList
deselect = unselect

textures = {}
currentTexture = None

positions = {}

#
# session save/restore stuff
#

import SimpleSession
def _saveSession(trigger, x, sessionFile):
	def reformatPosition(pos):
		xfDict = {}
		for molId, xf in pos[5].items():
			tr = xf.getTranslation()
			rot = xf.getRotation()
			xfDict[molId] = (tr.data(), rot[0].data() + (rot[1],))
		clipDict = {}
		if len(pos) > 6:
			for m, clipInfo in pos[6].items():
				if m.__destroyed__:
					continue
				key = (m.id, m.subid, m.__class__.__name__)
				useClip, plane, useThick, thickness = clipInfo
				origin, normal = plane.origin, plane.normal
				clipDict[key] = (useClip, origin.x, origin.y,
					origin.z, normal.x, normal.y, normal.z,
					useThick, thickness)
		return pos[:5] + (xfDict, clipDict) + pos[7:]
	saveablePositions = {}
	for name, pos in positions.items():
		saveablePositions[name] = reformatPosition(pos)
	restoring_code = \
"""
def restoreMidasBase():
	formattedPositions = %s
	import Midas
	Midas.restoreMidasBase(formattedPositions)
try:
	restoreMidasBase()
except:
	reportRestoreError('Error restoring Midas base state')

""" % (repr(saveablePositions))
	sessionFile.write(restoring_code)
chimera.triggers.addHandler(SimpleSession.SAVE_SESSION, _saveSession, None)

def restoreMidasBase(formattedPositions):
	cb = lambda fp = formattedPositions: restoreSavedPositions(fp)
	import SimpleSession
	SimpleSession.registerAfterModelsCB(cb)

def restoreSavedPositions(formattedPositions):
	import chimera
	from SimpleSession import modelMap, modelOffset
	def deformatPosition(pos):
		xfDict = {}
		for molId, xfData in pos[5].items():
			mid, subid = molId
			trData, rotData = xfData
			xf = chimera.Xform.translation(*trData)
			xf.rotate(*rotData)
			xfDict[(mid + modelOffset, subid)] = xf
		try:
			from chimera.misc import KludgeWeakWrappyDict
			clipDict = KludgeWeakWrappyDict("Model")
		except ImportError:
			from weakref import WeakKeyDictionary
			clipDict = WeakKeyDictionary()
		for clipID, clipInfo in pos[6].items():
			mid, subid, className = clipID
			models = [m for m in modelMap.get((mid, subid), [])
				  if m.__class__.__name__ == className
				     and not m.__destroyed__]
			if not models:
				continue
			useClip, ox, oy, oz, nx, ny, nz, useThick, thickness = clipInfo
			if useClip:
				origin = chimera.Point(ox, oy, oz)
				normal = chimera.Vector(nx, ny, nz)
				plane = chimera.Plane(origin, normal)
			else:
				plane = chimera.Plane()
			for m in models:
				clipDict[m] = (useClip, plane,
							useThick, thickness)
		return pos[:5] + (xfDict, clipDict) + pos[7:]
	positions = {}
	for name, fpos in formattedPositions.items():
		positions[name] = deformatPosition(fpos)
	import Midas
	if modelOffset == 0:
		posNames = positions.keys()
		Midas.positions.clear()
		if posNames:
			chimera.triggers.activateTrigger(REMOVE_POSITIONS, posNames)
	Midas.positions.update(positions)
	if positions:
		chimera.triggers.activateTrigger(ADD_POSITIONS, positions.keys())

def _closeSession(*args):
	positions.clear()
chimera.triggers.addHandler(chimera.CLOSE_SESSION, _closeSession, None)

def _postRestore(*args):
	# reformat old positions to current format
	def reformatPosition(pos):
		xfDict = {}
		for key, xf in pos[5].items():
			if isinstance(key, tuple):
				xfDict[key] = xf
				continue
			if key.__destroyed__:
				continue
			xfDict[(key.id, key.subid)] = xf
		return pos[:5] + (xfDict,) + pos[6:]
	for name, pos in positions.items():
		positions[name] = reformatPosition(pos)
	import SimpleSession
	if not (SimpleSession.mergedSession and 'session-start' in positions):
		def saveSesPos(*args):
			savepos("session-start")
			from chimera.triggerSet import ONESHOT
			return ONESHOT
		chimera.triggers.addHandler('new frame', saveSesPos, None)
chimera.triggers.addHandler(SimpleSession.END_RESTORE_SESSION,
							_postRestore, None)

def _atomSpecErrorCheck(f, t):
	from chimera.specifier import pickSynonyms
	if f in pickSynonyms:
		atoms = _selectedAtoms(f, ordered=True)
		half, rem = divmod(len(atoms), 2)
		if rem != 0:
			raise MidasError, "Odd number of atoms selected"
		fAtoms = atoms[0:half]
		tAtoms = atoms[half:]
	else:
		if isinstance(f, (list, tuple, set)):
			fAtoms = f
		else:
			fAtoms = _selectedAtoms(f, ordered=True)
		if isinstance(t, (list, tuple, set)):
			tAtoms = t
		else:
			tAtoms = _selectedAtoms(t, ordered=True)
	if len(fAtoms) != len(tAtoms):
		raise MidasError, "Unequal numbers of atoms chosen for evaluation"
	if len(fAtoms) < 1:
		raise TooFewAtomsError("At least one atom must be selected")

	return (fAtoms, tAtoms)

#define element colors (but after graphics initializes...)
def _initElementColors():
	for i, rgb in enumerate([
	[255, 255, 255], [217, 255, 255], [204, 128, 255], [194, 255, 0],
	[255, 181, 181], [144, 144, 144], [48, 80, 248], [255, 13, 13],
	[144, 224, 80], [179, 227, 245], [171, 92, 242], [138, 255, 0],
	[191, 166, 166], [240, 200, 160], [255, 128, 0], [255, 255, 48],
	[31, 240, 31], [128, 209, 227], [143, 64, 212], [61, 255, 0],
	[230, 230, 230], [191, 194, 199], [166, 166, 171], [138, 153, 199],
	[156, 122, 199], [224, 102, 51], [240, 144, 160], [80, 208, 80],
	[200, 128, 51], [125, 128, 176], [194, 143, 143], [102, 143, 143],
	[189, 128, 227], [255, 161, 0], [166, 41, 41], [92, 184, 209],
	[112, 46, 176], [0, 255, 0], [148, 255, 255], [148, 224, 224],
	[115, 194, 201], [84, 181, 181], [59, 158, 158], [36, 143, 143],
	[10, 125, 140], [0, 105, 133], [192, 192, 192], [255, 217, 143],
	[166, 117, 115], [102, 128, 128], [158, 99, 181], [212, 122, 0],
	[148, 0, 148], [66, 158, 176], [87, 23, 143], [0, 201, 0],
	[112, 212, 255], [255, 255, 199], [217, 255, 199], [199, 255, 199],
	[163, 255, 199], [143, 255, 199], [97, 255, 199], [69, 255, 199],
	[48, 255, 199], [31, 255, 199], [0, 255, 156], [0, 230, 117],
	[0, 212, 82], [0, 191, 56], [0, 171, 36], [77, 194, 255],
	[77, 166, 255], [33, 148, 214], [38, 125, 171], [38, 102, 150],
	[23, 84, 135], [208, 208, 224], [255, 209, 35], [184, 184, 208],
	[166, 84, 77], [87, 89, 97], [158, 79, 181], [171, 92, 0],
	[117, 79, 69], [66, 130, 150], [66, 0, 102], [0, 125, 0],
	[112, 171, 250], [0, 186, 255], [0, 161, 255], [0, 143, 255],
	[0, 128, 255], [0, 107, 255], [84, 92, 242], [120, 92, 227],
	[138, 79, 227], [161, 54, 212], [179, 31, 212], [179, 31, 186],
	[179, 13, 166], [189, 13, 135], [199, 0, 102], [204, 0, 89],
	[209, 0, 79], [217, 0, 69], [224, 0, 56], [230, 0, 46],
	[235, 0, 38]]):
		colordef(chimera.Element(i + 1).name, (rgb[0] / 255.0,
						rgb[1] / 255.0, rgb[2] / 255.0))
chimera.registerPostGraphicsFunc(_initElementColors)

def elementColor(element):
	if isinstance(element, chimera.Element):
		sym = element.name
	else:
		sym = element
	c = chimera.Color.lookup(sym)
	if c == None:
		return chimera.Color.lookup("magenta")
	return c

def deduceFileFormat(filename, filters):
	# try to deduce file format from filename
	# by looking for known suffix
	ext = os.path.splitext(filename)[1]
	if ext:
		for format, glob, suffix in filters:
			if isinstance(glob, basestring):
				if glob.endswith(ext):
					return format
			else:
				for g in glob:
					if g.endswith(ext):
						return format
	return None
