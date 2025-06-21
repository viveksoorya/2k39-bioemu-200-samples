# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: gui.py 38292 2013-02-14 22:13:32Z pett $

from OpenSave import SaveModeless, OpenModeless
from save import saveSession
from chimera import replyobj, dialogs, triggers
import chimera

thumbnailSizes = {
	'large': 256,
	'medium': 128,
	'small': 64
}
def _saveCB(okayed, dialog):
	if not okayed:
		return
	paths = dialog.getPaths()
	if not paths:
		replyobj.warning("No save file selected; aborting save.\n")
		return
	kw = {}
	from prefs import prefs, INCLUDE_THUMB, THUMB_SIZE
	if dialog.includeThumbVar.get():
		prefs[INCLUDE_THUMB] = True
		thumbSize = dialog.labelToVal[dialog.thumbSize.getvalue()]
		prefs[THUMB_SIZE] = thumbSize
		kw['thumbnailSize'] = thumbnailSizes[thumbSize]
	else:
		prefs[INCLUDE_THUMB] = False
	description = dialog.description.getvalue()
	if description.strip():
		kw['description'] = description
	saveSession(paths[0], **kw)
	chimera.setLastSession(paths[0])
	chimera.setLastSessionDescriptKw(kw, saving=True)

class SaveSessionDialog(SaveModeless):
	name = "Save Session"
	title = "Choose Session Save File"

	def __init__(self):
		SaveModeless.__init__(self, command=_saveCB,
				filters=[("Chimera session", ["*.py"], ".py")],
				historyID="SimpleSession", compressed=True, clientPos='s', clientSticky="ew")
		triggers.addHandler(chimera.CONFIRM_CLOSE_SESSION, self._confirmCloseSes, None)
		triggers.addHandler(chimera.CONFIRM_APPQUIT, self._confirmCloseSes, None)
		triggers.addHandler(chimera.CLOSE_SESSION, self._closeSes, None)
		import SimpleSession
		triggers.addHandler(SimpleSession.SAVE_SESSION, self._saveSes, None)
	
	def fillInUI(self, parent):
		SaveModeless.fillInUI(self, parent)
		import Tkinter, Pmw
		includeThumb, thumbSize, description = self._descriptSettings()

		self.includeThumbVar = Tkinter.IntVar(self.clientArea)
		self.includeThumbVar.set(includeThumb)
		thumbFrame = Tkinter.Frame(self.clientArea)
		thumbFrame.grid(row=0, column=0, sticky='w')
		Tkinter.Checkbutton(thumbFrame, command=self._thumbCB,
			text="Include thumbnail image, ", variable=self.includeThumbVar
			).grid(row=0, column=0, sticky='e')
		self.valToLabel = {}
		self.labelToVal = {}
		for val, pixels in thumbnailSizes.items():
			label = "%s (%dx%d)" % (val, pixels, pixels)
			self.valToLabel[val] = label
			self.labelToVal[label] = val
		self.thumbSize = Pmw.OptionMenu(thumbFrame, items=[self.valToLabel[val]
			for val in ("small", "medium", "large")],
			labelpos="w", label_text="size:", initialitem=self.valToLabel[thumbSize])
		self.thumbSize.grid(row=0, column=1, sticky='w')
		if not self.includeThumbVar.get():
			self.thumbSize.component("menubutton").configure(state='disabled')

		from CGLtk.PeerText import PeerText
		from Notepad.gui import NotepadDialog
		dlg = dialogs.find(NotepadDialog.name)
		if dlg:
			peer = dlg.text.component('text')
		else:
			peer = None
		self.description = Pmw.ScrolledText(self.clientArea, labelpos="nw",
			label_text="Session Description/Notes", text_pyclass=PeerText, text_peer=peer)
		if not peer:
			self.description.setvalue(description)
		if self.description.getvalue().count('\n') < 3:
			self.description.component('text').configure(height=5)
		# prevent Return in text description from invoking Save...
		self.preventDefault(self.description.component('text'))
		self.description.grid(row=1, column=0, columnspan=2, sticky="news")
		self.clientArea.columnconfigure(0, weight=1)
		self.clientArea.columnconfigure(1, weight=1)
		reminder = Tkinter.Label(self.clientArea, text="The Notepad tool (in the Utilities"
			" category) can also be used to edit session description/notes")
		from CGLtk.Font import shrinkFont
		shrinkFont(reminder)
		reminder.grid(row=2, column=0, columnspan=2)

	def updateDescriptionWidgets(self):
		includeThumb, thumbSize, description = self._descriptSettings()
		self.includeThumbVar.set(includeThumb)
		thumbMenu = self.thumbSize.component("menubutton")
		thumbMenu.configure(state="normal")
		self.thumbSize.setvalue(self.valToLabel[thumbSize])
		if not includeThumb:
			thumbMenu.configure(state="disabled")
		self.description.setvalue(description)
		self.description.component('text').edit_modified(False)

	def _confirmCloseSes(self, trigName, myData, messages):
		if self.description.component('text').edit_modified():
			messages.append("You have added a session description without saving a session.")

	def _closeSes(self, *args):
		self.description.setvalue("")
		self.description.component('text').edit_modified(False)
	
	def _saveSes(self, *args):
		self.description.component('text').edit_modified(False)

	def _descriptSettings(self):
		prevKw = chimera._lastSessionDescriptKw
		from prefs import prefs, INCLUDE_THUMB, THUMB_SIZE
		if prevKw is None:
			includeThumb = prefs[INCLUDE_THUMB]
			thumbSize = prefs[THUMB_SIZE]
			description = ""
		else:
			includeThumb = 'thumbnailSize' in prevKw
			if includeThumb:
				for thumbSize, dim in thumbnailSizes.items():
					if dim == prevKw['thumbnailSize']:
						break
			else:
				thumbSize = prefs[THUMB_SIZE]
			description = prevKw.get('description', "")
		return includeThumb, thumbSize, description

	def _thumbCB(self):
		if self.includeThumbVar.get():
			state = "normal"
		else:
			state = "disabled"
		self.thumbSize.component("menubutton").configure(state=state)

