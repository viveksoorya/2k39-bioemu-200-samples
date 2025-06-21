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

# below also in #6505
#TODO: nucleotides is a _lot_ of work
#TODO: viewdock info?

import replyobj
pipes_string = " Pipes and Planks"
surface_export_warned = False
label_2d_rgba_warned = False
label_2d_size_warned = False
label_2d_style_warned = False
label_2d_font_name_warned = False
label_2d_multiline_warned = False

def export_cx(filename):
	from OpenSave import osOpen
	f = osOpen(filename, 'w')
	write_utility_functions(f)

	# 3D models
	write_prolog(f)
	by_id = {}
	metal_pbg_lookup = {}
	msms_models = []
	from chimera import openModels, viewer
	for m in openModels.list():
		cname = m.__class__.__name__
		if cname == 'Molecule':
			write_molecule(f, m)
			pbg = m.metalComplexGroup(create=False)
			if pbg:
				metal_pbg_lookup[pbg] = m
			by_id.setdefault(m.id, []).append(m)
		elif cname == 'MSMSModel':
			msms_models.append(m)
			by_id.setdefault(m.molecule, []).append(m)
		elif cname in ('Volume', 'Volume_Model'):
                        pass  # Handled below by write_volumes()
		else:
			if not m.name.endswith(pipes_string):
				replyobj.warning("ChimeraX export does not yet support %s models" % m.__class__.__name__)
			continue

        write_volumes(f, filename)

	from StructMeasure import Axes, Centroids, Planes
	from StructMeasure.Geometry import geomManager as geom_manager
	axes = [i for i in geom_manager.items if isinstance(i, Axes.Axis)]
	if axes:
		write_axes(f, axes)
	centroids = [i for i in geom_manager.items if isinstance(i, Centroids.Centroid)]
	if centroids:
		write_centroids(f, centroids)
	planes = [i for i in geom_manager.items if isinstance(i, Planes.Plane)]
	if planes:
		write_planes(f, planes)
	global_groups = write_pseudobonds(f, metal_pbg_lookup)
	for msms_model in msms_models:
		write_msms_model(f, msms_model)
	write_selection(f)

	# 2D models
	from Ilabel import LabelsModel
	labels_2d_model = LabelsModel(create=False)
	if labels_2d_model:
		write_2d_labels(f, labels_2d_model)
	from Ilabel.ColorKey import getKeyModel
	key = getKeyModel(create=False)
	if key:
		write_color_key(f, key)
	from Ilabel.Arrows import ArrowsModel
	arrows_model = ArrowsModel(create=False)
	if arrows_model:
		write_arrows(f, arrows_model)

	# scene parameters
	cam = viewer.camera
	bg = viewer.background if viewer.backgroundMethod == viewer.Solid else None
	near, far = cam.nearFar
	has_bbox, bbox = openModels.bbox()
	if has_bbox:
		center = bbox.center()
		center_z = center.z
		center.z = near
		if bbox.inside(center):
			near = center_z - near
		else:
			near = None
		center.z = far
		if bbox.inside(center):
			far = center_z - far
		else:
			far = None
	else:
		near = far = None
	write_epilog(f, by_id, global_groups, cam.eyePos(0), cam.fieldOfView, near, far, viewer.windowSize, bg)

	# alignments
	from chimera.extension import manager
	from MultAlignViewer.MAViewer import MAViewer
	for mav in [inst for inst in manager.instances if isinstance(inst, MAViewer)]:
		write_alignment(f, mav)
	f.close()

def deSortString(data):
	if isinstance(data, tuple):
		return tuple([deSortString(x) for x in data])
	elif isinstance(data, list):
		return [deSortString(x) for x in data]
	elif isinstance(data, dict):
		return { deSortString(k): deSortString(v) for k, v in data.items() }
	from CGLutil.SortString import SortString
	if isinstance(data, SortString):
		return unicode(data)
	return data

def pickled(data):
	# convert SortStrings to simple strings so that the SortString class isn't pickled
	data = deSortString(data)
	from SimpleSession.save import pickled as pickled2
	#for i in range(len(data)):
	#	pickled2(data[i])
	return "p" + pickled2(data)[2:-1] + ", encoding='latin1')"  # change the initial 'cPickle' to 'pickle'

def color_val(color):
	return None if color is None else color.rgba()

def simple_offset(off):
	return off.data() if hasattr(off, 'data') else off

def write_utility_functions(f):
	print>>f, color_converter_definition
	print>>f, restore_model_definition
	print>>f, make_structure_definition
	print>>f, make_molecular_surface_definition
	print>>f, restore_coordset_definition
	print>>f, restore_res_definition
	print>>f, restore_atom_definition
	print>>f, restore_bond_definition
	print>>f, make_pseudobonds_definition
	print>>f, restore_selection_definition
	print>>f, restore_camera_definition
	print>>f, restore_window_size_definition
	print>>f, make_alignment_definition
	print>>f, restore_seq_definition
	print>>f, restore_2d_labels_definition
	print>>f, restore_color_key_definition
	print>>f, restore_arrows_definition
	print>>f, restore_axes_definition
	print>>f, restore_centroids_definition
	print>>f, restore_planes_definition

