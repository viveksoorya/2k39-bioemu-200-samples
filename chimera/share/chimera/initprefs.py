# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: initprefs.py 42098 2019-11-13 18:58:17Z goddard $

import preferences, tkoptions, os
from tkoptions import MoleculeColorOption, LineWidthOption, \
	RibbonXSectionOption, RibbonScalingOption, RibbonDisplayOption, \
	AtomDisplayOption, AtomDrawModeOption, BondDrawModeOption, \
	PseudoBondGroupColorOption, StickScaleOption, BallScaleOption, \
	AutoChainOption, BooleanOption, RibbonHideBackboneOption, EnumOption

# preference controls for PDB handling
PREF_PDB = "PDB"
PREF_PDB_FETCH = "Fetch from web\nas necessary"
PREF_PDB_DIRS = "Personal PDB\ndirectories"

# register prefs one-by-one in category
_pdbPreferences = {
	PREF_PDB_FETCH:
		(tkoptions.BooleanOption, 1, None),
	PREF_PDB_DIRS:
		(tkoptions.OrderedDirListOption, [], None),
}

_pdbPreferencesOrder = [
	PREF_PDB_FETCH, PREF_PDB_DIRS
]
preferences.register(PREF_PDB, _pdbPreferences)

preferences.setOrder(PREF_PDB, _pdbPreferencesOrder)


# preferences for newly-opened models
MOLECULE_DEFAULT = "New Molecules"
MOL_AUTOCOLOR = "use new color for each model"
MOL_SMART = "smart initial display"
MOL_COLOR = "otherwise, use color"
MOL_LINEWIDTH = LineWidthOption.name
MOL_RIBBONDISP = RibbonDisplayOption.name
MOL_RIBBONMODE = RibbonXSectionOption.name
MOL_RIBBONSCALE = RibbonScalingOption.name
MOL_HIDE_BACKBONE = RibbonHideBackboneOption.name
MOL_ATOMDRAW = AtomDrawModeOption.name
MOL_ATOMDISPLAY = "show atoms"
MOL_BONDDRAW = BondDrawModeOption.name
MOL_STICKSCALE = StickScaleOption.name
MOL_BALLSCALE = BallScaleOption.name
MOL_PERATOM = "per-atom coloring"
MOL_AUTOCHAIN = AutoChainOption.name
MOL_COMPLEX_LW = "metal complex line width"
MOL_COMPLEX_COLOR = "metal complex color"
MOL_COMPLEX_REPR = "metal complex representation"
MOL_IONS_REPR = "monatomic ion style"
MOL_MOL2_NAME = "Mol2 model naming"

class MCLineWidthOption(LineWidthOption):
	default = 2.0

class MCColorOption(PseudoBondGroupColorOption):
	balloon = "color of metal-complex bonds"
	default = "medium purple"

class MCReprOption(EnumOption):
	balloon = "How to depict coordination bonds"
	values = ["dashed lines", "solid lines", "springs"]
	default = "dashed lines"

class IonsReprOption(AtomDrawModeOption):
	import chimera
	default = chimera.Atom.Sphere

class PerAtomOption(EnumOption):
	balloon = "coloring to apply to atoms"
	values = ["none", "by element", "by heteroatom"]

class Mol2NameOption(EnumOption):
	FILE_NAME = "file name"
	MOL_NAME = "Mol2 molecule name"
	MOL_COMMENT = "Mol2 molecule comment"
	values = [FILE_NAME, MOL_NAME, MOL_COMMENT]
	default = MOL_NAME
	balloon = """source for the model name of Mol2 molecules
"%s" is the first line after @<TRIPOS>MOLECULE
"%s" is the sixth line after @<TRIPOS>MOLECULE
If such lines are ininformative (e.g. non-alphanumeric)
then the file name will be used instead""" % (MOL_NAME, MOL_COMMENT)

