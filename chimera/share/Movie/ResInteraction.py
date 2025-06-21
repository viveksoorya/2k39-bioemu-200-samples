# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: RmsdMap.py 36306 2012-04-26 20:54:25Z pett $

import Tkinter, Pmw
from chimera.baseDialog import ModelessDialog
from chimera import UserError
from prefs import prefs, RES_NET_WEIGHTING, RES_NET_IGNORE_BONDED, \
	RES_NET_SOLVENT_NODE, RES_NET_IONS_NODE, RES_NET_EDGE_DISCARD_FRAC, \
	RES_NET_EDGE_DISCARD_WEIGHT, RES_NET_EDGE_HIST_MARKERS, RES_NET_EDGE_WIDTH, \
	RES_NET_INTERACTION_TYPE

class ResInteractionStarter(ModelessDialog):
	title = "Get Residue Interaction Parameters"
	help = "ContributedSoftware/movie/movie.html#rins"

	def __init__(self, movie, clusterInfo=None, differenceNetwork=False):
		self.movie = movie
		self.clusterInfo = clusterInfo
		self.differenceNetwork = differenceNetwork
		self.paramDialogs = []
		if clusterInfo:
			self.oneshot = True
			self.title = "Calculate Residue-Interaction Network for Cluster"
		else:
			self.title = "Calculate Residue-Interaction Network for Trajectory"
		movie.subdialogs.append(self)
		ModelessDialog.__init__(self)

	def fillInUI(self, parent):
		parent.columnconfigure(0, weight=1)
		import itertools
		row = itertools.count()

		from CGLtk.WrappingLabel import WrappingLabel
		disclaimer = WrappingLabel(parent, text= "To show the network you need to start"
			" Cytoscape first and then run Chimera via Cytoscape's StructureViz plugin.",
			fg="#ff0000")
		from CGLtk.Font import shrinkFont
		shrinkFont(disclaimer, fraction=1.25)
		disclaimer.grid(row=row.next(), column=0, columnspan=2, sticky="ew")
		if self.differenceNetwork:
			WrappingLabel(parent, text="Compute the difference between the"
				" residue-interaction networks for two clusters.  OK"
				" will bring up a dialog for specifying contact parameters.",
				relief="ridge", bd=4).grid(row=row.next(), column=0,
				columnspan=2, sticky="ew")
		else:
			if self.clusterInfo:
				addendum = ""
			else:
				addendum = "  To compute an interaction network for a cluster," \
					" first calculate clusters using the Analysis menu, then use" \
					" the cluster dialog residue-interaction network option."
			WrappingLabel(parent, text="Compute residue-interaction network.  OK"
				" will bring up a dialog for specifying contact parameters.%s"
				% addendum, relief="ridge", bd=4).grid(row=row.next(), column=0,
				columnspan=2, sticky="ew")

		from chimera.tkoptions import IntOption, BooleanOption, FloatOption, EnumOption
		if not self.clusterInfo:
			startFrame = self.movie.startFrame
			endFrame = self.movie.endFrame
			self.startFrame = IntOption(parent, row.next(), "Starting frame",
				startFrame, None, min=startFrame, max=endFrame, width=6)

			numFrames = endFrame - startFrame + 1
			defStride = 1 + int(numFrames/300)
			self.stride = IntOption(parent, row.next(), "Step size", defStride,
				None, min=1, max=numFrames, width=3)

			self.endFrame = IntOption(parent, row.next(), "Ending frame", endFrame,
				None, min=startFrame, max=endFrame, width=6)

		class InteractionTypeOption(EnumOption):
			values = ["H-bonds", "contacts"]
		self.interactionType = InteractionTypeOption(parent, row.next(),
			"Type of residue interactions", prefs[RES_NET_INTERACTION_TYPE], None)

		self.doWeight = BooleanOption(parent, row.next(), "Weight interactions"
			" by number of H-bonds/contacts formed", prefs[RES_NET_WEIGHTING],
			self._weightingChange)

		self.ignoreBonded = BooleanOption(parent, row.next(), "Ignore H-bonds/contacts"
			" between covalently bonded residues", prefs[RES_NET_IGNORE_BONDED], None)

		self.lumpSolvent = BooleanOption(parent, row.next(), "Group solvent as"
			" one node", prefs[RES_NET_SOLVENT_NODE], None)

		self.lumpIons = BooleanOption(parent, row.next(), "Group ions as"
			" one node", prefs[RES_NET_IONS_NODE], None)

		lowRow = row.next()
		self.lowValueCutoff = FloatOption(parent, lowRow, "Discard-edge threshold",
			prefs[RES_NET_EDGE_DISCARD_FRAC], None, balloon="Omit residue interactions"
			" that occur in less than the given fraction of frames")
		self.lowValueCutoff.forget()
		self.lowWeightCutoff = FloatOption(parent, lowRow, "Weighted discard-edge"
			" threshold", prefs[RES_NET_EDGE_DISCARD_WEIGHT], None, balloon=
			"Omit residue interactions whose final weight is less than the given value.")
		self.lowWeightCutoff.forget()
		# due to the way the .forget() method works, can't manage both and then
		# forget the one we don't want...
		if self.doWeight.get():
			self.lowWeightCutoff.manage()
		else:
			self.lowValueCutoff.manage()


	def Apply(self):
		if self.clusterInfo:
			if self.differenceNetwork:
				info1, info2 = self.clusterInfo
				frames = (info1[0], info2[0])
				rep = (info1[1], info2[1])
			else:
				frames, rep = self.clusterInfo
		else:
			startFrame = self.startFrame.get()
			stride = self.stride.get()
			endFrame = self.endFrame.get()
			if endFrame <= startFrame:
				self.enter()
				raise UserError("Start frame must be less"
								" than end frame")
			if startFrame < self.movie.startFrame \
			or endFrame > self.movie.endFrame:
				self.enter()
				raise UserError("Start or end frame outside of trajectory")
			frames = range(startFrame, endFrame+1, stride)
			rep = None

		class ParamsBase:
			buttons = ("OK", "Cancel")
			oneshot = True

			mdresnet_frames = frames
			mdresnet_representative = rep
			mdresnet_movie = self.movie
			mdresnet_doWeight = self.doWeight.get()
			mdresnet_ignoreBonded = self.ignoreBonded.get()
			mdresnet_lumpSolvent = self.lumpSolvent.get()
			mdresnet_lumpIons = self.lumpIons.get()
			if self.paramDialogs is None:
				mdresnet_container = self.movie.subdialogs
			else:
				mdresnet_container = self.paramDialogs
			if mdresnet_doWeight:
				mdresnet_edgeCutoff = self.lowWeightCutoff.get()
			else:
				mdresnet_edgeCutoff = self.lowValueCutoff.get()
			mdresnet_userClosed = False

			def Apply(slf, *args, **keywds):
				cmdArgs, cmdKeywds = slf.mdresnet_gatherArgsKeywds()
				ResInteractionDialog(slf.mdresnet_movie, slf.mdresnet_frames,
					slf.mdresnet_representative, slf.mdresnet_doWeight,
					slf.mdresnet_ignoreBonded, slf.mdresnet_lumpSolvent,
					slf.mdresnet_lumpIons, slf.mdresnet_edgeCutoff,
					slf.__class__.mdresnet_getInteractions, cmdArgs, cmdKeywds)

			def Close(slf):
				# not being directly destroyed...
				slf.mdresnet_userClosed = True
				try:
					slf.__class__.__bases__[-1].Close(slf)
				except:
					slf.mdresnet_userClosed = False
					raise

			def destroy(slf):
				if slf.mdresnet_userClosed:
					# can't do this directly in Close because some settings
					# call self.enter() and then raise an error, so Close
					# may be called multiple times
					slf.mdresnet_container.remove(slf)

		if self.interactionType.get() == "H-bonds":
			prefs[RES_NET_INTERACTION_TYPE] = "H-bonds"
			from FindHBond.gui import HBDialog
			class HBondParams(ParamsBase, HBDialog):
				title = "Residue Interaction H-Bond Parameters"
				help = "ContributedSoftware/movie/movie.html#rin-hbonds"

				MDResNetMode = True

				def destroy(slf):
					for base in slf.__class__.__bases__:
						base.destroy(slf)

				def mdresnet_gatherArgsKeywds(slf):
					from chimera import UserError
					if slf.relaxParams.relaxConstraints:
						try:
							kw = { 'distSlop': slf.relaxParams.relaxDist,
								'angleSlop': slf.relaxParams.relaxAngle }
						except UserError:
							slf.enter()
							raise
					else:
						kw = { 'distSlop': 0.0, 'angleSlop': 0.0 }
					kw['intermodel'] = False
					kw['intramodel'] = True
					kw['cacheDA'] = True
					
					if slf.inSelection.get():
						from chimera.selection import currentAtoms
						selAtoms = [a for a in currentAtoms()
							if a.molecule == slf.mdresnet_movie.model._mol]
						if not selAtoms:
							slf.enter()
							raise UserError("No trajectory atoms selected!")
						selRestrict = slf.SelShorthands[slf.selType.index(Pmw.SELECT)]
						import weakref
						slf.__class__.mdresnet_hb_selAtoms = weakref.WeakSet(selAtoms)
						if selRestrict == "both":
							kw['donors'] = kw['acceptors'] = \
								slf.__class__.mdresnet_hb_selAtoms
						elif selRestrict == "osl":
							selRestrict = slf.STAtomSpec.get()
					else:
						selRestrict = None
					slf.__class__.mdresnet_hb_selRestrict = selRestrict
					return ([slf.mdresnet_movie.model._mol],), kw

				@classmethod
				def mdresnet_getInteractions(cls, *args, **kw):
					crdSet = kw.pop('crdSet')
					from FindHBond import findHBonds, filterHBondsBySel
					try:
						# since getting findHBonds to use a coord set other
						# than the current coordinate set would be a massive
						# undertaking, use this horrible kludge to get it
						# to use another coord set
						def kludge(slf, cs=crdSet):
							return slf.mdresnet_xformCoord(cs)
						from chimera import Atom
						Atom.mdresnet_xformCoord = Atom.xformCoord
						Atom.xformCoord = kludge
						hbonds = findHBonds(*args, **kw)
					finally:
						Atom.xformCoord = Atom.mdresnet_xformCoord
						delattr(Atom, 'mdresnet_xformCoord')

					if cls.mdresnet_hb_selRestrict is not None:
						hbonds = filterHBondsBySel(hbonds, cls.mdresnet_hb_selAtoms,
							cls.mdresnet_hb_selRestrict)
					return hbonds

			dlg = HBondParams()

		else:
			prefs[RES_NET_INTERACTION_TYPE] = "contacts"
			from DetectClash.gui import DetectClashDialog
			class ContactParams(ParamsBase, DetectClashDialog):
				title = "Residue Interaction Contact Parameters"
				help = "ContributedSoftware/movie/movie.html#rin-contacts"

				IncludeTreatment = False
				IncludeFrequency = False

				def destroy(slf):
					if slf.designated:
						slf.designated.selChangedCB = None
					if slf.designated2:
						slf.designated2.selChangedCB = None
					for base in slf.__class__.__bases__:
						base.destroy(slf)

				def mdresnet_gatherArgsKeywds(slf):
					return DetectClashDialog.gatherArgsKeywds(slf)

				@classmethod
				def mdresnet_getInteractions(cls, *args, **kw):
					from DetectClash import cmdDetectClash
					data = cmdDetectClash(*args, **kw)
					return [(a1, a2) for a1, aContacts in data.items()
						for a2 in aContacts.keys()]

			dlg = ContactParams()
			dlg._contactDefaultsCB()
		if self.paramDialogs is None:
			self.movie.subdialogs.append(dlg)
		else:
			self.paramDialogs.append(dlg)

	def Close(self):
		# if we are one-shot, transfer responsibility for param
		# dialogs to main gui
		if self.clusterInfo:
			self.movie.subdialogs.extend(self.paramDialogs)
			for pd in self.paramDialogs:
				pd.mdresnet_container = self.movie.subdialogs
			self.paramDialogs = None
		ModelessDialog.Close(self)

	def destroy(self):
		if self.paramDialogs is not None:
			for pd in self.paramDialogs:
				pd.destroy()
			self.paramDialogs = None
		self.movie = None
		ModelessDialog.destroy(self)

	def _weightingChange(self, opt):
		if opt.get():
			self.lowValueCutoff.forget()
			self.lowWeightCutoff.manage()
		else:
			self.lowWeightCutoff.forget()
			self.lowValueCutoff.manage()


