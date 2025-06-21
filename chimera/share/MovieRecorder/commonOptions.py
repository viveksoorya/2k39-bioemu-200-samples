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

from chimera import preferences
import sys

RENDERING = "rendering type"
NUM_SUPERSAMPLES = "number of supersamples"
ENCODE_FORMAT = "encoded movie format (command version)"
IMAGE_FORMAT = "image format"
QUALITY= "recording quality"
USER_RECORD_ARGS = "user-supplied record args"
USER_ENCODE_ARGS = "user-supplied encode args"

from MoviePreferences import MovieQualityOption, MovieRecordFFormatOption, \
		MOVIE_ENCODE_QUALITY, MOVIE_RECORD_FFORMAT
from RecorderGUI import formats, default_format, format_name_field, command_formats, \
		format_description_field, movie_format_synonyms
defaults = {
	RENDERING: "supersample", # has to match commonOptions.RenderingOption
	NUM_SUPERSAMPLES: 3,
	ENCODE_FORMAT: default_format[format_name_field],
	QUALITY: MovieQualityOption.default,
	IMAGE_FORMAT: MovieRecordFFormatOption.default,
	USER_RECORD_ARGS: "",
	USER_ENCODE_ARGS: ""
}

from copy import deepcopy
prefs = preferences.addCategory("common movie-recording settings",
	preferences.HiddenCategory, optDict=deepcopy(defaults))

class CommonMovieOptions(object):
	def __init__(self, frame, startRow=0, startCol=0, externalRecordKeywords=[],
			externalEncodeKeywords=[], renderIncludeScreenGrab=False):
		"""Class of widgets for gathering common record/encode settings and returning
		   corresponding arg strings to add to 'movie record' and 'movie encode'
		   commands.

		   The widgets will be gridded into the provided 'frame', starting at 'startRow'
		   and 'startCol'.  Two columns will be used. 'startRow' can be an integer or an
		   instance of itertools.count().  If it's an integer then the first row after the
		   widgets will be in self.nextAvailableRow.

		   Keywords that are gathered by non-CommonMovieOptions parts of the interface
		   (other than 'format', which is always assumed to be gathered) should be
		   listed in externalRecordKeywords or externalEncodeKeywords as appropriate.

		   The optionStrings() method returns two strings of arguments to add to the
		   'movie record' and 'movie encode' commands respectively.
		"""

		if type(startRow) == int:
			import itertools
			row = itertools.count(startRow)
		else:
			row = startRow

		self.__prevFmt = None
		self.__initialRenderCB = True
		self.renderingOptions = RenderingOptions(frame, row, startCol=startCol,
			includeScreenGrab=renderIncludeScreenGrab, renderingChangeCB=self.__renderChange)

		import Tkinter, Pmw
		from chimera.widgets import DisclosureFrame
		df = DisclosureFrame(frame, text="Advanced Options")
		self.qualityOpt = MovieQualityOption(df.frame, 0, MOVIE_ENCODE_QUALITY,
			prefs[QUALITY], None)
		self.formatOpt = MovieRecordFFormatOption(df.frame, 1, MOVIE_RECORD_FFORMAT,
			prefs[IMAGE_FORMAT], None)
		from chimera.tkoptions import StringOption
		self.userRecordArgsOpt = StringOption(df.frame, 2, "Additional recording options",
			prefs[USER_RECORD_ARGS], None, balloon=
			"Options (other than: %s) for\n"
			"recording frames as per Chimera's 'movie record' command"
			% ", ".join(['supersample', 'raytrace', 'format'] + externalRecordKeywords))
		self.userEncodeArgsOpt = StringOption(df.frame, 3, "Additional encoding options",
			prefs[USER_ENCODE_ARGS], None, balloon=
			"Options (other than: %s) for composing the frames\n"
			"into the final animation as per Chimera's 'movie encode' command"
			% ", ".join(['quality'] + externalEncodeKeywords))

		df.frame.columnconfigure(0, weight=1)
		df.frame.columnconfigure(1, weight=1)
		df.grid(row=row.next(), column=startCol, columnspan=2, sticky="ew")
		if prefs[USER_RECORD_ARGS] or prefs[USER_ENCODE_ARGS]:
			df.header.invoke()

		if type(startRow) == int:
			self.nextAvailableRow = row.next()

	def optionStrings(self, savePrefs=True):
		recordArgs = self.renderingOptions.optionString(savePrefs=savePrefs)
		format = self.formatOpt.get()
		userRecordArgs = self.userRecordArgsOpt.get().strip()
		recordArgs += " format %s %s" % (format, userRecordArgs)

		quality = self.qualityOpt.get()
		userEncodeArgs = self.userEncodeArgsOpt.get().strip()
		encodeArgs = "quality %s %s" % (quality, userEncodeArgs)
		if savePrefs:
			prefs[QUALITY] = quality
			prefs[IMAGE_FORMAT] = format
			prefs[USER_RECORD_ARGS] = userRecordArgs
			prefs[USER_ENCODE_ARGS] = userEncodeArgs

		return recordArgs, encodeArgs
	
	def __renderChange(self, rendering):
		if self.__initialRenderCB:
			# ignore setup callback
			self.__initialRenderCB = False
			return
		if rendering == RENDERING_RAYTRACE:
			self.__prevFmt = self.formatOpt.get()
			from MoviePreferences import RAYTRACE_FORMATS
			self.formatOpt.set(RAYTRACE_FORMATS[0])
		else:
			if self.__prevFmt:
				self.formatOpt.set(self.__prevFmt)
				self.__prevFmt = None
			else:
				self.formatOpt.set(MovieRecordFFormatOption.default)