def smartDispCB(opt):
	if not hasattr(opt, 'get'):  # event instead
		opt = preferences.getOption(MOLECULE_DEFAULT, MOL_SMART)
	dependentOpts = [MOL_RIBBONDISP, MOL_RIBBONMODE, MOL_RIBBONSCALE,
		MOL_HIDE_BACKBONE, MOL_ATOMDISPLAY, MOL_PERATOM, MOL_ATOMDRAW,
		MOL_BONDDRAW, MOL_AUTOCHAIN]
	if opt.get():
		for do in dependentOpts:
			ui = preferences.getOption(MOLECULE_DEFAULT, do).ui()
			if ui:
				ui.disable()
	else:
		for do in dependentOpts:
			ui = preferences.getOption(MOLECULE_DEFAULT, do).ui()
			if ui:
				ui.enable()

moleculePreferences = {
	MOL_AUTOCOLOR:
		(tkoptions.BooleanOption, True, None),
	MOL_COLOR:
		(MoleculeColorOption,
				MoleculeColorOption.default, None),
	MOL_SMART:
		(tkoptions.BooleanOption, True, smartDispCB, {'balloon':
"""If true, newly opened molecules will be depicted in a fashion
similar to the 'Interactive 1' preset except that no rainbow
coloring of chains will occur.  This will override other
options in this section except for those dealing with initial
model color, metal complexes, Mol2 model naming, line width,
or ball/stick scale."""
		}),
	MOL_LINEWIDTH:
		(LineWidthOption, LineWidthOption.default, None),
	MOL_RIBBONDISP:
		(RibbonDisplayOption, RibbonDisplayOption.default, None),
	MOL_RIBBONMODE:
		(RibbonXSectionOption, RibbonXSectionOption.default, None),
	MOL_RIBBONSCALE:
		(RibbonScalingOption, RibbonScalingOption.default, None),
	MOL_HIDE_BACKBONE:
		(RibbonHideBackboneOption,
				RibbonHideBackboneOption.default, None),
	MOL_ATOMDISPLAY:
		(AtomDisplayOption, AtomDisplayOption.default, None),
	MOL_ATOMDRAW:
		(AtomDrawModeOption, AtomDrawModeOption.default, None),
	MOL_BONDDRAW:
		(BondDrawModeOption, BondDrawModeOption.default, None),
	MOL_IONS_REPR:
		(IonsReprOption, IonsReprOption.default, None),
	MOL_STICKSCALE:
		(StickScaleOption, StickScaleOption.default, None),
	MOL_BALLSCALE:
		(BallScaleOption, BallScaleOption.default, None),
	MOL_PERATOM:
		(PerAtomOption, "none", None),
	MOL_AUTOCHAIN:
		(AutoChainOption, AutoChainOption.default, None),
	MOL_COMPLEX_LW:
		(MCLineWidthOption, MCLineWidthOption.default, None),
	MOL_COMPLEX_COLOR:
		(MCColorOption, MCColorOption.default, None),
	MOL_COMPLEX_REPR:
		(MCReprOption, MCReprOption.default, None),
	MOL_MOL2_NAME:
		(Mol2NameOption, Mol2NameOption.default, None)
}
moleculePreferencesOrder = [
	MOL_SMART, MOL_RIBBONDISP, MOL_RIBBONMODE, MOL_RIBBONSCALE,
	MOL_HIDE_BACKBONE, MOL_ATOMDISPLAY, MOL_PERATOM, MOL_ATOMDRAW,
	MOL_BONDDRAW, MOL_AUTOCHAIN,
	MOL_AUTOCOLOR, MOL_COLOR, MOL_STICKSCALE, MOL_BALLSCALE, MOL_LINEWIDTH,
	MOL_IONS_REPR,
	MOL_COMPLEX_REPR, MOL_COMPLEX_COLOR, MOL_COMPLEX_LW, MOL_MOL2_NAME
]
preferences.register(MOLECULE_DEFAULT, moleculePreferences, onDisplay=smartDispCB)
preferences.setOrder(MOLECULE_DEFAULT, moleculePreferencesOrder)

