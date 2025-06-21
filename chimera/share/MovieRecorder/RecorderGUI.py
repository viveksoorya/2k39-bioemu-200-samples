from chimera.baseDialog import ModelessDialog
import Tkinter, Pmw

import chimera
from chimera import tkoptions
from chimera import chimage
from chimera import help
from chimera import MOVIE_PREF_UPDATE

import tempfile, os, sys, string

from MovieRecorder import DEFAULT_OUTFILE, EXIT_SUCCESS, EXIT_ERROR, EXIT_CANCEL
from MovieRecorder import DEFAULT_PATTERN
from MovieRecorder import MovieError
from MovieRecorder import RESET_CLEAR, RESET_KEEP, RESET_NONE
from MovieRecorder import BaseRecorderGUI
from utils import getRandomChars
import MoviePreferences
from MoviePreferences import MOVIE_FORMATS, movie_format_synonyms

FRM_OPTS_ROW = 6
MOV_OPTS_ROW = 8

# Formats: (description, file suffix, ffmpeg format name, ffmpeg video codec,
#		   limited frame rates, size restriction, format name)
fields = ('label', 'suffix', 'ffmpeg_name', 'ffmpeg_codec', 'limited_framerates', 'size_restriction')
formats = [tuple(f[k] for k in fields) + (n,) for n, f in MOVIE_FORMATS.items()]
format_description_field = 0
file_suffix_field = 1
file_format_field = 2
video_codec_field = 3
limited_frame_rate_field = 4
size_restriction_field = 5
format_name_field = 6

dfi = MOVIE_FORMATS.keys().index(MoviePreferences.defaults['encode_format'])
default_format = formats[dfi]

# Movie command format names.
command_formats = dict(zip(MOVIE_FORMATS.keys(), formats))
for k, v in movie_format_synonyms.items():
	command_formats[k] = [f for f in formats if
			      f[format_name_field] == v][0]

imageFormats = ('JPEG', 'PNG', 'PPM')
defaultImageFormat = 'PPM'
raytraceImageFormats = ('PNG',)
defaultRaytraceImageFormat = 'PNG'

default_bit_rate = 2000		 # kbits/sec
default_quality = 'good'	 # Variable bit rate quality