dialogs.register(SaveSessionDialog.name, SaveSessionDialog)

def _openCB(okayed, dialog):
	if not okayed:
		return
	for path in dialog.getPaths():
		chimera.openModels.open(path, type="Python")

class OpenSessionDialog(OpenModeless):
	name = "Open Session"
	title = "Choose Previously Saved Chimera Session File"

	def __init__(self):
		self.labelImage = None

		OpenModeless.__init__(self, command=_openCB,
				filters=[("Chimera session", ["*.py"])],
				defaultFilter="Chimera session", addAll=False,
				historyID="SimpleSession", clientPos="s")

		self.triggers.addHandler(self.PATHS_CHANGED, self._updateSesInfo, None)

	def fillInUI(self, parent):
		OpenModeless.fillInUI(self, parent)
		import Tkinter, Pmw
		self.icon = Tkinter.Label(self.clientArea)
		self.icon.grid(row=0, column=0)
		self.icon.grid_remove()

		self.text = Pmw.ScrolledText(self.clientArea, text_relief="flat")
		self.text.grid(row=0, column=1)
		self.text.grid_remove()

	def _updateSesInfo(self, trigName, myData, paths):
		self.clientArea.grid()
		if len(paths) != 1:
			self.clientArea.grid_remove()
			self.icon.grid_remove()
			self.text.grid_remove()
			return
		infoRepr = ""
		with open(paths[0], "r") as ses:
			firstLine = True
			for line in ses:
				if firstLine:
					if line and line[0] == "(":
						infoRepr += line.strip()
					else:
						break
					firstLine = False
				else:
					infoRepr += line.strip()
				if infoRepr[-1] == ")":
					break
		if not infoRepr:
			self.clientArea.grid_remove()
			self.icon.grid_remove()
			self.text.grid_remove()
			return
		info = eval(infoRepr)
		version, imgInfo, descript = info
		if imgInfo:
			mode, size, cmpImgStr = imgInfo
			import zlib
			imgStr = zlib.decompress(cmpImgStr)
			from PIL import Image, ImageTk
			img = Image.fromstring(mode, size, imgStr)
			self.labelImage = ImageTk.PhotoImage(img) # keep a ref due to PIL bug
			self.icon.configure(image=self.labelImage)
			self.icon.grid()
		else:
			self.labelImage = None
			self.icon.grid_remove()

		if descript:
			tkText = self.text.component('text')
			tkText.configure(state='normal')
			self.text.setvalue(descript)
			tkText.configure(height=descript.count('\n')+1,
				width=max([len(l) for l in descript.split('\n')]))
			tkText.configure(state='disabled')
			self.text.grid()
		else:
			self.text.grid_remove()


dialogs.register(OpenSessionDialog.name, OpenSessionDialog)