KSDSSP = "ksdssp parameters"
KSDSSP_ENERGY = "h-bond energy cutoff"
KSDSSP_HELIX_LENGTH = "minimum helix length"
KSDSSP_STRAND_LENGTH = "minimum strand length"
ksdsspOptions = {
	KSDSSP_ENERGY: -0.5,
	KSDSSP_HELIX_LENGTH: 3,
	KSDSSP_STRAND_LENGTH: 3
}
ksdsspPrefs = preferences.addCategory(KSDSSP, preferences.HiddenCategory,
							optDict=ksdsspOptions)

GRAPHICS_CHECK = "graphics check"
GRAPHICS_GDI_CHECKED = "gdi checked"
graphicsOptions = {
	GRAPHICS_GDI_CHECKED: False,
}
graphicsPrefs = preferences.addCategory(GRAPHICS_CHECK, preferences.HiddenCategory,
					optDict=graphicsOptions)

SURFACE_DEFAULT = "New Surfaces"
from tkoptions import SurfaceReprOption, SurfaceColorSourceOption, SurfaceProbeRadiusOption, SurfaceDensityOption, SurfaceLineWidthOption, SurfaceDotSizeOption, SurfaceDisjointOption
SURF_REPR = SurfaceReprOption.name
SURF_PROBE_RADIUS = SurfaceProbeRadiusOption.name
SURF_DENSITY = SurfaceDensityOption.name
SURF_LINEWIDTH = SurfaceLineWidthOption.name
SURF_DOTSIZE = SurfaceDotSizeOption.name
SURF_DISJOINT = SurfaceDisjointOption.name

surfacePreferences = {
	SURF_REPR:
		(SurfaceReprOption, SurfaceReprOption.default, None),
	SURF_PROBE_RADIUS:
		(SurfaceProbeRadiusOption, SurfaceProbeRadiusOption.default, None),
	SURF_DENSITY:
		(SurfaceDensityOption, SurfaceDensityOption.default, None),
	SURF_LINEWIDTH:
		(SurfaceLineWidthOption, SurfaceLineWidthOption.default, None),
	SURF_DOTSIZE:
		(SurfaceDotSizeOption, SurfaceDotSizeOption.default, None),
	SURF_DISJOINT:
		(SurfaceDisjointOption, SurfaceDisjointOption.default, None),
}
surfacePreferencesOrder = [
	SURF_REPR,
	SURF_PROBE_RADIUS,
	SURF_DENSITY,
	SURF_LINEWIDTH,
	SURF_DOTSIZE,
	SURF_DISJOINT,
]
preferences.register(SURFACE_DEFAULT, surfacePreferences)
preferences.setOrder(SURFACE_DEFAULT, surfacePreferencesOrder)

PREF_LABEL = "Labels"
LABEL_FONT = "Label font"
LABELS_ON_TOP = "Labels on top"
ATOMSPEC_BALLOON = "Show atomspec balloon"
ATOMSPEC_CONTENTS = "Atomspec display style"
ATOMSPEC_SERIAL = "serial number"
ATOMSPEC_SIMPLE = "simple"
ATOMSPEC_MIDAS = "Midas atomspec"

import chimera
def setLabelFont(option=None):
	if chimera.nogui:
		return
	def postGfx(option=option):
		if option is None:
			option = preferences.getOption(PREF_LABEL, LABEL_FONT)
		name, style, size = option.get()
		if style == 'Bold':
			style = chimera.OGLFont.bold
		elif style == 'Italic':
			style = chimera.OGLFont.italic
		elif style == 'Bold Italic':
			style = chimera.OGLFont.bold | chimera.OGLFont.italic
		else:
			style = chimera.OGLFont.normal
		font = chimera.OGLFont(name, size, style)
		if font.valid():
			global default_label_font
			default_label_font = font
			chimera.OGLFont.setDefaultFont(font)
			chimera.viewer.invalidateCache()
	chimera.registerPostGraphicsFunc(postGfx)