def write_prolog(f):
	print>>f, "from chimerax.core.commands import run"
	print>>f, "run(session, 'close session')"
	print>>f, "import pickle, base64"
	print>>f, "global_atom_map = {}"
	print>>f, "structure_map = {}"
	print>>f, "residue_map = {}"
	print>>f, "label_data = []"
	print>>f, "font_mapping = {'Serif': 'Times', 'Sans Serif': 'Helvetica', 'Fixed': 'Courier'}"

def write_pseudobonds(f, metal_pbg_lookup):
	from chimera import PseudoBondMgr
	mgr = PseudoBondMgr.mgr()
	global_groups = []
	from StructMeasure.DistMonitor import monitoredGroups, precision, _pref
	for grp in mgr.pseudoBondGroups:
		if grp.category.startswith('internal-chain'):
			continue
		if not grp.pseudoBonds:
			continue
		if grp in metal_pbg_lookup:
			parent, category = "m%d" % id(metal_pbg_lookup[grp]), "metal coordination bonds"
		else:
			parent, category = None, grp.category
			if category != "missing segments":
				global_groups.append(grp)
		if grp in monitoredGroups:
			monitored = (precision(), _pref["show units"])
		else:
			monitored = False
		data = [parent, (category, color_val(grp.color), grp.lineType == 1), monitored, [bond_data(pb)
			for pb in grp.pseudoBonds]]
		print>>f, "pbg%d = make_pseudobonds(%s)" % (id(grp), pickled(data))
	return global_groups

def write_selection(f):
	from chimera import selection
	sel_atoms = ["a%d" % id(a) for a in selection.currentAtoms()]
	sel_bonds = [("a%d" % id(b.atoms[0]), "a%d" % id(b.atoms[1])) for b in selection.currentBonds()]
	sel_pbs = [("pbg%d" % id(pb.pseudoBondGroup), "a%d" % id(pb.atoms[0]), "a%d" % id(pb.atoms[1]))
		for pb in selection.currentPseudobonds()]
	print>>f, "restore_selection(*%s)" % pickled((sel_atoms, sel_bonds, sel_pbs))

def write_2d_labels(f, model):
	data = []
	global label_2d_multiline_warned
	from chimera import OGLFont
	for label in model.labels:
		if len(label.lines) > 1 and not label_2d_multiline_warned:
			replyobj.warning("ChimeraX export does not support multi-line 2D labels; creating multiple"
				" single-line labels instead")
			label_2d_multiline_warned = True
		for i, line in enumerate(label.lines):
			if not line:
				continue
			rgba, size, style, font_name, text = line_data(line)
			if i > 0:
				from chimera import viewer
				w, h = viewer.windowSize
				pos = (label.pos[0],  label.pos[1] - (i * size) / float(h))
			else:
				pos = label.pos
			data.append([pos, label.background, label.margin, label.outline, label.opacity, rgba, size,
				style & OGLFont.bold, style & OGLFont.italic, font_name, text])
	print>>f, "restore_2d_labels(%s)" % pickled(data)

def write_arrows(f, model):
	data = []
	for arrow in model.arrows:
		data.append((arrow.ident, arrow.start, arrow.end, arrow.head, arrow.shown,
			arrow.weight, arrow.color, arrow.opacity))
	print>>f, "restore_arrows(%s)" % pickled(data)

def write_color_key(f, key):
	from chimera import OGLFont
	keywords = {}
	pos = key.getKeyPosition()
	if pos is None:
		keywords['display'] = False
	else:
		ll, ur = pos
		keywords['pos'] = (min([ll[0], ur[0]]), min([ll[1], ur[1]]))
		keywords['size'] = (abs(ur[0] - ll[0]), abs(ll[1] - ur[1]))
	keywords['font_size'] = key.getFontSize()
	keywords['bold'] = bool(key.getFontStyle() & OGLFont.bold)
	keywords['italic'] = bool(key.getFontStyle() & OGLFont.italic)
	keywords['color_treatment'] = key.getColorTreatment()
	keywords['justification'] = key.getJustification()
	keywords['label_side'] = key.getLabelSide()
	keywords['numeric_label_spacing'] = key.getNumLabelSpacing()
	keywords['label_rgba'] = key.getLabelColor()
	# ChimeraX internally adds 5 to the offset
	keywords['label_offset'] = key.getLabelOffset() - 5
	keywords['font'] = key.getFontTypeface()
	keywords['border'] = key.getBorderColor() != None
	if keywords['border']:
		keywords['border_rgba'] = key.getBorderColor()
	keywords['border_width'] = key.getBorderWidth()
	keywords['ticks'] = key.getTickMarks()
	keywords['tick_length'] = key.getTickLength()
	keywords['tick_thickness'] = key.getTickThickness()
	keywords['rgbas_and_labels'] = key.getRgbasAndLabels()
	print>>f, "restore_color_key(%s)" % pickled(keywords)