RENDERING_SCREEN, RENDERING_SUPERSAMPLE, RENDERING_RAYTRACE = renderingVals = ["screen",
		"supersample", "ray trace"]

class RenderingOptions(object):
	def __init__(self, frame, startRow, startCol=0, renderVal=None, supersampleVal=None,
			renderingChangeCB=None, supersampleChangeCB=None, includeScreenGrab=True):

		if type(startRow) == int:
			import itertools
			row = itertools.count(startRow)
		else:
			row = startRow

		from chimera.tkoptions import SymbolicEnumOption
		baseBalloon = \
			"Chimera supersampling produces high quality images quickly and is best\n" \
			"for most final recordings.\n" \
			"High supersamples settings may produce thin lines (depends on graphics card).\n" \
			"\n" \
			"POV-Ray raytracing also produces high quality images, but is quite slow.\n" \
			"It is sometimes needed when shadows are important (e.g. some surfaces)\n" \
			"but is usually bad for ribbon depictions due to confusing criss-cross shadows."
		labels = ["screen grab", "Chimera", "POV-Ray"]
		if includeScreenGrab:
			renderVals = renderingVals
			renderLabels = labels
			balloon = \
				"'Screen grab' rendering is fastest but its quality is limited to what\n" \
				"is shown in the Chimera graphics window.\n" \
				"For this type of rendering, the Chimera window must not have other\n" \
				"windows/menus on top of it.\n" \
				"\n" + baseBalloon
		else:
			renderVals = renderingVals[1:]
			renderLabels = labels[1:]
			balloon = baseBalloon
		class RenderingOption(SymbolicEnumOption):
			values = renderVals
			labels = renderLabels
			name = "Rendering"
		if renderVal is None:
			renderVal = prefs[RENDERING]
			if renderVal == RENDERING_SCREEN and not includeScreenGrab:
				renderVal = RENDERING_SUPERSAMPLE
		self.userRenderChangeCB = renderingChangeCB
		self.renderingOpt = RenderingOption(frame, row.next(), None, renderVal,
				self._renderingChange, startCol=startCol, balloon=balloon)

		auxRow = row.next()
		from chimera.printer import SupersampleOption
		if supersampleVal is None:
			supersampleVal = min(prefs[NUM_SUPERSAMPLES], max(SupersampleOption.values))
		self.samples = SupersampleOption(frame, auxRow, "Supersample",
				supersampleVal, supersampleChangeCB, startCol=startCol)
		self.samples.forget()
		import Tkinter
		self.povFrame = centeringFrame = Tkinter.Frame(frame)
		centeringFrame.grid(row=auxRow, column=startCol, columnspan=2, sticky="ew")
		def povOptCB():
			from chimera.dialogs import display
			d = display("preferences")
			from chimera.printer import POVRAY_SETUP
			d.setCategoryMenu(POVRAY_SETUP)
		self.povrayButton = Tkinter.Button(centeringFrame, text="POV-Ray Options", pady=0,
			command=povOptCB)
		self.povrayButton.grid(row=0, column=1)
		self.povFrame.grid_remove()
		# some fancy footwork to try to get button centered under previous row widgets
		def centerPOVOptions(startCol=startCol, row=auxRow, frame=frame,
				centeringFrame=centeringFrame, butWidth=self.povrayButton.winfo_reqwidth()):
			widths = [0, 0]
			for col in [startCol, startCol+1]:
				maxWidth = 0
				for gridRow in range(0, row+20):
					width = 0
					for widget in frame.grid_slaves(row=gridRow, column=col):
						width += widget.winfo_reqwidth()
					maxWidth = max(maxWidth, width)
				widths[col-startCol] = maxWidth
			centeringFrame.columnconfigure(0, weight=max(0, widths[0]-butWidth/2))
			centeringFrame.columnconfigure(2, weight=max(0, widths[1]-butWidth/2))
		centeringFrame.after_idle(centerPOVOptions)

		if type(startRow) == int:
			self.nextAvailableRow = row.next()

		# avoid callback before caller has had chance to assign this instance
		# to a variable (to get auxiliary values)
		centeringFrame.after_idle(lambda s=self: s._renderingChange(s.renderingOpt))

	def disable(self):
		self._enableWidgets(False)

	def enable(self):
		self._enableWidgets(True)

	def optionString(self, savePrefs=True):
		supersample, raytrace = self.get(savePrefs=savePrefs)
		if supersample is None:
			return "raytrace true"
		return "raytrace false supersample %d" % supersample

	def get(self, savePrefs=True):
		rendering = self.renderingOpt.get()
		if rendering == RENDERING_SCREEN:
			supersample = 0
			raytrace = False
		elif rendering == RENDERING_SUPERSAMPLE:
			supersample = self.samples.get()
			raytrace = False
		else:
			raytrace = True
			supersample = None
		if savePrefs:
			prefs[RENDERING] = rendering
			if supersample:
				prefs[NUM_SUPERSAMPLES] = supersample
		return supersample, raytrace

	def _enableWidgets(self, doEnable):
		from chimera.tkoptions import Option
		for widget in [self.renderingOpt, self.samples, self.povrayButton]:
			if isinstance(widget, Option):
				if doEnable:
					widget.enable()
				else:
					widget.disable()
			else:
				if doEnable:
					widget.config(state='normal')
				else:
					widget.config(state='disabled')

	def _renderingChange(self, opt):
		rendering = opt.get()
		if rendering == RENDERING_SCREEN:
			self.samples.gridUnmanage()
			self.povFrame.grid_remove()
		elif rendering == RENDERING_SUPERSAMPLE:
			self.samples.gridManage()
			self.povFrame.grid_remove()
		else:
			self.samples.gridUnmanage()
			self.povFrame.grid()
		if self.userRenderChangeCB:
			self.userRenderChangeCB(rendering)