class MovieRecorderGUI(ModelessDialog, BaseRecorderGUI):
	name = "Movie Recorder"
	buttons = ('Image Tips', 'Close',)
	provideStatus = True
	help = "ContributedSoftware/recorder/recorder.html"

	def __init__(self):

		self.director = None

		self.this_dir = os.path.split(os.path.abspath(__file__))[0]

		ModelessDialog.__init__(self)

		self.cache_width = None
		self.cache_height = None

		## get the width and height when the frame options are expanded
		self.frmOptionsFrame.grid(row=FRM_OPTS_ROW , column=0, columnspan=3, sticky='nsew')
		chimera.tkgui.app.update_idletasks()
		self.frm_width, self.frm_height = \
						(self.frmOptionsFrame.winfo_width(), self.frmOptionsFrame.winfo_height())
		self.frmOptionsFrame.grid_forget()
		chimera.tkgui.app.update_idletasks()


		## get the width and height when the movie options are expanded
		self.movOptionsFrame.grid(row=MOV_OPTS_ROW, column=0, columnspan=3, sticky='nsew')
		chimera.tkgui.app.update_idletasks()
		self.mov_width, self.mov_height = \
						(self.movOptionsFrame.winfo_width(), self.movOptionsFrame.winfo_height())
		self.movOptionsFrame.grid_forget()
		chimera.tkgui.app.update_idletasks()

		w, h = map(int, self.getCurrentDimensions())
		self._toplevel.wm_geometry('%sx%s' % (w + 30, h + 20))

		#self.director.adjustGfxSize()

		chimera.triggers.addHandler(MOVIE_PREF_UPDATE, self.updatePreference, None)

		chimera.tkgui.app.after(1000, self.showStatus, "Click the record button to start capturing frames")

	def fillInUI(self, parent):
		#recCtrlFrame = Tkinter.Frame(parent)
		#recCtrlFrame.grid(row=0,column=0,columnspan=2, sticky='w', pady=10, padx=10)


		##--------Record button-----------##
		self.recButton = Tkinter.Button(parent, text="Record", command=self.startRecording)
		#self.rec_img   = chimage.get(os.path.join(self.this_dir, "record.png"), self.recButton)
		#self.pause_img = chimage.get(os.path.join(self.this_dir, "pause.png"),  self.recButton)
		#self.recButton.configure(image=self.rec_img, relief='flat')
		#self.recButton._rec_image   = self.rec_img
		#self.recButton._pause_image = self.pause_img
		help.register(self.recButton, balloon="Start capturing frames from the graphics window")
		self.recButton.grid(row=0, column=0, sticky='w', pady=5, padx=10)
		## ---------------------------------



		##--------Encode button-----------##
		self.encButton = Tkinter.Button(parent, text="Make movie", command=self.startEncoding)
		#self.movie_img = chimage.get(os.path.join(self.this_dir, "movie.png"),		self.encButton)
		#self.abort_img = chimage.get(os.path.join(self.this_dir, "abort_movie.png"),  self.encButton)

		#self.encButton.configure(image=self.movie_img, relief='flat')
		#self.encButton._movie_img  = self.movie_img
		#self.encButton._abort_img  = self.abort_img
		help.register(self.encButton, balloon="Make a movie from currently captured frames")

		self.encButton.grid(row=0, column=1, sticky='w')

		## can't encode yet - don't have any frames cached !
		self.encButton.configure(state='disabled')
		## ------------------------------------

		##--------Reset button-----------##
		self.clearButton = Tkinter.Button(parent,
										  text="Reset",
										  command=self.resetRecording)
		help.register(self.clearButton, balloon="Clear all saved frames")
		self.clearButton.configure(state='disabled')
		self.clearButton.grid(row=1, column=0, sticky='w', pady=5, padx=10)
		## ------------------------------------------------



		## -----------Movie format--------------------
		from MoviePreferences import MovieFormatOption
		from commonOptions import prefs, ENCODE_FORMAT
		self.movieFmtOption = MovieFormatOption(parent, 2, 'Output format',
				prefs[ENCODE_FORMAT], self.chooseFmtCB)
		## --------------------------------------------



		## --------Reset after encode---------------
		self.autoResetVar = Tkinter.IntVar(parent)
		self.autoResetVar.set(True)
		Tkinter.Checkbutton(parent, text="Reset after encode",
				variable=self.autoResetVar, command=self.resetModeCB
				).grid(row=1, column=1, sticky='w')
		## -----------------------------------------



		## -------------Output path ------------------
		outputFrame = Tkinter.Frame(parent)
		initialfile = DEFAULT_OUTFILE

		from OpenSave import SaveModeless
		class OutputPathDialog(SaveModeless):
			default = 'Set Movie Path'
			title = 'Select movie output file'
			def SetMoviePath(self):
				self.Save()
		setattr(OutputPathDialog, OutputPathDialog.default,
				OutputPathDialog.SetMoviePath) # Work around OpenSave bug
		ofo = tkoptions.OutputFileOption(outputFrame,
										 0, 'Output file',
										 initialfile,
										 None,
										 balloon='Output file save location '
										 )
		ofo.dialogType = OutputPathDialog
		self.outFileOption = ofo
		outputFrame.grid(row=3, column=0, columnspan=3, sticky='ew', pady=10)
		outputFrame.columnconfigure(1, weight=1)
		## -------------------------------------------





		statsGroup = Pmw.Group(parent, tag_text="Status")
		statsGroup.grid(row=0, column=2, rowspan=3, padx=20, sticky='nsew')
		#statsGroup.configure(hull_width=1000)

		self.frame_num_var = Tkinter.StringVar(parent)
		self.time_left_var = Tkinter.StringVar(parent)

		self.actionLabel	 = Tkinter.Label(statsGroup.interior(), text="Stopped")
		numFramesLabel = Tkinter.Label(statsGroup.interior(),
									   text="# Frames:")#,

		frameResLabel = Tkinter.Label(statsGroup.interior(),
									  text="Resolution:")#,

		estLengthLabel = Tkinter.Label(statsGroup.interior(),
									   text="Est. Length:")#,

		#statsGroup.interior().rowconfigure(0,weight=1)
		statsGroup.interior().columnconfigure(2, weight=1)

		self.accum_frames_var = Tkinter.StringVar(parent)
		self.accum_frames_var.set('0')

		self.frame_res_var = Tkinter.StringVar(parent)
		self.frame_res_var.set('%dx%d' % chimera.viewer.windowSize)

		self.accum_secs_var = Tkinter.StringVar(parent)
		self.accum_secs_var.set('0s.')


		numFramesVal = Tkinter.Label(statsGroup.interior(),
									 textvariable=self.accum_frames_var)

		frameResVal = Tkinter.Label(statsGroup.interior(),
									 textvariable=self.frame_res_var)

		estLengthVal = Tkinter.Label(statsGroup.interior(),
									 textvariable=self.accum_secs_var)

		self.actionLabel.grid(row=0, column=0, columnspan=2, pady=2, sticky='w')
		numFramesLabel.grid(row=1, column=0, pady=2, sticky='w')
		frameResLabel.grid(row=2, column=0, pady=2, sticky='w')
		estLengthLabel.grid(row=3, column=0, pady=2, sticky='w')

		numFramesVal.grid(row=1, column=1, padx=5, sticky='w')
		frameResVal.grid(row=2, column=1, padx=5, sticky='w')
		estLengthVal.grid(row=3, column=1, padx=5, sticky='w')


		parent.columnconfigure(2, weight=1)
		parent.columnconfigure(3, weight=2)
		parent.rowconfigure(9, weight=1)

		dummyFrame = Tkinter.Frame(parent, relief='groove', borderwidth=1)
		Tkinter.Frame(dummyFrame).pack()
		dummyFrame.grid(row=4, column=0, columnspan=3, pady=10, sticky='ew')

		## -------------- Frame options -----------------------
		frmOptChBFrame = Tkinter.Frame(parent, background="gray")
		frmOptChBFrame.grid(row=5, column=0, columnspan=3, pady=5, sticky='ew')
		frmOptChBFrame.columnconfigure(1, weight=1)

		self.frmOptionsVar = Tkinter.IntVar(frmOptChBFrame)
		frmOptionsChB = Tkinter.Checkbutton(frmOptChBFrame,
											indicatoron=False,
											selectcolor='',
											background="gray",
											offrelief='flat',
											overrelief='flat',
											text="Options...",
											relief='flat',
											variable=self.frmOptionsVar,
											command=self.showFrmOptionsCB)

		r_arrow_img = chimage.get("rightarrow.png", frmOptionsChB)
		frmOptionsChB.configure(image=r_arrow_img)
		frmOptionsChB._image = r_arrow_img

		d_arrow_img = chimage.get("downarrow.png", frmOptionsChB)
		frmOptionsChB.configure(selectimage=d_arrow_img)
		frmOptionsChB._selectimage = d_arrow_img

		#frmOptionsChB.configure(relief='sunken')
		#print frmOptionsChB.configure().keys()
		frmOptionsChB.grid(row=0, column=0, sticky='w')

		frmOptionsLabel = Tkinter.Label(frmOptChBFrame, text="Frame Options", background="gray")
		frmOptionsLabel.grid(row=0, column=1, sticky='w', padx=5)

		self.frmOptionsFrame = Tkinter.Frame(parent)
		self.populateFrmOptionsFrame()
		## ---------------------------------------------------


		## --------------------- Movie options -----------------

		movOptChBFrame = Tkinter.Frame(parent, background="gray")
		movOptChBFrame.grid(row=7, column=0, columnspan=3, pady=5, sticky='ew')
		movOptChBFrame.columnconfigure(1, weight=1)

		self.movOptionsVar = Tkinter.IntVar(movOptChBFrame)
		movOptionsChB = Tkinter.Checkbutton(movOptChBFrame,
											indicatoron=False,
											selectcolor='',
											background="gray",
											offrelief='flat',
											overrelief='flat',
											text="Options...",
											relief='flat',
											variable=self.movOptionsVar,
											command=self.showMovOptionsCB)

		movOptionsChB.configure(image=r_arrow_img)
		movOptionsChB._image = r_arrow_img

		movOptionsChB.configure(selectimage=d_arrow_img)
		movOptionsChB._selectimage = d_arrow_img

		movOptionsChB.grid(row=0, column=0, sticky='w', pady=0)

		movOptionsLabel = Tkinter.Label(movOptChBFrame, text="Movie Options", background="gray")
		movOptionsLabel.grid(row=0, column=1, sticky='w', padx=5)


		self.movOptionsFrame = Tkinter.Frame(parent)
		self.populateMovOptionsFrame()
		self.movOptionsFrame.columnconfigure(0, weight=1)
		## -----------------------------------------------------

		self.initDirector()

	def populateFrmOptionsFrame(self):

		#inputOptsGroup = Pmw.Group(self.optionsFrame, tag_text="Frame capture options")
		#inputOptsGroup.grid(row=0, column=0, sticky='nsew', pady=10)

		self.inputDirOption = tkoptions.InputFileOption(self.frmOptionsFrame,
													  0, 'Directory',
													  tempfile.gettempdir(), None,
													  balloon='Directory to use for saving image files',
													  dirsOnly=True
													  )

		self.inputPatternOption = tkoptions.StringOption(self.frmOptionsFrame,
														 1, 'Filename pattern',
														 DEFAULT_PATTERN % getRandomChars()
														 , None)

		from MoviePreferences import MovieRecordFFormatOption
		self.imgFmtOption = MovieRecordFFormatOption(self.frmOptionsFrame, 2, 'Format',
				defaultImageFormat, None)

		from commonOptions import RenderingOptions, RENDERING_SCREEN
		self.renderingOptions = RenderingOptions(self.frmOptionsFrame, 3,
				renderVal=RENDERING_SCREEN, renderingChangeCB=self.renderingCB)
		row = self.renderingOptions.nextAvailableRow

		self.keepSrcOption = tkoptions.BooleanOption(self.frmOptionsFrame, row,
				"Save images on Reset", False, self.resetModeCB)
		row += 1

		self.frmOptionsFrame.columnconfigure(1, weight=1)


	def populateMovOptionsFrame(self):

		##--------------Quality params-------------------

		mof = Tkinter.Frame(self.movOptionsFrame)
		mof.grid(row=1, column=0, sticky='w')
		Tkinter.Label(mof, text="Bit rate controls quality and file size:"
				).grid(row=0, column=0, sticky='w')
		self.bitrate_mode = Tkinter.StringVar(mof)
		self.bitrate_mode.set("variable")

		brf = Tkinter.Frame(mof)
		brf.grid(row=2, column=0, sticky='w')
		Tkinter.Radiobutton(brf, variable=self.bitrate_mode, value="constant", padx=0
				).grid(row=0, column=0, sticky='w')
		from MoviePreferences import MovieBitrateOption, MOVIE_ENCODE_BITRATE
		self.bit_rate = MovieBitrateOption(brf, 0, MOVIE_ENCODE_BITRATE, None, None, startCol=1)

		qf = Tkinter.Frame(mof)
		qf.grid(row=1, column=0, sticky='w')
		Tkinter.Radiobutton(qf, variable=self.bitrate_mode, value="variable", padx=0
				).grid(row=0, column=0, sticky='w')
		# can't get spacing right use 'text' option of Radiobutton, so...
		Tkinter.Label(qf, text="Variable bit rate; ").grid(row=0, column=1)
		from MoviePreferences import MovieQualityOption, MOVIE_ENCODE_QUALITY
		self.qscale = MovieQualityOption(qf, 0, MOVIE_ENCODE_QUALITY, None, None, startCol=2)

		##-----------------------------------------------

		from MoviePreferences import MovieFramerateOption, MOVIE_ENCODE_FRAMERATE
		class LimitedFrameRateOption(tkoptions.EnumOption):
			values = ["24", "25", "30", "50", "60"]
		self.frRateEnumFrame = Tkinter.Frame(self.movOptionsFrame)
		self.frRateEnumOption = LimitedFrameRateOption(self.frRateEnumFrame, 0,
				MOVIE_ENCODE_FRAMERATE, "25", self.updateFpsCB)

		self.frRateEntryFrame = Tkinter.Frame(self.movOptionsFrame)
		self.frRateEntryOption = MovieFramerateOption(self.frRateEntryFrame, 0,
				MOVIE_ENCODE_FRAMERATE, None, self.updateFpsCB, width=3)

		self.chooseFmtCB()

		##-----------------------------------------------

		self.bounceVar = Tkinter.IntVar(self.movOptionsFrame)
		bnc = Tkinter.Checkbutton(self.movOptionsFrame,
								   variable=self.bounceVar,
								   text="Play forward then backward")
		bnc.grid(row=3, column=0, sticky='w')

		##-----------------------------------------------

	def ImageTips(self):
		from chimera import help
		help.display("UsersGuide/print.html#tips")

	def initDirector(self):

		from MovieRecorder import getDirector
		director = getDirector()

		self.director = director

		if director.hasState():
			self.disableInputOptions()
			self._notifyGfxSize("%sx%s" % tuple(director.getGfxWindowSize()))
			self._notifyFrameCount(director.getFrameCount())
			self._notifyMovieTime(director.getFrameCount() / 25)

			if director.isRecording():
				self._notifyRecordingStart()
			else:
				self._notifyRecordingStop()
			if director.isEncoding():
				self._notifyEncodingStart()
		#else:
		#	mr._notifyRecorderReset()

		director.registerUI(self)

	def updateFpsCB(self, event):
		fps = event.get()

		try:
			n = int(fps)
		except ValueError:
			pass
		else:
			if self.director:
				self.director.setFps(n)

	def chooseFmtCB(self, event=None):

		new_fmt = command_formats[self.movieFmtOption.get()]

		self.replaceExt(new_fmt)

		if new_fmt[limited_frame_rate_field]:
			self.showFrmRateEnum()	  # limited frame rates
		else:
			self.showFrmRateEntry()


	def showFrmRateEntry(self):
		try:
			self.frRateEnumFrame.grid_forget()
		except:
			pass

		self.frRateEntryFrame.grid(row=2, column=0, sticky='w')
		self.useFrOption = self.frRateEntryOption
		self.updateFpsCB(self.frRateEntryOption)

	def showFrmRateEnum(self):
		try:
			self.frRateEntryFrame.grid_forget()
		except:
			pass

		self.frRateEnumFrame.grid(row=2, column=0, sticky='w')
		self.useFrOption = self.frRateEnumOption
		self.updateFpsCB(self.frRateEnumOption)

	def replaceExt(self, new_fmt):
		out_file = self.outFileOption.get()
		base, ext = os.path.splitext(out_file)
		self.outFileOption.set(base + '.' + new_fmt[file_suffix_field])

	def renderingCB(self, renderMode):
		from commonOptions import RENDERING_RAYTRACE
		if renderMode == RENDERING_RAYTRACE:
			fmts = raytraceImageFormats
			defaultFmt = defaultRaytraceImageFormat
		else:
			fmts = imageFormats
			defaultFmt = defaultImageFormat
		self.imgFmtOption.set(defaultFmt)

	def resetModeCB(self, opt=None):
		if self.autoResetVar.get():
			if self.keepSrcOption.get():
				mode = RESET_KEEP
			else:
				mode = RESET_CLEAR
		else:
			mode = RESET_NONE
		self.director.setResetMode(mode)

	def getCurrentDimensions(self):
		## get the size...
		geom = self._toplevel.wm_geometry()
		#print "GEOM IS ", geom
		dimensions = geom.split('+', 1)[0].split('-', 1)[0]
		width, height = dimensions.split('x')
		return int(width), int(height)

	def doCustomResize(self, evt=None):
		width = int(self.custResWidthE.get())
		height = int(self.custResHeightE.get())

		new_width = self.director.findNextMacroblock(width)
		new_height = self.director.findNextMacroblock(height)

		self.director.setGfxWindowSize(new_width, new_height)

		self.custResWidthE.delete(0, 'end')
		self.custResWidthE.insert(0, new_width)

		self.custResHeightE.delete(0, 'end')
		self.custResHeightE.insert(0, new_height)


	def getTargetSize(self):
		if self.frmOptionsVar.get():
			if self.movOptionsVar.get():
				return self.both_width, self.both_height
			else:
				return self.frm_width, self.frm_height
		elif self.movOptionsVar.get():
			return self.mov_width, self.mov_height
		else:
			return self.cache_width, self.cache_height

	def showFrmOptionsCB(self):
		self.showOptionsCB('frame')

	def showMovOptionsCB(self):
		self.showOptionsCB('movie')

	def showOptionsCB(self, option):

		if option == 'frame':
			VAR = self.frmOptionsVar
			FRAME = self.frmOptionsFrame
			ROW = FRM_OPTS_ROW
			HEIGHT = self.frm_height
		elif option == 'movie':
			VAR = self.movOptionsVar
			FRAME = self.movOptionsFrame
			ROW = MOV_OPTS_ROW
			HEIGHT = self.mov_height

		current_w, current_h = self.getCurrentDimensions()

		if VAR.get():
			FRAME.grid(row=ROW, column=0, columnspan=3, sticky='nsew')

			self._toplevel.wm_geometry(newGeometry='%sx%s' % (current_w, current_h + HEIGHT))

		else:
			FRAME.grid_forget()
			self._toplevel.wm_geometry(newGeometry='%sx%s' % (current_w, current_h - HEIGHT))

	## Button callbacks


	## The callback for start recording happens in two parts:
	## (1) Code that actually tells the director to start recording, and
	## (2) Code that updates the GUI so it looks like it's recording
	## These are put in seperate functions so they can be called
	## seperately

	def startRecording(self):

		patt = self.inputPatternOption.get()
		input_pattern = ''
		if patt:
			input_pattern = patt
		else:
			input_pattern = DEFAULT_PATTERN % getRandomChars()
			self.inputPatternOption.set(input_pattern)

		img_fmt = self.imgFmtOption.get()
		img_dir = self.inputDirOption.get() or tempfile.gettempdir()
		size = None	 # Use graphics window size
		supersample, raytrace = self.renderingOptions.get(savePrefs=False)

		try:
			self.director.startRecording(img_fmt, img_dir, input_pattern,
										 size, supersample, raytrace)
		except MovieError, what:
			self.showStatus("%s" % what, color="red")
		#else:
		#	self.startRecordingGUIConfig()

	#def startRecordingGUIConfig(self):
	def _notifyRecordingStart(self):
		## <-------code that updates the gui--------->
		#
		self.actionLabel.configure(text="Recording", fg='red')

		## set button states to disabled
		#self.recButton.configure(image=self.pause_img, command=self.stopRecording)
		self.recButton.configure(text="Stop", state='normal', command=self.stopRecording)
		help.register(self.recButton, balloon="Stop capturing frames from graphics window")

		self.clearButton.configure(state='disabled')
		self.encButton.configure(state='disabled')

		self.disableInputOptions()

	def disableInputOptions(self):
		"""helper function to disable all input-file (i.e. frame-related)
		input options"""

		## only do this once - once they start recording anything
		## they can't switch up the format. the encoder will *not*
		## appreciate this.
		self.imgFmtOption.disable()
		self.renderingOptions.disable()
		self.inputDirOption.disable()
		self.inputPatternOption.disable()

	def enableInputOptions(self):
		"""helper function to enable all input-file (i.e. frame-related)
		input options"""

		## the user is now free to choose another input format
		## and/or input directory
		self.inputDirOption.enable()
		self.inputPatternOption.enable()
		self.imgFmtOption.enable()
		self.renderingOptions.enable()

	def stopRecording(self):
		if not self.director.isRecording():
			self.showStatus("Not currently recording")
			return

		try:
			self.director.stopRecording()
		except MovieError, what:
			self.showStatus("%s" % what, color="red")
		#else:
		#	self.stopRecordingGUIConfig()


	def _notifyRecordingStop(self):
		self.showStatus("Stopped recording", blankAfter=20)
		self.actionLabel.configure(text="Stopped", fg='black')

		## restore button states to normal
		#self.recButton.configure(image=self.rec_img, command=self.startRecording)
		self.recButton.configure(text="Record", state='normal', command=self.startRecording)
		help.register(self.recButton, balloon="Start capturing frames from the graphics window")

		self.encButton.configure(state='normal')
		self.clearButton.configure(state='normal')


	def _notifyRecorderReset(self):
		"""this is called from outside the module, probably by the
		directory, to notify me (the gui) that the recorder
		has been reset"""

		self.accum_frames_var.set('0')
		self.accum_secs_var.set('0s.')
		self.clearButton.configure(state='disabled')

		self.enableInputOptions()

		if self.keepSrcOption.get():
			## if you kept the last set of input images
			if self.inputPatternOption.get()[0:9] == 'chimovie_':
				## and didn't change (presumably) the input pattern
				self.inputPatternOption.set(DEFAULT_PATTERN % getRandomChars())
			## else, we won't touch your 'custom' pattern

		self.encButton.configure(text="Make movie", state='disabled',
								 command=self.startEncoding)

		self.recButton.configure(text="Record", state='normal',
								 command=self.startRecording)

		self.actionLabel.configure(text="Stopped", fg='black')

	def resetRecording(self):

		if not self.keepSrcOption.get():
			clr = True
		else:
			clr = False

		try:
			self.director.resetRecorder(clearFrames=clr)
		except MovieError, what:
			self.showStatus("%s" % what, color="red")


	def getFnamePattern(self, pattern, format):
		""" helper function - converts
		chimera-img-%d
		"""
		pass

	def startEncoding(self):

		## Encoder API -
		#
		#   In order to encode a movie, the encoder will need to know
		#   some basic parameters, which will be passed to it in a dictionary
		#   with the following key/value pairs:
		#
		#   OUT_FILE	   where to write the movie output
		#   INPUT_FORMAT   the format the individual frames are in
		#   INPUT_DIR	  the directory where all the individual frames are saved
		#   INPUT_PATTERN  the pattern  of the input frame filenames
		#   INPUT_LAST	 the last frame number to encode (assume 0 is the first)


		## need to figure out what the user wants to do parameter-wise

		param_dict = {'OUT_FILE':	  self.outFileOption.get(),
					  'FPS'	:	   self.useFrOption.get()
					  }

		fmt = self.movieFmtOption.get()
		format = command_formats[fmt]
		param_dict['FORMAT'] = format[file_format_field]
		if format[video_codec_field]:
			param_dict['VIDEO_CODEC'] = format[video_codec_field]
			param_dict['SIZE_RESTRICTION'] = format[size_restriction_field]

		if self.bitrate_mode.get() == 'constant':
			param_dict['BIT_RATE'] = self.bit_rate.get()
		else:
			fmt_name = format[format_name_field]
			qopt = MOVIE_FORMATS[fmt_name]['ffmpeg_quality']
			if qopt:
				param_dict['QUALITY'] = (qopt['option_name'], qopt[self.qscale.get()])

		param_dict['PLAY_FORWARD_AND_BACKWARD'] = self.bounceVar.get()

		try:
			self.director.startEncoding(self.updateEncStatus, **param_dict)
		except MovieError, what:
			self.showStatus("%s" % what, color="red")

	def _notifyEncodingStart(self):
		self.statusLine.configure(textvariable=self.frame_num_var)
		self.actionLabel.configure(text="Encoding", fg='red')
		#self.encButton.configure(image=self.abort_img, command=self.abortEncoding)
		self.encButton.configure(text="Cancel movie", command=self.abortEncoding)
		help.register(self.encButton, balloon="Cancel encoding of movie")

		## establish constraints
		self.clearButton.configure(state='disabled')
		self.recButton.configure(state='disabled')

	def updateEncStatus(self, msg):
		self.frame_num_var.set(msg)

	def _notifyEncodingComplete(self, exit_status):
		"""this is called from outside of this module, probably
		from the director, to notify me (the gui) that encoding
		has completed"""

		#self.actionLabel.configure(text="Stopped", fg='black')
		self.statusLine.configure(textvariable='')

		#self.encButton.configure(image=self.movie_img)
		self.encButton.configure(text="Make movie")
		help.register(self.encButton, balloon="Make a movie from currently captured frames")

		## re-enable buttons
		self.clearButton.configure(state='normal')
		self.recButton.configure(state='normal')
		self.encButton.configure(command=self.startEncoding)

		if exit_status == EXIT_SUCCESS:
			self.actionLabel.configure(text="Successfully encoded!!", fg='red')

		elif  exit_status == EXIT_CANCEL:
			self.actionLabel.configure(text="Canceled encoding!!", fg='red')

		elif exit_status == EXIT_ERROR:
			self.actionLabel.configure(text="Encoding error", fg='red')


	def abortEncoding(self):
		try:
			self.director.stopEncoding()
		except MovieError, what:
			self.showStatus("%s" % what, color="red")
			return

		self.showStatus("Attempt to cancel encoding....")

	def _notifyFrameCount(self, count):
		"""this is called from outside of this module
		to notify me (the gui) that i should update any views
		of how many frames have been recorded"""

		self.accum_frames_var.set(count)

	def _notifyMovieTime(self, t):
		"""this is called from outside of this module
		to notify me (the gui) to update any views of
		the estimated movie time"""

		self.accum_secs_var.set(t)

	def _notifyStatus(self, msg):
		"""this is called from outside this module
		to notify me (the gui) to show some status
		string"""

		self.showStatus(msg)

	def _notifyError(self, err):
		"""this is called from outside this module
		to notify me (the gui) to show some error
		string"""

		chimera.replyobj.error(err)
		self.showStatus(err, color='red')


	def _notifyInfo(self, info):
		"""this is called from outside this module
		to notify me (the gui) to show some info
		string"""

		chimera.replyobj.info(info)

	def _notifyGfxSize(self, size):
		"""this is called from outside this module
		to notify me (the gui) that the graphics window
		size has changed"""
		self.frame_res_var.set(size)

	def showStatus(self, msg, **kw):
		self.status(msg, **kw)

	def updatePreference(self, trigger, funcData=None, option=None):
		'Update a movie preference when modified'
		pref = option._ui.attribute
		from MoviePreferences import MOVIE_ENCODE_FORMAT
		if pref == MOVIE_ENCODE_FORMAT:
			format = command_formats[option.value]
			self.replaceExt(format)

chimera.dialogs.register(MovieRecorderGUI.name, MovieRecorderGUI)
