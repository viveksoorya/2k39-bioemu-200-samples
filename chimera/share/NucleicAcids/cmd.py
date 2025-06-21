# chimera nucleotides command
#
#	nucleotides ndbcolor [atom-spec]
#	nucleotides sidechain type [keyword options] [atom-spec]
#		* show side chains -- sugar/bases
#		* type is one of atoms, fill/fill, fill/slab, tube/slab, ladder
#		* fill/fill is same as:
#			nuc sidechain atoms atom-spec; fillring thick atom-spec
#		* options vary with sidechain type
#		* fill/fill, fill/slab, tube/slab:
#			* orient (true|false)
#		* fill/slab, tube/slab:
#			* shape (box|tube|ellipsoid)
#			* style slab-style
#			* thickness 0.5
#			* hide (true|false)
#		* tube-slab:
#			* glycosidic (true|false)
#			  (shows separate glycosidic bond)
#		* ladder:
#			* radius 0.45
#			  (radius of ladder rungs and only applies to base-base
#			  H-bonds -- zero means use defaults)
#			* stubs (true|false)
#			* ignore (true|false)
#			  (ignore non-base H-bonds)
#	nucleotides add style-name options
#		* create/modify slab style, all options are required
#		* options are:
#			anchor (sugar|base)
#			(purine|pyrimidine) (lower-left|ll|upper-right|ur) x y
#	nucleotides delete style-name
#		* delete style

# look at movie, volume, hbond commands for ideas

import NucleicAcids as NA
import Midas
Error = Midas.MidasError
from Midas.midas_text import getSpecs, keyword_match, first_arg
import default

BOOL = ('false', 'true')
SIDES = ('atoms', 'fill/fill', 'fill/slab', 'tube/slab', 'ladder')
BOOL_PARAMS = ('orient', 'glycosidic', 'stubs', 'ignore', 'useexisting', 'hide')
FLOAT_PARAMS = ('radius', 'thickness')
SIDE_PARAMS = ('shape', 'style') + BOOL_PARAMS + FLOAT_PARAMS
SHAPES = ('box', 'tube', 'ellipsoid')
STYLE_OPTS = (NA.ANCHOR, NA.PURINE, NA.PYRIMIDINE)
ANCHOR_OPTS = (NA.SUGAR, NA.BASE)

def cvtBool(s):
	try:
		b = keyword_match(s, BOOL)
	except Error:
		raise ValueError("invalid literal for boolean: %s" % s)
	return b

def unnucleotides(cmdName, args):
	_sidechain(' '.join(['atoms', args]))

def nucleotides(cmdName, args):
	cmd, args = first_arg(args)
	if not cmd:
		raise Error('missing arguments to %s command' % cmdName)

	i = keyword_match(cmd, CMDS)
	CMD_INFO[i][1](args)
	return

def _sidechain(args):
	# parse arguments and call sidechain
	side, args = first_arg(args)
	side = SIDES[keyword_match(side, SIDES)]
	params = {}
	while 1:
		name, args = first_arg(args)
		try:
			name = SIDE_PARAMS[keyword_match(name, SIDE_PARAMS)]
		except Error:
			args = ' '.join([name, args])
			break
		arg, args = first_arg(args)
		if name in BOOL_PARAMS:
			try:
				arg = cvtBool(arg)
			except ValueError:
				raise Error("%s argument must be true or false" % arg)
		elif name in FLOAT_PARAMS:
			try:
				arg = float(arg)
			except ValueError:
				raise Error("%s argument must be a number" % arg)
		elif name == 'shape':
			try:
				arg = SHAPES[keyword_match(arg, SHAPES)]
			except Error:
				raise Error("Unknown slab shape: %s" % arg)
		elif name == 'style':
			info = NA.findStyle(arg)
			if not info:
				raise Error("Unknown slab style: %s" % arg)
		params[name] = arg
	params['sel'] = getSpecs(args)
	sidechain(side, **params)

