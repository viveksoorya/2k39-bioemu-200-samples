# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: RecorderDialog.py 36825 2012-07-05 21:05:43Z pett $

import Tkinter, Pmw
from OpenSave import SaveModeless
from prefs import prefs, RECORDER_ROUNDTRIP
from MovieRecorder.commonOptions import BaseRecordDialog
import chimera

class RecorderDialog(BaseRecordDialog):
	title = "Record Animation of Trajectory"
	help = "ContributedSoftware/movie/movie.html#recording"

	def __init__(self, movie):
		self.movie = movie
		movie.subdialogs.append(self)
		BaseRecordDialog.__init__(self, historyID="MD recorder")

	def destroy(self):
		self.movie = None
		BaseRecordDialog.destroy(self)

	def fillInUI(self, parent):
		BaseRecordDialog.fillInUI(self, parent, startRow=10,
				externalEncodeKeywords=["roundtrip"])
		row = 0

		startFrame = self.movie.startFrame
		endFrame = self.movie.endFrame
		from chimera.tkoptions import IntOption, BooleanOption
		self.startFrame = IntOption(self.clientArea, row,
					"Starting frame", startFrame, None,
					min=startFrame, max=endFrame, width=6)
		row += 1

		numFrames = endFrame - startFrame + 1
		defStride = 1 + int(numFrames/300)
		self.stride = IntOption(self.clientArea, row, "Step size",
			defStride, None, min=1, max=numFrames, width=3)
		row += 1

		self.endFrame = IntOption(self.clientArea, row, "Ending frame",
			endFrame, None, min=startFrame, max=endFrame, width=6)
		row += 1

		self.roundtrip = BooleanOption(self.clientArea, row, "Encode"
			' forward then backward ("roundtrip")', prefs[
			RECORDER_ROUNDTRIP], None, balloon=
			"Encode the frames in forward and then reverse\n"
			"order so that if the movie is played as a loop\n"
			"the motion seems continuous")
		row += 1

	def Apply(self):
		from chimera import UserError
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
		roundtrip = self.roundtrip.get()
		prefs[RECORDER_ROUNDTRIP] = roundtrip
		commonRecordArgs, commonEncodeArgs = self.commonOptionStrings()
		recordArgs =  commonRecordArgs
		encodeArgs = " ".join([commonEncodeArgs, "roundtrip", str(roundtrip)])
		self.movie.recordAnimation(startFrame=startFrame,
				endFrame=endFrame, step=self.stride.get(),
				recordArgs=recordArgs, encodeArgs=encodeArgs)