from OpenSave import SaveModeless
class BaseRecordDialog(SaveModeless):
	title = "Record Movie"
	default = "Record"

	def __init__(self, historyID="recorded movies", **kw):
		import RecorderGUI
		filters = []
		for fmtInfo in formats:
			fmt, ext = fmtInfo[:2]
			filters.append((fmt, '*.' + ext, "." + ext))
		cmdFormat = command_formats[prefs[ENCODE_FORMAT]]
		self.extraButtons = list(getattr(self, 'extraButtons', [])) + ['Image Tips']

		SaveModeless.__init__(self, clientPos='s', clientSticky='ew', filters=filters,
			defaultFilter=cmdFormat[format_description_field], historyID=historyID, **kw)

	def fillInUI(self, parent, **kw):
		SaveModeless.fillInUI(self, parent)
		self.clientArea.columnconfigure(kw.get('startCol', 0) + 1, weight=1)
		self.__commonOptions = CommonMovieOptions(self.clientArea, **kw)


	def commonOptionStrings(self, savePrefs=True):
		recordArgs, encodeArgs = self.__commonOptions.optionStrings(savePrefs=savePrefs)
		path, encodeFormat = self.getPathsAndTypes()[0]
		if ' ' not in path:
			reprPath = path
		elif '"' not in path:
			reprPath = '"' + path + '"'
		else:
			reprPath = "'" + path + "'"
		for cmdFormatName, format in command_formats.items():
			if format[format_description_field] == encodeFormat:
				break
		else:
			raise AssertionError("Provided format %s cannot be found in list of formats"
					% encodeFormat)
		if savePrefs:
			prefs[ENCODE_FORMAT] = movie_format_synonyms.get(cmdFormatName, cmdFormatName)
		return recordArgs, "output %s format %s " % (reprPath, cmdFormatName) + encodeArgs

	Record = SaveModeless.Save

	def ImageTips(self):
		from chimera import help
		help.display("UsersGuide/print.html#tips")