def _add(args):
	# parse args and call addStyle
	style, args = first_arg(args)
	info = {
		#NA.ANCHOR: self.anchor.get(),
		#NA.PURINE: (puLL, puUR),
		#NA.PYRIMIDINE: (pyLL, pyUR),
		#NA.PSEUDO_PYRIMIDINE: (pyLL, pyUR),
	}
	while 1:
		name, args = first_arg(args)
		if not name:
			break
		name = STYLE_OPTS[keyword_match(name, STYLE_OPTS)]
		if name == NA.ANCHOR:
			arg, args = first_arg(args)
			arg = ANCHOR_OPTS[keyword_match(arg, ANCHOR_OPTS)]
			info[NA.ANCHOR] = arg
		else:
			BOUNDS_NAME = (
				'lower left x', 'lower left y',
				'upper right x', 'upper right y'
			)
			bounds = ['', '', '', '']
			bounds[0], args = first_arg(args)
			bounds[1], args = first_arg(args)
			bounds[2], args = first_arg(args)
			bounds[3], args = first_arg(args)
			for i in range(4):
				try:
					bounds[i] = float(bounds[i])
				except ValueError:
					raise Error("%s argument must be a number: %s" % (BOUNDS_NAME[i], bounds[i]))
			info[name] = ((bounds[0], bounds[1]),
						(bounds[2], bounds[3]))
			if name == NA.PYRIMIDINE:
				info[NA.PSEUDO_PYRIMIDINE] = info[NA.PYRIMIDINE]
	if len(info) != 4:
		raise Error("Incomplete style")
	print "adding style", style
	NA.addStyle(style, info)

def _delete(args):
	# parse args and call removeStyle
	name, args = first_arg(args)
	if not name or args:
		raise Error("Can only delete one style")
	try:
		NA.removeStyle(name)
	except KeyError:
		raise Error("Style '%s' is already gone" % name)

def ndbcolor(sel='sel'):
	if isinstance(sel, basestring):
		sel = getSpecs(sel)
	residues = Midas._selectedResidues(sel)
	NA.NDBColors(residues)

def sidechain(side, glycosidic=default.GLYCOSIDIC, orient=default.ORIENT,
		thickness=default.THICKNESS, hide=default.HIDE,
		shape=default.SHAPE, style=default.STYLE, radius=default.RADIUS,
		stubs=default.STUBS, ignore=default.IGNORE,
		useexisting=default.USE_EXISTING, sel='sel'):
	if isinstance(sel, basestring):
		sel = Midas.evalSpec(sel)
		residues = sel.residues()
	elif isinstance(sel, (list, tuple, set)):
		residues = sel
	else:
		residues = sel.residues()
	residues = [r for r in residues
				if r.ribbonResidueClass.isNucleic()]
	molecules = set(r.molecule for r in residues)
	if side == 'atoms':
		for r in residues:
			r.fillDisplay = False
		NA.set_normal(molecules, residues)
	elif side == 'fill/fill':
		for r in residues:
			r.fillDisplay = True
		if orient:
			NA.set_orient(molecules, residues)
		else:
			NA.set_normal(molecules, residues)
	elif side in ('fill/slab', 'tube/slab'):
		if side.startswith('fill'):
			for r in residues:
				r.fillDisplay = True
			showGly = True
		else:
			showGly = glycosidic
		if showGly:
			info = NA.findStyle(style)
			showGly = info[NA.ANCHOR] != NA.SUGAR
		NA.set_slab(side, molecules, residues, style=style,
			thickness=thickness, orient=orient,
			shape=shape, showGly=showGly, hide=hide)
	elif side == 'ladder':
		from FindHBond import recDistSlop, recAngleSlop
		NA.set_ladder(molecules, residues,
			rungRadius=radius,
			showStubs=stubs,
			skipNonBaseHBonds=ignore,
			useExisting=useexisting,
			distSlop=recDistSlop, angleSlop=recAngleSlop)
CMD_INFO = (
	('ndbcolor', ndbcolor),
	('sidechain', _sidechain),
	('add', _add),
	('delete', _delete),
)
CMDS = [c[0] for c in CMD_INFO]