def line_data(line):
	global label_2d_rgba_warned, label_2d_size_warned, label_2d_style_warned, label_2d_font_name_warned

	rgbas = set([c.rgba for c in line])
	if len(rgbas) > 1 and not label_2d_rgba_warned:
		replyobj.warning("ChimeraX export does not support mixed colors within a single 2D label line")
		label_2d_rgba_warned = True
	rgba = rgbas.pop()

	sizes = set([c.size for c in line])
	if len(sizes) > 1 and not label_2d_size_warned:
		replyobj.warning("ChimeraX export does not support mixed font sizes within a single 2D label line")
		label_2d_size_warned = True
	size = sizes.pop()

	styles = set([c.style for c in line])
	if len(styles) > 1 and not label_2d_style_warned:
		replyobj.warning("ChimeraX export does not support mixed font styles within a single 2D label line")
		label_2d_style_warned = True
	style = styles.pop()

	font_names = set([c.fontName for c in line])
	if len(font_names) > 1 and not label_2d_font_name_warned:
		replyobj.warning("ChimeraX export does not support mixed fonts within a single 2D label line")
		label_2d_font_name_warned = True
	font_name = font_names.pop()

	return (rgba, size, style, font_name, "".join([unicode(c) for c in line]))

def write_epilog(f, by_id, global_groups, eye_pos, field_of_view, near_clip, far_clip, window_size,
		bg_color):
	for id_info, models in by_id.items():
		model_list = ", ".join(["m%d" % id(m) for m in models])
		if isinstance(id_info, int):
			print>>f, "session.models.add([%s], minimum_id=%d, _from_session=True)" % (
				", ".join(["m%d" % id(m) for m in models]), id_info+1)
		else:
			print>>f, "m%d.add([%s])" % (id(id_info), model_list)
		for model in models:
			if model.__class__.__name__ == 'Molecule':
				print>>f, """
if m%d.num_coordsets > 1:
	from chimerax.core.commands import run
	run(session, "coordset slider %%s" %% m%d.atomspec, log=False)
""" % (id(model), id(model))
	print>>f, "session.models.add([%s], _from_session=True)" % ", ".join(
		["pbg%d" % id(pbg) for pbg in global_groups])
	print>>f, "restore_camera(%s, %s, %s, %s)" % (eye_pos, field_of_view, near_clip, far_clip)
	print>>f, "restore_window_size(%d, %d)" % window_size
	print>>f, """
from chimerax.label.label3d import label as label3d
from chimerax.core.objects import Objects
from chimerax.atomic import Atoms
for obj, obj_type, label, color, offset in label_data:
	if obj_type == "atoms":
		objs = Objects(atoms=Atoms([obj]))
	else:
		objs = Objects(atoms=obj.atoms)
	label3d(session, objects=objs, object_type=obj_type, text=label, color=color, offset=offset)
"""
	print>>f, "session.main_view.background_color = (%g, %g, %g, %g)" % (
		(0.0, 0.0, 0.0, 1.0) if bg_color is None else bg_color.rgba())

def write_molecule(f, m):
	tube = False
	from chimera import openModels
	for other_m in openModels.list():
		if other_m.id == m.id and other_m.name.startswith(m.name) and other_m.name.endswith(pipes_string):
			tube = True
			break
	coord_sets = m.coordSets.values()
	coord_sets.sort(lambda cs1, cs2: cmp(cs1.id, cs2.id))
	data = [model_data(m), m.autochain, m.ballScale, color_val(m.color), m.lineType, m.lineWidth,
		m.lowerCaseChains, m.mol2comments, m.mol2data, m.pdbHeaders, m.pdbVersion, m.pointSize,
		m.ribbonHidesMainchain, color_val(m.ribbonInsideColor), m.silhouette, m.stickScale,
		color_val(m.surfaceColor or m.color), m.surfaceOpacity, tube, m.vdwDensity, m.wireStipple,
		[coordset_data(cs) for cs in coord_sets], [res_data(r) for r in m.residues],
		[bond_data(b) for b in m.bonds]]
	print>>f, "m%d = structure_map['m%d'] = make_structure(%s)" % (id(m), id(m), pickled(data))

def write_msms_model(f, m):
	color_mode = m.colorMode
	global surface_export_warned
	if color_mode == 2 and not surface_export_warned:
		replyobj.warning("ChimeraX export does not support per-vertex surface coloring")
		surface_export_warned = True
	data = [model_data(m), m.probeRadius, m.density, color_val(m.color), color_mode,
		["a%d" % id(a) for a in m.atomMap]]
	print>>f, "m%d = make_molecular_surface(%s)" % (id(m), pickled(data))

def write_axes(f, axes):
	data = []
	from chimera import openModels
	id_lookup = {}
	for m in openModels.list():
		if m.__class__.__name__ == "Molecule":
			id_lookup[(m.id, m.subid)] = m
	for axis in axes:
		associated_structure = id_lookup.get((axis.model.id, axis.model.subid), None)
		if associated_structure:
			associated_structure = "m%d" % id(associated_structure)
		data.append((model_data(axis.model), associated_structure, axis.number, axis.surfacePiece.color,
			axis.radius, axis.extents, axis.center.data(), axis.direction.data()))
	print>>f, "restore_axes(%s)" % pickled(data)

