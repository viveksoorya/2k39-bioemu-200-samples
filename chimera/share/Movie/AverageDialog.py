# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: VolumeDialog.py 26655 2009-01-07 22:02:30Z gregc $

from chimera.baseDialog import ModelessDialog

class AverageDialog(ModelessDialog):
	help = "ContributedSoftware/movie/movie.html#averaging"
	provideStatus = True
	statusPosition = "left"
	buttons = ('OK', 'Close')
	default= 'OK'

	def __init__(self, movie, clusterInfo=None):
		self.movie = movie
		self.clusterInfo = clusterInfo
		if clusterInfo:
			self.oneshot = True
			self.title = "Calculate Cluster Average Structure"
		else:
			self.title = "Calculate Trajectory Average Structure"
		movie.subdialogs.append(self)
		ModelessDialog.__init__(self)

	def destroy(self):
		self.movie = None
		ModelessDialog.destroy(self)

	def fillInUI(self, parent):
		row = 0

		if self.clusterInfo:
			addendum = ""
		else:
			addendum = "  For cluster averages, first calculate clusters using the"\
				" Analysis menu, then use the cluster dialog averaging option."

		from CGLtk.WrappingLabel import WrappingLabel
		WrappingLabel(parent, text="The average structure of biopolymeric components"
			" (peptides/proteins and nucleic acids) will be calculated and opened"
			" as a new model.  Coordinate averaging may produce poor chemical geometry."
			"%s" % (addendum,),
			relief="ridge", bd=4).grid(
			row=row, column=0, columnspan=2, sticky="ew")
		row += 1

		from chimera.tkoptions import IntOption, BooleanOption, StringOption
		if not self.clusterInfo:
			startFrame = self.movie.startFrame
			endFrame = self.movie.endFrame
			self.startFrame = IntOption(parent, row, "Starting frame",
				startFrame, None, min=startFrame, max=endFrame, width=6)
			row += 1

			numFrames = endFrame - startFrame + 1
			self.stride = IntOption(parent, row, "Step size", 1,
				None, min=1, max=numFrames, width=3)
			row += 1

			self.endFrame = IntOption(parent, row, "Ending frame", endFrame,
				None, min=startFrame, max=endFrame, width=6)
			row += 1

		self.doSelAlign = BooleanOption(parent, row, 'Align structures based'
			' on current selection, if any', True, None)
		row += 1

		self.heavysOnly = BooleanOption(parent, row, 'Omit hydrogens', True, None,
			balloon="Since the average structure will likely have distortions,\n"
			"particularly for hydrogens, it is recommended that hydrogens be\n"
			"added afterward if needed.")
		row += 1

		from gui import IncludeMetalIonsOption as IMIO
		self.metalIons = IMIO(parent, row, IMIO.defaultLabel, IMIO.defaultValue, None)
		row += 1

		self.structName = StringOption(parent, row, 'Name average structure',
			"average", None)
		row += 1

	def Apply(self):
		from chimera import UserError
		if self.clusterInfo:
			frames, rep = self.clusterInfo
			testFrame = rep
		else:
			startFrame = self.startFrame.get()
			endFrame = self.endFrame.get()
			if endFrame <= startFrame:
				self.enter()
				raise UserError("Start frame must be less"
								" than end frame")
			if startFrame < self.movie.startFrame \
			or endFrame > self.movie.endFrame:
				self.enter()
				raise UserError("Start or end frame outside"
								" of trajectory")
			stride = self.stride.get()

			# load needed coord sets...
			for frameNum in range(startFrame, endFrame+1, stride):
				if not self.movie.findCoordSet(frameNum):
					self.movie.status("loading frame %d" % frameNum)
					self.movie._LoadFrame(frameNum, makeCurrent=False)

			frames = range(startFrame, endFrame+1, stride)
			rep = None
			testFrame = startFrame

		frameOffset = self.movie.findCoordSet(testFrame).id - testFrame

		from average import averageStructure, AverageError
		try:
			averageStructure(self.movie.model.Molecule(), [f + frameOffset for f in frames],
				self.doSelAlign.get(), self.heavysOnly.get(), self.metalIons.get(),
				self.structName.get(), superpositionFrame=rep, status=self.movie.status)
		except AverageError, v:
			raise UserError(unicode(v))