class ResInteractionDialog(ModelessDialog):
	title = "Residue Interaction Computation and Display"
	oneshot = True
	provideStatus = True
	statusPosition = "above"
	buttons = ("OK", "Apply", "Close")
	help = "ContributedSoftware/movie/movie.html#rin-colors"

	def __init__(self, movie, frames, representative, doWeight, ignoreBonded,
			lumpSolvent, lumpIons, edgeCutoff, interactionsCmd, interactionsArgs,
			interactionsKeywds):
		self.movie = movie
		self.movie.subdialogs.append(self)
		self.frames = frames
		self.representative = representative
		self.ignoreBonded = ignoreBonded
		self.doWeight = doWeight
		self.lumpSolvent = lumpSolvent
		self.lumpIons = lumpIons
		self.edgeCutoff = edgeCutoff
		self.interactionsCmd = interactionsCmd
		self.interactionsArgs = interactionsArgs
		self.interactionsKeywds = interactionsKeywds
		ModelessDialog.__init__(self)

	def Close(self):
		if self._computing:
			self._abort = True
			return
		self.movie.subdialogs.remove(self)
		ModelessDialog.Close(self)

	def destroy(self):
		self.movie = None
		ModelessDialog.destroy(self)

	def fillInUI(self, parent):
		from chimera import numpyArrayFromAtoms, UserError

		self._computing = False
		self.buttonWidgets['OK'].configure(state="disabled")
		self.buttonWidgets['Apply'].configure(state="disabled")
		self.buttonWidgets['Close'].configure(text="Abort")

		prefs[RES_NET_WEIGHTING] = doWeight = self.doWeight
		prefs[RES_NET_IGNORE_BONDED] = ignoreBonded = self.ignoreBonded
		if doWeight:
			prefs[RES_NET_EDGE_DISCARD_WEIGHT] = self.edgeCutoff
		else:
			prefs[RES_NET_EDGE_DISCARD_FRAC] = self.edgeCutoff

		from itertools import count
		row = count()

		from CGLtk.Histogram import MarkedHistogram
		self.histogram = MarkedHistogram(parent, statusline=self.status,
			minlabel=True, maxlabel=True, scaling="linear", labelpos='w',
			label_text="Edge weight\nto edge color\nmapping")
		self.histogram['datasource'] = "Computing residue interactions"
		self.histogram.grid(row=row.next(), column=0, columnspan=2, sticky="nsew")

		from chimera.tkoptions import SymbolicEnumOption, StringOption
		class EdgeWidthOption(SymbolicEnumOption):
			values = list(range(1, 11))
			labels = [str(v) for v in values]
		self.edgeWidthOption = EdgeWidthOption(parent, row.next(), "Edge width",
			prefs[RES_NET_EDGE_WIDTH], None, balloon="How thick edges the edges"
			" between nodes in the Cytoscape network are")

		self.netNameOption = StringOption(parent, row.next(), "Network name",
			"MD residue interactions", None, balloon="Title of network in Cytoscape"
			" as well as name of corresponding visual style")

		from collections import defaultdict
		self.differenceNetwork = self.representative is not None \
			and type(self.representative) != int
		if self.differenceNetwork:
			frameSets = self.frames
		else:
			frameSets = [self.frames]
		networkInfo = []
		for fsi, frameSet in enumerate(frameSets):
			numInteractions = defaultdict(int)
			for fni, frameNum in enumerate(frameSet):
				self._computing = True
				self._abort = False
				parent.update() # allow abort
				self._computing = False
				if self._abort:
					parent.after_idle(self.Close)
					return

				# load needed coord sets...
				if len(frameSets) > 1:
					statusInfo = "Frame %d (%d/%d) of cluster %d: " % (frameNum,
							fni+1, len(frameSet), fsi+1)
				else:
					statusInfo = "Frame %d (%d/%d): " % (frameNum,
							fni+1, len(frameSet))
				if not self.representative and not self.movie.findCoordSet(frameNum):
					self.status(statusInfo + "loading")
					self.movie._LoadFrame(frameNum, makeCurrent=False)
				cs = self.movie.findCoordSet(frameNum)

				self.status(statusInfo + "finding interactions")
				self.interactionsKeywds['crdSet'] = cs
				interactions = self.interactionsCmd(*self.interactionsArgs,
					**self.interactionsKeywds)

				self.status(statusInfo + "processing interactions")
				from chimera import bondsBetween
				if not doWeight:
					resPairSeen = set()
				atomPairSeen = set()
				for a1, a2 in interactions:
					if (a1, a2) in atomPairSeen:
						continue
					atomPairSeen.add((a1, a2))
					atomPairSeen.add((a2, a1))

					r1, r2 = a1.residue, a2.residue

					if r1 == r2:
						continue

					if a1.surfaceCategory in ("solvent", "ions") \
					and a2.surfaceCategory in ("solvent", "ions"):
						continue

					if ignoreBonded and bondsBetween(r1, r2, onlyOne=True):
						continue

					if self.lumpSolvent and a1.surfaceCategory == "solvent":
						resID1 = "solvent"
					elif self.lumpIons and a1.surfaceCategory == "ions":
						resID1 = "ions"
					else:
						resID1 = r1
					if self.lumpSolvent and a2.surfaceCategory == "solvent":
						resID2 = "solvent"
					elif self.lumpIons and a2.surfaceCategory == "ions":
						resID2 = "ions"
					else:
						resID2 = r2
					if str(resID1) < str(resID2):
						key = (resID1, resID2)
					else:
						key = (resID2, resID1)
					if not doWeight:
						if key in resPairSeen:
							continue
						resPairSeen.add(key)
					numInteractions[key] += 1
			numFrames = float(len(frameSet))
			for interaction in numInteractions.keys():
				numInteractions[interaction] /= numFrames
			networkInfo.append(numInteractions)

		self.buttonWidgets['Close'].configure(text="Close")

		self.interactions = {}
		if self.differenceNetwork:
			allInteractions = set()
			inter1, inter2 = networkInfo
			allInteractions.update(inter1.keys())
			allInteractions.update(inter2.keys())
			for interaction in allInteractions:
				val1 = inter1.get(interaction, 0.0)
				val2 = inter2.get(interaction, 0.0)
				if val1 < self.edgeCutoff and val2 < self.edgeCutoff:
					continue
				self.interactions[interaction] = val2 - val1
		else:
			for interaction, val in networkInfo[0].items():
				if val < self.edgeCutoff:
					continue
				self.interactions[interaction] = val
		if self.interactions:
			data = self.interactions.values()
			minVal, maxVal = min(data), max(data)
			# need to put data into histogram bins
			binSize = 1.0 / len(frameSet)
			vrange = (maxVal - minVal)
			numBins = int(vrange/binSize + 0.5) + 1
			if numBins == 1:
				bins = [len(data)]
			else:
				bins = [0] * numBins
				binSize = vrange / float(numBins - 1)
				leftEdge = minVal - 0.5 * binSize
				for val in data:
					bin = int((val - leftEdge) / binSize)
					bins[bin] += 1
			self.histogram['datasource'] = (minVal, maxVal, bins)
			self.markers = self.histogram.addmarkers(coordtype="absolute")
			self.markers.extend(prefs[RES_NET_EDGE_HIST_MARKERS][self.differenceNetwork]
				[doWeight])
			self.buttonWidgets['OK'].configure(state="normal")
			self.buttonWidgets['Apply'].configure(state="normal")
			self.status("Click OK or Apply to show network in Cytoscape")
		else:
			self.histogram['datasource'] = "No interacting residues"

	def Apply(self):
		import os, tempfile
		nodes = set()
		netName = self.netNameOption.get()
		cytoInfo = [2, netName]
		fd, path = tempfile.mkstemp(suffix='_network.txt', text=True)
		cytoInfo.append(path)
		f = os.fdopen(fd, "w")
		for interaction, val in self.interactions.items():
			r1, r2 = interaction
			print>>f, "%s\tvdw\t%s\t%g" %(r1, r2, val)
			nodes.add(r1)
			nodes.add(r2)
		f.close()

		fd, path = tempfile.mkstemp(suffix='_nattr.txt', text=True)
		cytoInfo.append(path)
		f = os.fdopen(fd, "w")
		for node in nodes:
			if isinstance(node, basestring):
				print>>f, "%s\t/surfaceCategory=%s" % (node, node)
			else:
				ident = node.oslIdent()
				print>>f, "%s\t%s\t%s" % (node, ident[ident.index(':')+1:],
					node.molecule.name)
		f.close()

		markerSettings = [(m['xy'], m['rgba']) for m in self.markers]
		oldMarkerPref = prefs[RES_NET_EDGE_HIST_MARKERS]
		newMarkerPref = []
		for diff in range(2):
			subPref = []
			for weighted in range(2):
				if diff == self.differenceNetwork and weighted == self.doWeight:
					subPref.append(markerSettings)
				else:
					subPref.append(oldMarkerPref[diff][weighted])
			newMarkerPref.append(tuple(subPref))
		prefs[RES_NET_EDGE_HIST_MARKERS] = tuple(newMarkerPref)
		edgeWidth = prefs[RES_NET_EDGE_WIDTH] = self.edgeWidthOption.get()

		fd, path = tempfile.mkstemp(suffix='_netviz.xml', text=True)
		cytoInfo.append(path)
		f = os.fdopen(fd, "w")
		print>>f, netvizPreamble % netName
		indent1 = "        "
		print>>f, indent1 + "<network>"
		indent2 = indent1 + "    "
		prefix = indent2 + '<visualProperty name="NETWORK_'
		for name, val in [("BACKGROUND_PAINT", "#ffffff"), ("DEPTH", "0.0"),
				("EDGE_SELECTION", "true"), ("HEIGHT", "400.0"),
				("NODE_SELECTION", "true"), ("SCALE_FACTOR", "1.0"),
				("SIZE", "550.0"), ("TITLE", self.movie.title),
				("WIDTH", "550.0")]:
			print>>f, '%s%s" default="%s"/>' % (prefix, name, val)
		for coord in "XYZ":
			print>>f, '%sCENTER_%s_LOCATION" default="0.0"/>' % (prefix, coord)
		print>>f, indent1 + "</network>"
		print>>f, indent1 + "<node>"
		print>>f, indent2 + '<dependency name="nodeCustomGraphicsSizeSync" value="true"/>'
		print>>f, indent2 + '<dependency name="nodeSizeLocked" value="true"/>'
		prefix = indent2 + '<visualProperty name="NODE_'
		for name, val in [("PAINT", "#333333"), ("STROKE", "SOLID"),
				("TRANSPARENCY", "255"), ("WIDTH", "3.0")]:
			print>>f, '%sBORDER_%s" default="%s"/>' % (prefix, name, val)
		for n in range(1, 10):
			print>>f, '%sCUSTOMGRAPHICS_%d" default="org.cytoscape.ding.customgraphics.NullCustomGraphics,0,[ Remove Graphics ],"/>' % (prefix, n)
			print>>f, '%sCUSTOMGRAPHICS_POSITION_%d" default="C,C,c,0.00,0.00"/>' % (prefix, n)
			print>>f, '%sCUSTOMGRAPHICS_SIZE_%d" default="50.0"/>' % (prefix, n)
			print>>f, '%sCUSTOMPAINT_%d" default="DefaultVisualizableVisualProperty(id=NODE_CUSTOMPAINT_2, name=Node Custom Paint %d)"/>' % (prefix, n, n)
		for name, val in [("DEPTH", "0.0"), ("FILL_COLOR", "#00acad"),
				("HEIGHT", "40.0"), ("NESTED_NETWORK_IMAGE_VISIBLE", "true"),
				("PAINT", "#1e90ff"), ("SELECTED", "false"),
				("SELECTED_PAINT", "#ffff00"), ("SHAPE", "ROUND_RECTANGLE"),
				("SIZE", "45.0"), ("TOOLTIP", ""), ("TRANSPARENCY", "255"),
				("VISIBLE", "true"), ("WIDTH", "70.0")]:
			print>>f, '%s%s" default="%s"/>' % (prefix, name, val)
		print>>f, '%sLABEL" default="">' % prefix
		print>>f, indent2 + '    <passthroughMapping attributeType="string" attributeName="name"/>'
		print>>f, indent2 + '</visualProperty>'
		for name, val in [("COLOR", "#000000"), ("FONT_FACE", "Dialog,plain,12"),
				("FONT_SIZE", "12"), ("POSITION", "C,C,c,0.00,0.00"),
				("TRANSPARENCY", "255"), ("WIDTH", "200.0")]:
			print>>f, '%sLABEL_%s" default="%s"/>' % (prefix, name, val)
		for coord in "XYZ":
			print>>f, '%s%s_LOCATION" default="0.0"/>' % (prefix, coord)
		print>>f, indent1 + "</node>"
		print>>f, indent1 + "<edge>"
		print>>f, indent2 + '<dependency name="arrowColorMatchesEdge" value="false"/>'
		prefix = indent2 + '<visualProperty name="EDGE_'
		for name, val in [("LABEL", ""), ("VISIBLE", "true"), ("BEND", ""),
				("CURVED", "true"), ("LINE_TYPE", "SOLID"), ("PAINT", "#323232"),
				("SELECTED", "false"), ("SELECTED_PAINT", "#ff0000"),
				("STROKE_SELECTED_PAINT", "#ff0000"), ("TOOLTIP", ""),
				("TRANSPARENCY", "255"), ("UNSELECTED_PAINT", "#404040"),
				("VISIBLE", "true")]:
			print>>f, '%s%s" default="%s"/>' % (prefix, name, val)
		print>>f, '%sWIDTH" default="%.1f"/>' % (prefix, edgeWidth)
		print>>f, '%sSTROKE_UNSELECTED_PAINT" default="#333333">' % (prefix,)
		print>>f, indent2 + '    <continuousMapping attributeType="float" attributeName="Weight">'
		from CGLtk.color import rgba2tk
		for xy, rgba in markerSettings:
			tkColor = rgba2tk(rgba, fieldWidth=2)
			print>>f, '%s        <continuousMappingPoint lesserValue="%s" greaterValue="%s" equalValue="%s" attrValue="%g"/>' % (indent2, tkColor, tkColor, tkColor, xy[0])
		print>>f, indent2 + '    </continuousMapping>'
		print>>f, indent2 + '</visualProperty>'
		for name, val in [("COLOR", "#000000"), ("FONT_FACE", "Dialog,plain,10"),
				("FONT_SIZE", "10"), ("TRANSPARENCY", "255")]:
			print>>f, '%sLABEL_%s" default="%s"/>' % (prefix, name, val)
		for name, val in [("SELECTED_PAINT", "#ffff00"), ("SHAPE", "NONE"),
				("UNSELECTED_PAINT", "#000000")]:
			print>>f, '%sSOURCE_ARROW_%s" default="%s"/>' % (prefix, name, val)
			print>>f, '%sTARGET_ARROW_%s" default="%s"/>' % (prefix, name, val)
		print>>f, indent1 + "</edge>"
		print>>f, netvizPostmortem
		f.close()
		from sys import __stdout__ as stdout
		print>>stdout, "Trajectory residue network info: %s" % repr(cytoInfo)
		stdout.flush()

netvizPreamble = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<vizmap documentVersion="3.0" id="VizMap-2013_04_30-14_51">
    <visualStyle name="%s">"""
netvizPostmortem = """    </visualStyle>
</vizmap>"""