def write_centroids(f, centroids):
	data = []
	from chimera import openModels
	id_lookup = {}
	for m in openModels.list():
		if m.__class__.__name__ == "Molecule":
			id_lookup[(m.id, m.subid)] = m
	for centroid in centroids:
		associated_structure = id_lookup.get((centroid.model.id, centroid.model.subid), None)
		if associated_structure:
			associated_structure = "m%d" % id(associated_structure)
		data.append((model_data(centroid.model), associated_structure, centroid.number,
			centroid.surfacePiece.color, centroid.radius, centroid.center.data()))
	print>>f, "restore_centroids(%s)" % pickled(data)

def write_planes(f, planes):
	data = []
	from chimera import openModels
	id_lookup = {}
	for m in openModels.list():
		if m.__class__.__name__ == "Molecule":
			id_lookup[(m.id, m.subid)] = m
	for plane in planes:
		associated_structure = id_lookup.get((plane.model.id, plane.model.subid), None)
		if associated_structure:
			associated_structure = "m%d" % id(associated_structure)
		data.append((model_data(plane.model), associated_structure, plane.number, plane.surfacePiece.color,
			plane.radius, plane.thickness, plane.plane.origin.data(), plane.plane.normal.data()))
	print>>f, "restore_planes(%s)" % pickled(data)

def write_volumes(f, filename):
        from VolumeViewer.volume import volume_manager, Volume
        if len(volume_manager.data_regions) == 0:
                return

        # This code is copied from VolumeViewer.session.save_volume_data_state()
        from VolumeViewer.session import Volume_Manager_State
        s = Volume_Manager_State()
        s.state_from_manager(volume_manager)

        # Add in the model state (name, position, ...)
        volumes = {}
        from chimera import openModels
        for v in openModels.list(modelTypes=[Volume]):
                volumes[v.session_volume_id] = v 
        for data_state, volume_states in s.data_and_regions_state:
                if data_state.xyz_step is None:
                        del data_state.xyz_step
                if data_state.xyz_origin is None:
                        del data_state.xyz_origin
                for vs in volume_states:
                        vs.state_attributes += ('model_state','place')
                        vid = vs.session_volume_id
                        v = volumes[vid]
                        ms = model_data(v)
                        if v.representation == 'solid':
                                sm = v.solid_model()
                                if sm and sm.display:
                                        ms[1] = True
                        vs.model_state = ms
                        vs.place = ((1,0,0,0),(0,1,0,0),(0,0,1,0))

        from os.path import dirname
        directory = dirname(filename)
        if directory:
                s.use_relative_paths(directory)

        from SessionUtil import objecttree
        t = objecttree.instance_tree_to_basic_tree(s)

        print>>f, make_volumes_definition
        print>>f, "volumes_state = %s" % t
	print>>f, "make_volumes(volumes_state)"

make_volumes_definition = """
def make_volumes(volumes_state):
  from chimerax.map import session as vses
  file_paths = vses.ReplacementFilePaths(session.ui)
  # From chimerax.map.session.create_maps_from_state()
  vlist = []
  gdcache = {}        # (path, grid_id) -> GridData object
  for ds, vslist in volumes_state['data_and_regions_state']:
    data = vses.grid_data_from_state(ds, gdcache, session, file_paths)
    if data:        # Can be None if user does not replace missing file.
      for vs in vslist:
        v = vses.create_map_from_state(vs, data, session)
        for lev, color in zip(vs['surface_levels'], vs['surface_colors']):
          surf = v.add_surface(lev, rgba = color)
          if vs['representation'] == 'mesh':
            surf.show_mesh = True
          surf.display = (vs['representation'] in ('surface', 'mesh'))
        v.matrix_value_statistics(read_matrix = True) # Fixes histogram display
        restore_model_data(v, vs['model_state'])
        vlist.append(v)
  session.models.add(vlist)
  from chimerax.map.volume_viewer import show_volume_dialog
  d = show_volume_dialog(session)
  for v in vlist:
    d.display_volume_info(v)
"""

def model_data(m):
	xf = m.openState.xform
	axis, angle = xf.getRotation()
	trans = xf.getTranslation()
	return [m.name, m.display, [axis[i] for i in range(3)], angle, [trans[i] for i in range(3)],
		m.useClipPlane, m.useClipThickness, plane_data(m.clipPlane), m.clipThickness]

def plane_data(p):
	return (p.origin.data(), p.normal.data())

def coordset_data(cs):
	return [cs.id, cs.xyzArray()]

def res_data(r):
	try:
		label_coord = r.labelCoord().data()
	except:
		# throws exception if nothing displayed
		label_coord = (0.0,0.0,0.0)
	return ["r%d" % id(r), r.currentLabelOffset().data(), color_val(r.fillColor), r.fillDisplay,
		r.fillMode, r.id.chainId, r.id.insertionCode, r.id.position, r.isHelix, r.isHet, r.isStrand,
		r.label, color_val(r.labelColor or r.ribbonColor or r.molecule.color),
		label_coord, simple_offset(r.labelOffset), color_val(r.ribbonColor or r.molecule.color),
		r.ribbonDisplay, r.ribbonDrawMode, r.ssId, r.type, [atom_data(a) for a in r.atoms]]