def setLabelsOnTop(option=None):
	def postGfx(option=option):
		if option is None:
			option = preferences.getOption(PREF_LABEL, LABELS_ON_TOP)
		ontop = option.get()
		chimera.viewer.labelsOnTop = ontop
	chimera.registerPostGraphicsFunc(postGfx)

def _setAtomspecBalloon(o):
	from tkgui import app
	if app:
		app._setAtomspecBalloon(o)

labelPreferences = {
	LABEL_FONT:
		(tkoptions.FontOption, (tkoptions.FontOption.names[0],
			tkoptions.FontOption.styles[0], 16), setLabelFont),
	LABELS_ON_TOP: (
		tkoptions.BooleanOption, True, setLabelsOnTop),
	ATOMSPEC_BALLOON:
		(tkoptions.BooleanOption, True, _setAtomspecBalloon),
	ATOMSPEC_CONTENTS:
		(tkoptions.NamingStyleOption, ATOMSPEC_SIMPLE, None),
}
labelPreferencesOrder = [
	LABEL_FONT,
	LABELS_ON_TOP,
	ATOMSPEC_BALLOON,
	ATOMSPEC_CONTENTS,
]
GENERAL = "General"
from bgprefs import BACKGROUND
preferences.register(PREF_LABEL, labelPreferences, inherit=[
	(LABEL_FONT, BACKGROUND, LABEL_FONT, None),
	(LABELS_ON_TOP, BACKGROUND, LABELS_ON_TOP, None),
	(ATOMSPEC_BALLOON, GENERAL, ATOMSPEC_BALLOON, None),
	(ATOMSPEC_CONTENTS, GENERAL, ATOMSPEC_CONTENTS, None)])
preferences.setOrder(PREF_LABEL, labelPreferencesOrder)

setLabelFont()
setLabelsOnTop()

PREF_SELECTION = "Selection"
HMETHOD = "Selection highlight method"
HCOLOR = "Selection highlight color"
def postGfx():
	if isinstance(chimera.viewer, chimera.LensViewer):
		class HighlightOption(tkoptions.SymbolicEnumOption):
			"""Specialization of SymbolicEnumOption Class for highlights"""
			labels = ("outline", "fill")
			values = [chimera.LensViewer.Outline, chimera.LensViewer.Fill]

		def _highlightMethodCB(option):
			method = option.get()
			chimera.viewer.highlight = method

		def _highlightColorCB(option):
			rgba = option.get()
			if not rgba:
				color = None
			else:
				color = chimera.MaterialColor(*rgba)
			chimera.viewer.highlightColor = color

		selectionPreferences = {
			HMETHOD: (
				HighlightOption, chimera.viewer.highlight,
				_highlightMethodCB
			),
			HCOLOR: (
				tkoptions.RGBAOption, chimera.viewer.highlightColor.rgba(),
				_highlightColorCB, { "noneOkay": False }
			),
		}
		selectionPreferencesOrder = [ HMETHOD, HCOLOR ]
		preferences.register(PREF_SELECTION, selectionPreferences, inherit=[
			(HMETHOD, BACKGROUND, HMETHOD, None),
			(HCOLOR, BACKGROUND, HCOLOR, None)])
		preferences.setOrder(PREF_SELECTION, selectionPreferencesOrder)
chimera.registerPostGraphicsFunc(postGfx)

def _reloadPresets(opt):
	import preset
	preset.get().reloadCustomPresets()
PREF_PRESET = "Presets"
PREF_PRESET_DIRS = "Personal preset\ndirectories"
_presetPreferences = {
	PREF_PRESET_DIRS:
		(tkoptions.OrderedDirListOption, [], _reloadPresets ),
}
_presetPreferencesOrder = [
	PREF_PRESET_DIRS,
]
preferences.register(PREF_PRESET, _presetPreferences)
preferences.setOrder(PREF_PRESET, _presetPreferencesOrder)