def atom_data(a):
	return ["a%d" % id(a), a.altLoc, a.anisoU, a.bfactor if a.haveBfactor else None, a.coord().data(),
		a.coordIndex, a.currentLabelOffset().data(), a.defaultRadius, a.display, a.drawMode,
		a.element.number, a.hide, a.idatmIsExplicit, a.idatmType, a.label,
		color_val(a.labelColor or a.color or a.molecule.color), a.labelCoord().data(),
		simple_offset(a.labelOffset), a.name[:4], a.occupancy if a.haveOccupancy else None, a.radius,
		a.serialNumber, color_val(a.shownColor()), a.surfaceCategory, color_val(a.surfaceColor or
		a.molecule.color), a.surfaceDisplay, a.surfaceOpacity, a.vdw, color_val(a.vdwColor)]

def bond_data(b):
	"""Also used for pseudobonds"""
	return [["a%d" % id(a) for a in b.atoms], [color_val(b.color), b.currentLabelOffset().data(), b.display,
		b.drawMode, b.halfbond, b.label, color_val(b.labelColor), b.labelCoord().data(),
		simple_offset(b.labelOffset), b.radius]]

def write_alignment(f, mav):
	assoc_info = {}
	for mol, seq in mav.associations.items():
		match_map = seq.matchMaps[mol]
		info = {}
		for key, value in match_map.items():
			if type(key) == int:
				info[key] = "r%d" % id(value)
		assoc_info[mav.seqs.index(seq)] = info

	from MultAlignViewer.RegionBrowser import SEL_REGION_NAME
	rb = mav.regionBrowser
	regions = []
	for seq, seq_regions in rb.sequenceRegions.items():
		for r in seq_regions:
			if r.name == SEL_REGION_NAME:
				continue
			regions.append((r, seq))
	region_data = []
	for r, seq in regions:
		region_data.append([r.name, region_blocks(mav, r), r.shown, r.interiorRGBA, r.borderRGBA,
			r.highlighted, r.coverGaps, None if seq is None else mav.seqs.index(seq)])
	data = [mav.title, [seq_data(seq) for seq in mav.seqs], hdr_data(mav), assoc_info, region_data,
		mav.intrinsicStructure]
	print>>f, "make_alignment(%s)" % pickled(data)

def region_blocks(mav, region):
	blocks = []
	for block in region.blocks:
		line1, line2, i1, i2 = block
		if line1 not in mav.seqs and line2 not in mav.seqs:
			continue
		# in Chimera, regions can be drawn in header lines
		seq1 = line1 if line1 in mav.seqs else mav.seqs[0]
		seq2 = line2 if line2 in mav.seqs else mav.seqs[0]
		blocks.append((mav.seqs.index(seq1), mav.seqs.index(seq2), i1, i2))
	return blocks

def seq_data(seq):
	# strip will-be-inaccurate model number...
	seq_name = seq.name
	start = seq_name.find(" (#")
	if start >= 0:
		end = seq_name[start:].find(')')
		if end >= 0:
			if seq_name[start+3:][:end-3].isdigit():
				seq_name = seq_name[:start] + seq_name[start+end+1:]
	return [seq_name, str(seq)]

def scaled_seq(hdr):
	if hasattr(hdr, 'depictionVal'):
		return [hdr.depictionVal(i) for i in range(len(hdr))]
	return hdr.sequence

def hdr_data(mav):
	data = { hdr.name: scaled_seq(hdr) for hdr in mav.headers(shownOnly=True) }
	from MultAlignViewer.prefs import CONSERVATION_STYLE
	return data, mav.prefs[CONSERVATION_STYLE]

restore_model_definition = """
def restore_model_data(m, data):
	name, display, axis, angle, trans, use_clip_plane, use_clip_thickness, clip_plane, clip_thickness = data
	m.name = name
	m.display = display
	from chimerax.geometry import Place, rotation, translation
	from numpy import array, float64, transpose
	m.scene_position = translation(trans) * rotation(axis, angle)
	if use_clip_plane:
		from chimerax.std_commands.clip import clip
		origin, normal = clip_plane
		from chimerax.core.commands import Axis, Center
		kw = {
			'position': Center(coords=origin),
			'axis': Axis(coords=normal),
			'coordinate_system': m.scene_position
		}
		if use_clip_thickness:
			kw['front'] = 0 - clip_thickness/2
			kw['back'] = clip_thickness/2
		else:
			kw['front'] = 0
		def perform_clipping(*args, ses=session, kw=kw, frame_counter=[0]):
			from chimerax.std_commands.clip import clip
			clip(ses, **kw)
			frame_counter[0] += 1
			if frame_counter[0] > 3:
				from chimerax.core.triggerset import DEREGISTER
				return DEREGISTER
		session.triggers.add_handler('new frame', perform_clipping)
"""

restore_axes_definition = """
def restore_axes(axes_data):
	from chimerax.axes_planes.cmd import cmd_define_axis
	grouping_models = {}
	for axis_data in axes_data:
		model_data, assoc_structure, number, rgba, radius, extents, center, direction = axis_data
		axis = cmd_define_axis(session, color=rgba_to_color(rgba), radius=radius,
			from_point=[c+extents[0]*d for c, d in zip(center, direction)],
			to_point=[c+extents[1]*d for c, d in zip(center, direction)], show_tool=False)[0]
		restore_model_data(axis, model_data)
		if assoc_structure:
			session.models.remove([axis])
			s = structure_map[assoc_structure]
			group = grouping_models.get(s, None)
			if group is None:
				from chimerax.core.models import Model
				group = grouping_models[s] = Model("helix axes", s.session)
				s.add([group])
			fields = axis.name.split(" H")
			if len(fields) == 2 and fields[-1].isdigit():
				axis.name = "helix %d" % int(fields[-1])
			from chimerax.geometry import identity
			axis.position = identity()
			group.add([axis])
"""

restore_centroids_definition = """
def restore_centroids(centroids_data):
	from chimerax.centroids import CentroidModel
	from chimerax.centroids.cmd import simplified_string
	for centroid_data in centroids_data:
		model_data, assoc_structure, number, rgba, radius, center = centroid_data
		s = CentroidModel(session)
		restore_model_data(s, model_data)
		r = s.new_residue('centroid', 'centroid', 1)
		from chimerax.atomic.struct_edit import add_atom
		import numpy
		a = add_atom("centroid", 'C', r, numpy.array(center))
		a.color = rgba_to_color(rgba).uint8x4()
		a.radius = radius
		a.string = lambda a=a, **kw: simplified_string(a, **kw)
		if assoc_structure:
			from chimerax.geometry import identity
			s.position = identity()
			structure_map[assoc_structure].add([s])
		else:
			session.models.add([s])
"""

restore_planes_definition = """
def restore_planes(planes_data):
	from chimerax.axes_planes import PlaneModel
	from chimerax.geometry import Plane, identity
	from numpy import array
	for plane_data in planes_data:
		model_data, assoc_structure, number, rgba, radius, thickness, origin, normal = plane_data
		plane = Plane(array(origin), normal=array(normal))
		pm = PlaneModel(session, "plane", plane, thickness, radius, rgba_to_color(rgba).uint8x4())
		restore_model_data(pm, model_data)
		if assoc_structure:
			pm.position = identity()
			structure_map[assoc_structure].add([pm])
		else:
			session.models.add([pm])
"""

make_structure_definition = """
def make_structure(structure_data):
	model_data, auto_chain, ball_scale, color, line_type, line_width, lower_case_chains, mol2_comments, \\
		mol2_data, pdb_headers, pdb_version, point_size, ribbon_hides_backbone, ribbon_inside_color, \\
		silhouette, stick_scale, surface_color, surface_opacity, tube, vdw_density, wire_stipple, \\
		coordset_data, res_data, bond_data = structure_data
	from chimerax.atomic import AtomicStructure
	s = AtomicStructure(session, auto_style=False)
	for key, value in pdb_headers.items():
		s.set_metadata_entry(key, value)
	restore_model_data(s, model_data)
	cs_id_lookup = restore_coordset_data(s, coordset_data)
	if tube:
		# s.ribbon_mode_strand is actively buggy
		s.ribbon_mode_helix = s.RIBBON_MODE_ARC
	atom_map = restore_res_data(s, res_data, ribbon_hides_backbone, tube)
	restore_bond_data(s, bond_data, atom_map, stick_scale)
	global_atom_map.update(atom_map)
	s.pdb_version = pdb_version
	s._set_chain_descriptions(session)
	from chimerax.pdb.pdb import set_logging_info
	set_logging_info(s)
	return s
"""

make_molecular_surface_definition = """
def make_molecular_surface(surface_data):
	model_data, probe_radius, density, color, color_mode, atoms = surface_data

	from chimerax.atomic import Atoms
	enclose_atoms = Atoms([global_atom_map[a_id] for a_id in atoms])
	show_atoms = Atoms([a for a in enclose_atoms if a._c2cx_surface_display])
	from math import sqrt
	grid = density / sqrt(3.0)
	from chimerax.atomic.molsurf import MolecularSurface
	s = MolecularSurface(session, enclose_atoms, show_atoms, probe_radius, grid, None, None,
		"name restored later", rgba_to_color(color).uint8x4(), None, True)
	restore_model_data(s, model_data)
	if s.name.startswith("MSMS "):
		s.name = s.name[5:]
	s.calculate_surface_geometry()
	s.auto_update = True
	if color_mode == 1:
		# per atom
		from numpy import array
		s.color_atom_patches(enclose_atoms, None, array([a._c2cx_surface_color for a in enclose_atoms]))
	elif color_mode == 2:
		session.logger.warning("Cannot restore custom surface colors")
	return s
"""

restore_coordset_definition = """
def restore_coordset_data(s, coordset_data):
	xyzs = []
	id_lookup = {}
	for i, data in enumerate(coordset_data):
		cs_id, cs_xyzs = data
		id_lookup[cs_id] = i
		xyzs.append(cs_xyzs)
	from numpy import array
	s.add_coordsets(array(xyzs))
	return id_lookup
"""

restore_res_definition = """
def restore_res_data(s, res_data, ribbon_hides_backbone, tube):
	global residue_map
	atom_map = {}
	for restore_id, current_label_offset, fill_color, fill_display, fill_mode, chain_id, \\
			insertion_code, position, is_helix, is_het, is_strand, label, label_color, \\
			label_coord, label_offset, ribbon_color, ribbon_display, ribbon_draw_mode, \\
			ss_id, type, atom_data in res_data:
		r = s.new_residue(type, chain_id, position, insertion_code)
		residue_map[restore_id] = r
		r.ss_type = r.SS_HELIX if is_helix else (r.SS_STRAND if is_strand else r.SS_COIL)
		r.ss_id = ss_id
		r.ribbon_display = ribbon_display or tube
		r.ribbon_color = rgba_to_color(ribbon_color).uint8x4()
		r.ribbon_hide_backbone = ribbon_hides_backbone
		if label:
			global label_data
			label_data.append((r, "residues", label, rgba_to_color(label_color), label_offset))
		atom_map.update(restore_atom_data(r, atom_data))
	xsection = s.ribbon_xs_mgr.STYLE_ROUND if ribbon_draw_mode == 2 else s.ribbon_xs_mgr.STYLE_SQUARE
	s.ribbon_xs_mgr.set_coil_style(xsection)
	s.ribbon_xs_mgr.set_helix_style(xsection)
	s.ribbon_xs_mgr.set_sheet_style(xsection)
	return atom_map
"""

restore_atom_definition = """
def restore_atom_data(r, atom_data):
	atom_map = {}
	draw_mode_map = { 0: 2, 1: 0, 2: 2, 3: 1 }
	for restore_id, alt_loc, aniso_u, bfactor, coord, coord_index, current_label_offset, \\
			default_radius, display, draw_mode, element_number, hide, idatm_is_explicit, idatm_type, label, \\
			label_color, label_coord, label_offset, name, occupancy, radius, serial_number, \\
			shown_color, surface_category, surface_color, surface_display, surface_opacity, vdw, vdw_color \\
			in atom_data:
		a = r.find_atom(name)
		if alt_loc != '' and a:
			a.set_alt_loc(alt_loc, True)
			a.coord = coord
		else:
			a = r.structure.new_atom(name, element_number)
			r.add_atom(a)
			if alt_loc != '':
				a.set_alt_loc(alt_loc, True)
			a.coord_index = coord_index
			a.display = display
			a.draw_mode = draw_mode_map[draw_mode]
			a.hide = a.HIDE_RIBBON if hide else 0
			if idatm_is_explicit:
				a.idatm_type = idatm_type
			if label:
				global label_data
				label_data.append((a, "atoms", label, rgba_to_color(label_color), label_offset))
			if default_radius != radius:
				a.radius = radius
			a.color = rgba_to_color(shown_color).uint8x4()
		if occupancy is not None:
			a.occupancy = occupancy
		if bfactor is not None:
			a.bfactor = bfactor
		a.serial_number = serial_number
		a.aniso_u6 = tuple((aniso_u[x][y]
			for x,y in [(0,0), (1,1), (2,2), (0,1), (0,2), (1,2)])) if aniso_u is not None else None
		a._c2cx_surface_display = surface_display
		scolor = rgba_to_color(surface_color)
		if surface_opacity >= 0.0:
			scolor.rgba[-1] = surface_opacity
		a._c2cx_surface_color = scolor.uint8x4()
		atom_map[restore_id] = a
	return atom_map
"""

restore_bond_definition = """
def restore_bond_data(s, bond_data, atom_map, stick_scale):
	for atom_ids, bond_attrs in bond_data:
		# bonds between alt locs in Chimera1 can be duplicative in ChimeraX...
		a1, a2 = [atom_map[ident] for ident in atom_ids]
		if a1 not in a2.neighbors:
			b = s.new_bond(a1, a2)
			if stick_scale != 1.0:
				b.radius *= stick_scale
"""

make_pseudobonds_definition = """
def make_pseudobonds(pseudobond_data):
	parent, pbg_data, monitored, pb_data = pseudobond_data
	category, color, solid = pbg_data
	if category == "missing segments":
		for atom_ids, pb_attrs in pb_data:
			a1, a2 = [global_atom_map[ident] for ident in atom_ids]
			pbg = a1.structure.pseudobond_group("missing structure")
			pb = pbg.new_pseudobond(a1, a2)
			if a1.connects_to(a2):
				a1.structure.delete_bond(a1.bonds[a1.neighbors.index(a2)])
			restore_pb_attrs(pb, pb_attrs)
	else:
		if parent is None:
			pbg = session.pb_manager.get_group(category)
		else:
			pbg = structure_map[parent].pseudobond_group(category)
		if monitored:
			precision, show_units = monitored
			monitor = pbg.session.pb_dist_monitor
			monitor.add_group(pbg, session_restore=True)
			monitor.decimal_places = precision
			monitor.show_units = show_units
		for atom_ids, pb_attrs in pb_data:
			a1, a2 = [global_atom_map[ident] for ident in atom_ids]
			pb = pbg.new_pseudobond(a1, a2)
			restore_pb_attrs(pb, pb_attrs)
	if solid:
		pbg.dashes = 0
	return pbg

def restore_pb_attrs(pb, pb_attrs):
	color = pb_attrs[0]
	if color is not None:
		pb.color = rgba_to_color(color).uint8x4()
"""

color_converter_definition = """
def rgba_to_color(rgba):
	from chimerax.core.colors import Color
	return Color(rgba)
"""

restore_selection_definition = """
def restore_selection(atom_data, bond_data, pb_data):
	session.selection.clear()
	for atom_id in atom_data:
		global_atom_map[atom_id].selected = True
	for id1, id2 in bond_data:
		a1 = global_atom_map[id1]
		a2 = global_atom_map[id2]
		for b in a1.bonds:
			if b.other_atom(a1) == a2:
				b.selected = True
				break
	for pbg_id, atom_id1, atom_id2 in pb_data:
		pbg = eval(pbg_id)
		pb_atoms = set([global_atom_map[aid] for aid in (atom_id1, atom_id2)])
		for pb in pbg.pseudobonds:
			if set(pb.atoms) == pb_atoms:
				pb.selected = True
"""

restore_camera_definition = """
def restore_camera(eye_pos, field_of_view, near_clip, far_clip):
	from chimerax.geometry import translation
	session.view.camera.position = translation(eye_pos)
	session.view.camera.field_of_view = field_of_view
	# as a nicety, multiply all matrices by the inverse of the
	# lowest-ID model's matrix, so that newly opened models
	# are in correct relative position to that model at least
	models = session.models[:]
	if models:
		models.sort()
		inverse = models[0].position.inverse(is_orthonormal=True)
		for m in models:
			if len(m.id) == 1:
				m.position = inverse * m.position
		session.view.camera.position = inverse * session.view.camera.position
	from chimerax.std_commands.clip import clip, clip_off
	if near_clip is None and far_clip is None:
		clip_off(session)
	else:
		clip(session, near=near_clip, far=far_clip)
"""

restore_window_size_definition = """
def restore_window_size(w,h):
	from chimerax.graphics.windowsize import window_size
	scaling = session.view.render.pixel_scale()
	window_size(session, round(w/scaling), round(h/scaling))
"""

make_alignment_definition = """
def make_alignment(alignment_data):
	title, seq_data, hdr_data, assoc_info, region_data, intrinsic = alignment_data
	seqs = [restore_seq(sd) for sd in seq_data]
	aln = session.alignments.new_alignment(seqs, title.replace(':', ';'), auto_associate=False,
		intrinsic=intrinsic)
	base_hdr_data, conservation_style = hdr_data
	known_headers = set()
	for hdr in aln.headers:
		hdr.shown = hdr.name in base_hdr_data
		if hdr.name == "Conservation" and conservation_style != "Clustal histogram":
			hdr.style = conservation_style
		known_headers.add(hdr.name)
	for name, contents in base_hdr_data.items():
		if name in known_headers:
			continue
		aln.add_fixed_header(name, contents)
	global residue_map
	from chimerax.atomic import SeqMatchMap
	for seq_index, map_info in assoc_info.items():
		if not map_info:
			continue
		align_seq = aln.seqs[seq_index]
		match_map = SeqMatchMap(align_seq, residue_map[list(map_info.values())[0]].chain)
		for index, res_id in map_info.items():
			match_map.match(residue_map[res_id], index)
		aln.prematched_assoc_structure(match_map, False, False)
	if aln.viewers:
		viewer = aln.viewers[0]
		if not viewer.seq_canvas.wrap_okay():
			# Docking non-wrapped alignments causes very wide ChimeraX window; float instead
			viewer.tool_window.floating = True
		for name, blocks, shown, fill, outline, highlighted, cover_gaps, seq_index in region_data:
			viewer.new_region(name=name, blocks=blocks, fill=fill, outline=outline, select=highlighted,
				cover_gaps=cover_gaps, session_restore=True, shown=shown,
				sequence=(None if seq_index is None else aln.seqs[seq_index]))
"""

restore_seq_definition = """
def restore_seq(seq_data):
	name, sequence = seq_data
	from chimerax.atomic import Sequence
	return Sequence(name=name, characters=sequence)
"""

restore_2d_labels_definition = """
def restore_2d_labels(labels_data):
	from chimerax.label.label2d import Label
	from chimerax.core.colors import Color
	used = set()
	for pos, background, margin, outline, opacity, rgba, size, bold, italic, font, text in labels_data:
		if background is not None:
			background = Color(background)
		font = font_mapping.get(font, font)
		label_name = text
		label_num = 1
		while label_name in used:
			label_name = "%s (%d)" % (label_name, label_num)
			label_num += 1
		Label(session, label_name, text=text, xpos=pos[0], ypos=pos[1],
			color=Color(rgba).uint8x4(), size=size, font=font, bold=bold, italic=italic,
			background=background, outline_width=outline, margin=margin)
"""

restore_color_key_definition = """
def restore_color_key(key_info):
	from chimerax.color_key.model import get_model
	key = get_model(session)
	for k, v in key_info.items():
		if k == "font":
			v = font_mapping.get(v, v)
		setattr(key, k, v)
"""

restore_arrows_definition = """
def restore_arrows(arrows_data):
	from chimerax.label.arrows import Arrow
	from chimerax.core.colors import Color
	used = set()
	arrow_num = 0
	for ident, start, end, head_style, shown, weight, rgba, opacity in arrows_data:
		while ident is None or ident in used:
			arrow_num += 1
			ident = "arrow %d" % arrow_num
		used.add(ident)
		Arrow(session, ident, start=start, end=end, color=Color(rgba).uint8x4(), weight=weight,
			head_style=head_style, visibility=shown)
"""
