# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: gui.py 42541 2024-09-10 00:25:10Z pett $

import chimera
from chimera import tkgui, chimage, CLOSE_SESSION
from chimera.mousemodes import getFuncName, setButtonFunction, addFunction
from chimera.baseDialog import ModelessDialog
from SimpleSession import SAVE_SESSION, BEGIN_RESTORE_SESSION
from Ilabel import contrastWithBG
from PIL import Image
import Tkinter
import Pmw

from Label import Character

class IlabelDialog(ModelessDialog):
	name = "2D Labels/Color Key"
	provideStatus = True
	buttons = ("Delete", "Close")

	LABELS = "Labels"
	ARROWS = "Arrows"
	COLOR_KEY = "Color Key"

	MOUSE_LABEL_TEXT = "Use mouse for label placement"
	MOUSE_ARROW_TEXT = "Use mouse for arrow placement"
	MOUSE_KEY_TEXT = "Use mouse for key placement"

	EmphasisColor = "forest green"

	def __init__(self):
		import os.path
		myDir, junk = os.path.split(__file__)
		addFunction('place text', (self._pickLabel, self._moveLabel,
			None), icon=chimage.get(Image.open(os.path.join(myDir,
						'ilabel.png')), tkgui.app))
		addFunction('place arrow', (self._startOrGrabArrow,
			self._sizeOrMoveArrow, None), icon=chimage.get(
			Image.open(os.path.join(myDir, 'arrow.png')), tkgui.app))
		addFunction('place key', (self._startOrGrabKey,
			self._sizeOrMoveKey, None), icon=chimage.get(
			Image.open(os.path.join(myDir, 'key.png')), tkgui.app))

		ModelessDialog.__init__(self)
		self._handlerIDs = {}
		for trigName, handler in [(SAVE_SESSION, self._saveSession),
				(CLOSE_SESSION, self.destroy),
				(BEGIN_RESTORE_SESSION, self.destroy),
				(chimera.SCENE_TOOL_SAVE, self._saveScene),
				(chimera.SCENE_TOOL_RESTORE, self._restoreScene)]:
			self._handlerIDs[trigName] = chimera.triggers.addHandler(trigName, handler, None)
	
	def __getattr__(self, attrName):
		if attrName == "model":
			import Ilabel
			return Ilabel.LabelsModel()
		elif attrName == "arrowsModel":
			from Arrows import ArrowsModel
			return ArrowsModel()
		raise AttributeError("No such attribute in 2D Labels dialog: %s" % attrName)

	def fillInUI(self, parent):
		top = parent.winfo_toplevel()
		# withdraw() immediately so that we can restore a hidden
		# dialog without it being displayed briefly
		top.withdraw()
		menubar = Tkinter.Menu(top, type="menubar", tearoff=False)
		top.config(menu=menubar)

		self.fileMenu = Tkinter.Menu(menubar)
		menubar.add_cascade(label="File", menu=self.fileMenu)
		self.fileMenu.add_command(label="Write...", command=self._writeFileCB)
		self.fileMenu.add_command(label="Read...", command=self._readFileCB)
		from chimera.tkgui import aquaMenuBar
		aquaMenuBar(menubar, parent, row=0)

		parent.rowconfigure(1, weight=1)
		parent.columnconfigure(0, weight=1)
		# _pageRaisedCB uses mouseModeVar, so define first
		self.mouseLabelingVar = Tkinter.IntVar(parent)
		self.mouseLabelingVar.set(True)
		self.mlLabelVar = Tkinter.StringVar(parent)
		self.mouseModeButton = Tkinter.Checkbutton(parent,
					command=self._mouseFuncCB,
					variable=self.mouseLabelingVar,
					textvariable=self.mlLabelVar)
		self.mouseModeButton.grid(row=2, column=0)
		self.notebook = Pmw.NoteBook(parent,
					raisecommand=self._pageRaisedCB)
		self.notebook.add(self.LABELS, tab_text=self.LABELS)
		self.notebook.add(self.ARROWS, tab_text=self.ARROWS)
		self.notebook.add(self.COLOR_KEY, tab_text=self.COLOR_KEY)
		self.notebook.grid(row=1, column=0, sticky="nsew")
		self._fillLabelsPage(self.notebook.page(self.LABELS))
		self._fillArrowsPage(self.notebook.page(self.ARROWS))
		self._fillColorKeyPage(self.notebook.page(self.COLOR_KEY))
		tkgui.app.rapidAccess.shown = False

	def _fillLabelsPage(self, page):
		page.columnconfigure(0, weight=1)
		page.columnconfigure(1, weight=1)
		page.columnconfigure(2, weight=1)

		row = 0
		from CGLtk.Table import SortableTable
		self.labelTable = SortableTable(page, automultilineHeaders=False)
		self.labelTable.addColumn("Label [(x, y) text]", self._labelListing,
			anchor='w')
		self.labelTable.addColumn("Shown", "shown", format=bool)
		self.labelTable.setData(self.model.labels)
		self.labelTable.launch(browseCmd=self._tableCB, selectMode="single")
		self.labelTable.grid(row=row, column=0, columnspan=3, sticky="nsew")
		page.rowconfigure(row, weight=1)
		row += 1

		f = Tkinter.Frame(page)
		f.grid(row=row, column=0, columnspan=3, sticky='ew')
		Tkinter.Button(f, text="Hide All", pady=0, command=lambda:
			self._hideShowAll("labels", False)).grid(row=0, column=0)
		Tkinter.Button(f, text="Show All", pady=0, command=lambda:
			self._hideShowAll("labels", True)).grid(row=0, column=1)
		f.columnconfigure(0, weight=1)
		f.columnconfigure(1, weight=1)
		row += 1

		self.labelText = Pmw.ScrolledText(page, labelpos='w',
			label_text="Text", text_height=3, text_width=20,
			text_wrap='none', text_state='disabled',
			text_exportselection=False)
		text = self.labelText.component('text')
		text.bind("<<Modified>>", self._textCB)
		text.bind("<<Selection>>", self._updateTextAttrWidgets)
		self.labelText.grid(row=row, column=0,
						sticky='nsew', columnspan=3)
		page.rowconfigure(row, weight=1)
		row += 1

		self.labelSymbolMenu = Pmw.OptionMenu(page, labelpos='w',
			label_text="Insert symbol:", command=self._insertSymbol,
			items=[
				u'\N{GREEK SMALL LETTER ALPHA}',
				u'\N{GREEK SMALL LETTER BETA}',
				u'\N{GREEK SMALL LETTER GAMMA}',
				u'\N{GREEK SMALL LETTER DELTA}',
				u'\N{GREEK SMALL LETTER EPSILON}',
				u'\N{GREEK SMALL LETTER PI}',
				u'\N{GREEK SMALL LETTER PHI}',
				u'\N{GREEK SMALL LETTER CHI}',
				u'\N{GREEK SMALL LETTER PSI}',
				u'\N{GREEK SMALL LETTER OMEGA}',
				u'\N{LEFTWARDS ARROW}',
				u'\N{RIGHTWARDS ARROW}',
				u'\N{LEFT RIGHT ARROW}',
				u'\N{UPWARDS ARROW}',
				u'\N{DOWNWARDS ARROW}',
				u'\N{SUPERSCRIPT TWO}',
				u'\N{SUPERSCRIPT THREE}',
				u'\N{DEGREE SIGN}',
				u'\N{LATIN CAPITAL LETTER A WITH RING ABOVE}',
				"more..."
			])
		self.labelSymbolMenu.grid(row=row, column=0, columnspan=3)

		row += 1

		colorHouse = Pmw.LabeledWidget(page, labelpos='w',
			label_text="Color")
		colorHouse.grid(row=row, column=0, rowspan=3)
		from CGLtk.color.ColorWell import ColorWell
		self.colorWell = ColorWell(colorHouse.interior(),
			color=contrastWithBG(), callback=self._colorCB)
		self.colorWell.grid()

		from chimera.tkoptions import IntOption
		self.labelFontSize = IntOption(page, row, "Font size", 24,
					self._labelChangeCB, startCol=1, min=1,
					attribute="size", width=3)
		row += 1
		self.labelFontStyle = FontStyle(page, row, "Font style",
			oglFont.normal, self._labelChangeCB, startCol=1)
		row += 1
		self.labelFontTypeface = FontTypeface(page, row, "Font typeface",
					FONT_TYPEFACE_VALUES[0],
					self._labelChangeCB, startCol=1)
		row += 1

		# can't get Pmw.Group to work right(!), so...
		from chimera.tkoptions import AttributeHeader
		self.solidBackgroundOption = ah = AttributeHeader(page,
			text="Use solid label background", collapsible=True, collapsed=True,
			bg=page.cget('bg'), relief='flat')
		ah.grid(row=row, column=0, columnspan=3)
		ah.header.config(command=self._labelBGDisplayCB)
		inside = ah.frame
		from chimera.tkoptions import RGBAOption, IntOption, EnumOption
		insideRow = 0
		bg = chimera.viewer.background
		if bg:
			bgColor = tuple(bg.rgba()[:3])
		else:
			bgColor = (0, 0, 0)
		labelBGColor = bgColor + (0.75,)
		self.labelBGColor = RGBAOption(inside, insideRow, "Label background color",
				labelBGColor, self._labelBGColorCB, noneOkay=False)
		insideRow += 1
		self.labelBGMargin = IntOption(inside, insideRow, "Margin around text",
				9, self._labelBGMarginCB, balloon="in pixels")
		insideRow += 1
		self.labelBGOutline = IntOption(inside, insideRow, "Outline around margin",
			0, self._labelBGOutlineCB, balloon="in pixels")
		insideRow += 1
		f = Tkinter.Frame(inside)
		f.grid(row=insideRow, column=0, columnspan=3)
		Tkinter.Button(f, text="Apply", pady=0, command=self._labelBGStandardize
				).grid(row=insideRow, column=0)
		Tkinter.Label(f, text="above background settings to all labels").grid(
				row=insideRow, column=1)
		row += 1

		if self.model.curLabel:
			self.changeToLabel(self.model.curLabel, force=True)

	def _fillArrowsPage(self, page):
		page.columnconfigure(0, weight=1)
		page.columnconfigure(1, weight=1)

		row = 0
		from CGLtk.Table import SortableTable
		self.arrowTable = SortableTable(page)
		self.arrowTable.addColumn("Position", "posString")
		self.arrowTable.addColumn("Color", "color", format=(False, True),
								titleDisplay=False)
		self.arrowTable.addColumn("Shown", "shown", format=bool)
		self.arrowTable.setData(self.arrowsModel.arrows)
		self.arrowTable.launch(browseCmd=self._arrowTableCB,
							selectMode="single")
		self.arrowTable.grid(row=row, column=0, columnspan=2, sticky="nsew")
		page.rowconfigure(row, weight=1)
		row += 1

		f = Tkinter.Frame(page)
		f.grid(row=row, column=0, columnspan=2, sticky='ew')
		Tkinter.Button(f, text="Hide All", pady=0, command=lambda:
			self._hideShowAll("arrows", False)).grid(row=0, column=0)
		Tkinter.Button(f, text="Show All", pady=0, command=lambda:
			self._hideShowAll("arrows", True)).grid(row=0, column=1)
		f.columnconfigure(0, weight=1)
		f.columnconfigure(1, weight=1)
		row += 1

		from chimera.tkoptions import FloatOption, EnumOption
		from Arrows import Arrow
		self.arrowWeightOpt = FloatOption(page, row, "Arrow weight", 1.0,
							lambda o: self._changeArrow(o, "weight"), min=0.0)
		row += 1

		class ArrowheadStyleOption(EnumOption):
			values = Arrow.headStyles
		self.arrowheadStyleOpt = ArrowheadStyleOption(page, row, "Arrowhead style",
			Arrow.HEAD_SOLID, lambda o: self._changeArrow(o, "head"))

	def _fillColorKeyPage(self, page):
		from chimera.tkoptions import IntOption, EnumOption, \
						BooleanOption, RGBAOption
		self._keyPrevConfigured = False
		from ColorKey import getKeyModel
		preexistingKey = getKeyModel(create=False) != None
		self.keyModel = getKeyModel()
		self.keyModel.gui = self
		f = Tkinter.Frame(page)
		f.grid(row=0, columnspan=2)
		km = self.keyModel
		self.numComponents = IntOption(f, 0, "Number of colors/labels",
			len(km.getRgbasAndLabels()), self._componentsCB, min=2, width=2)
		self.componentsFrame = Tkinter.Frame(page)
		self.componentsFrame.grid(row=1, column=0, sticky="nsew",
							columnspan=2)
		page.columnconfigure(0, weight=1)
		self.componentsFrame.columnconfigure(1, weight=1)
		def setKeyAttr(opt, km=km):
			setFunc = getattr(km,
					"set" + opt.attribute[0].upper() + opt.attribute[1:])
			setFunc(opt.get(), fromGui=True)
		class ColorTreatment(EnumOption):
			values = km.colorTreatmentValues
			attribute = "colorTreatment"
		self.keyColorTreatment = ColorTreatment(page, 2,
			"Color range depiction", km.getColorTreatment(), setKeyAttr,
			balloon="Should colors be shown as distinct rectangles"
			" or as a continuous range")
		class LabelSide(EnumOption):
			values = km.labelSideValues
			attribute = "labelSide"
		self.keyLabelSide = LabelSide(page, 3, "Label positions",
			km.getLabelSide(), setKeyAttr, balloon="Position of"
			" labels relative to color key.\nLabels always"
			" positioned adjacent to long side.")
		self.keyLabelColor = RGBAOption(page, 4, "Label color",
			km.getLabelColor(), setKeyAttr, balloon=
			"Label color.  If set to 'No color', use corresponding"
			" key color", noneOkay=True, attribute="labelColor")
		class LabelJustification(EnumOption):
			values = km.justificationValues
		self.keyJustification = LabelJustification(page, 5,
			"Label justification", km.getJustification(),
			setKeyAttr, balloon="Justification of label text"
			" in a vertical key layout.\nHorizontal key labels will"
			" always be center justified.", attribute="justification")
		class NumLabelSpacing(EnumOption):
			values = km.numLabelSpacingValues
			attribute = "numLabelSpacing"
		self.keyNumLabelSpacing = NumLabelSpacing(page, 6, "Numeric"
			" label separation", km.getNumLabelSpacing(),
			self._keyChangeCB, balloon="Controls whether numeric"
			" labels are positioned\nbased on the numeric value"
			" or instead equally spaced.")
		self.keyLabelOffset = IntOption(page, 7, "Label offset",
			km.getLabelOffset(), setKeyAttr, width=3, balloon=
			"Additional offset of labels from color bar, in pixels",
			attribute="labelOffset")
		self.keyFontSize = IntOption(page, 8, "Font size", km.getFontSize(),
			setKeyAttr, width=3, attribute="fontSize")
		self.keyFontStyle = FontStyle(page, 9, "Font style",
			km.getFontStyle(), setKeyAttr, attribute="fontStyle")
		self.keyFontTypeface = FontTypeface(page, 10, "Font typeface",
			km.getFontTypeface(), setKeyAttr, attribute="fontTypeface")
		self.keyBorderColor = RGBAOption(page, 11, "Border color",
			km.getBorderColor(), setKeyAttr, balloon= "Color of border"
			" around color key (not each individual color).\nIf 'no color',"
			" then no border is drawn.", attribute="borderColor")
		self.keyBorderWidth = IntOption(page, 12, "Border width",
			km.getBorderWidth(), setKeyAttr, balloon="in pixels",
			attribute="borderWidth")
		self.keyTickMarks = BooleanOption(page, 13, "Show tick marks",
			km.getTickMarks(), setKeyAttr, balloon="Show tick marks"
			" pointing from key to labels", attribute="tickMarks")
		self.keyTickLength = IntOption(page, 14, "Tick length",
			km.getTickLength(), setKeyAttr, balloon="in pixels",
			attribute="tickLength")
		self.keyTickThickness = IntOption(page, 15, "Tick thickness",
			km.getTickThickness(), setKeyAttr, balloon="in pixels",
			attribute="tickThickness")
		self._componentsCB(self.numComponents, update=False)
		if preexistingKey:
			self.notebook.selectpage(self.COLOR_KEY)

	def destroy(self, *args):
		self.mouseLabelingVar.set(True)
		self.mouseModeButton.invoke()
		for trigName, handlerID in self._handlerIDs.items():
			chimera.triggers.deleteHandler(trigName, handlerID)
		ModelessDialog.destroy(self)

	def map(self, e=None):
		from ColorKey import getKeyModel
		km = getKeyModel(create=False)
		if km and not km.getKeyPosition() and not self._keyPrevConfigured:
			# set key gui to defaults if no existing key
			km.reset(updateGui=True)
		self._keyPrevConfigured = False
		page = self.notebook.getcurselection()
		self._pageRaisedCB(page)

	def unmap(self, e=None):
		self.mouseLabelingVar.set(True)
		self.mouseModeButton.invoke()

	def changeToLabel(self, nextLabel, force=False):
		if nextLabel == self.model.curLabel and not force:
			return
		if self.model.curLabel and not unicode(self.model.curLabel) \
		and self.model.curLabel != nextLabel:
			# remove previous label if empty
			self.removeLabel(self.model.curLabel)
		self.model.changeToLabel(nextLabel)
		self._setTextFromLabel(nextLabel)
		self._updateBackgroundOptions(nextLabel)

	def Delete(self):
		if self.notebook.getcurselection() == self.LABELS:
			self.labelText.clear()
			if not self.model.curLabel:
				self.status("No label to delete", color="red",
								blankAfter=10)
				return
			delIndex = self.model.labels.index(self.model.curLabel)
			self.removeLabel(self.model.curLabel)
			self.labelText.component('text').configure(
							state='disabled')
			if self.model.labels:
				try:
					nextLabel = self.model.labels[delIndex]
				except IndexError:
					nextLabel = self.model.labels[-1]
				self.changeToLabel(nextLabel)
		if self.notebook.getcurselection() == self.ARROWS:
			arrow = self.arrowTable.selected()
			if not arrow:
				self.status("No arrow to delete", color="red",
								blankAfter=10)
				return
			arrows = self.arrowsModel.arrows
			index = arrows.index(arrow)
			if len(arrows) > 1:
				if index == len(arrows) - 1:
					self.arrowTable.select(arrows[index-1])
				else:
					self.arrowTable.select(arrows[index+1])
			self.arrowsModel.removeArrow(arrow)
			self.arrowTable.setData(self.arrowsModel.arrows)
		else:
			self.keyModel.setKeyPosition(None, fromGui=True)

	def Help(self):
		helpLoc = "ContributedSoftware/2dlabels/2dlabels.html"
		if self.notebook.getcurselection() == self.COLOR_KEY:
			helpLoc += "#colorkey"
		chimera.help.display(helpLoc)

	def keyConfigure(self, data, pageChange=True, fromGui=False):
		self._keyPrevConfigured = True
		self.keyModel.setRgbasAndLabels(data, fromGui=fromGui)
		if pageChange:
			self.notebook.selectpage(self.COLOR_KEY)

	def makeChar(self, char, model):
		attrs = {}
		try:
			attrs['rgba'] = self.colorWell.rgba
		except AttributeError: # multi or None
			if model:
				attrs['rgba'] = model.rgba
		size = self.labelFontSize.get()
		if size is not None:
			attrs['size'] = size
		style = self.labelFontStyle.get()
		if style is not None:
			attrs['style'] = style
		fontName = self.labelFontTypeface.get()
		if fontName is not None:
			attrs['fontName'] = fontName
		return Character(char, **attrs)

	def newLabel(self, pos):
		label = self.model.newLabel(pos)
		self.labelTable.setData(self.model.labels)
		self.status("Mouse drag to reposition label",
						color=self.EmphasisColor)
		return label

	def removeLabel(self, label):
		self.model.removeLabel(label)
		self.labelTable.setData(self.model.labels)
		if self.model.curLabel is not None:
			self.labelTable.select(self.model.curLabel)

	def reverseKey(self):
		data = zip([w.rgba for w in self.wells],
				[l.variable.get() for l in self.labels])
		data.reverse()
		self.keyConfigure(data)

	def setLabelFromText(self):
		curLabel = self.model.curLabel
		text = self.labelText.component('text')
		# delete parts of label not in text...
		#
		# newlines first...
		while len(curLabel.lines) > 1:
			for i, line in enumerate(curLabel.lines[:-1]):
				if not text.tag_ranges(id(line)):
					curLabel.lines[i+1][:0] = line
					del curLabel.lines[i]
					break
			else:
				break
		# characters...
		for line in curLabel.lines:
			for c in line[:]:
				if not text.tag_ranges(id(c)):
					line.remove(c)
		
		# get new parts of text into label
		model = None
		targets = []
		lines = curLabel.lines
		for line in lines:
			targets.extend([id(c) for c in line])
			if not model and line:
				model = line[0]
			if line is not lines[-1]:
				targets.append(id(line))
		contents = self.labelText.get()[:-1] # drop trailing newline

		if targets:
			target = targets.pop(0)
		else:
			target = None

		textLine = 1
		textIndex = -1
		curLine = lines[0]
		for c in contents:
			textIndex += 1
			if str(target) in text.tag_names("%d.%d"
						% (textLine, textIndex)):
				if targets:
					target = targets.pop(0)
				else:
					target = None
				if c == '\n':
					textLine += 1
					textIndex = -1
					curLine = lines[[id(l)
							for l in lines].index(
							id(curLine))+1]
				elif curLine:
					model = curLine[textIndex]
			elif c == '\n':
				insertLine = curLine[0:textIndex]
				lines.insert(textLine-1, insertLine)
				del curLine[0:textIndex]
				text.tag_add(id(insertLine), "%d.%d"
							% (textLine, textIndex))
				textLine += 1
				textIndex = -1
			else:
				labelChar = self.makeChar(c, model)
				curLine.insert(textIndex, labelChar)
				text.tag_add(id(labelChar), "%d.%d"
							% (textLine, textIndex))
		self.model.setMajorChange()

	def updateGUI(self, source="gui"):
		curLabel = self.model.curLabel
		if source == "gui":
			if curLabel:
				self.setLabelFromText()
		else:
			self._setTextFromLabel(curLabel)
		self.labelTable.setData(self.model.labels)
		if curLabel:
			self.labelTable.select(curLabel)
		self._updateTextAttrWidgets()
		if source != "gui":
			self.arrowTable.setData(self.arrowsModel.arrows)
		self._updateArrowAttrWidgets()

	def _arrowTableCB(self, sel):
		if sel:
			self.arrowWeightOpt.set(sel.weight)
			self.arrowheadStyleOpt.set(sel.head)

	def _changeArrow(self, opt, attrName):
		arrow = self.arrowTable.selected()
		if arrow:
			setattr(arrow, attrName, opt.get())
		else:
			self.status("No arrow selected in table")

	def _colorCB(self, color):
		curLabel = self.model.curLabel
		if not curLabel:
			self.status("No label to color", color='red')
			return
		self.model.setMajorChange()
		for c in self._selChars():
			c.rgba = color

	def _componentsCB(self, opt, update=True):
		cf = self.componentsFrame
		if hasattr(self, 'wells'):
			for well in self.wells:
				well.grid_forget()
				well.destroy()
			for label in self.labels:
				label.frame.grid_forget()
			self.reverseButton.grid_forget()
			self.reverseButton.destroy()
		else:
			Tkinter.Label(cf, text="Colors").grid(row=0)
			Tkinter.Label(cf, text="Labels").grid(row=0, column=1)
		if isinstance(opt, int):
			numComponents = opt
			self.numComponents.set(opt)
		else:
			numComponents = opt.get()
		if numComponents > 0:
			wellSize = min(38, int( (7 * 38) / numComponents ))
		from CGLtk.color.ColorWell import ColorWell
		self.wells = []
		self.labels = []
		from CGLtk import Hybrid
		colorsAndLabels = [("white", "")] * numComponents
		if not update:
			rgbasAndLabels = self.keyModel.getRgbasAndLabels()
			if len(rgbasAndLabels) == numComponents:
				colorsAndLabels = rgbasAndLabels
		for i in range(numComponents):
			color, label = colorsAndLabels[i]
			well = ColorWell(cf, width=wellSize, height=wellSize,
				callback=self._setKeyModelComponents, color=color)
			well.grid(row=i+1)
			self.wells.append(well)
			label = Hybrid.Entry(cf, "", 10, initial=label)
			label.variable.add_callback(self._keyTypingCB)
			label.frame.grid(row=i+1, column=1, sticky='ew')
			self.labels.append(label)
		self.reverseButton = Tkinter.Button(cf, command=self.reverseKey,
				text="Reverse ordering of above", pady=0)
		self.reverseButton.grid(row=numComponents+1, column=0,
								columnspan=2)
		self.notebook.setnaturalsize()
		if update:
			self._setKeyModelComponents()

	def _eventToPos(self, viewer, event, offset = (0, 0)):
		w, h = viewer.windowSize
		s = viewer.pixelScale
		return (s*event.x - offset[0]) / float(w), \
				(h - s*event.y - offset[1]) / float(h)
		
	def _handleTextChange(self):
		self.updateGUI()
		self.labelText.edit_modified(False)

	def _hideShowAll(self, target, show):
		if target == "labels":
			items = self.model.labels
			table = self.labelTable
		else:
			items = self.arrowsModel.arrows
			table = self.arrowTable
		for item in items:
			item.shown = show
		table.refresh()

	def _insertSymbol(self, item):
		if len(item) > 1:
			from chimera import help
			help.display("ContributedSoftware/2dlabels/symbols.html")
			return
		if not self.model.labels:
			self.status("No labels have been created yet", color="red")
			return
		if not self.labelTable.selected():
			self.status("No labels active", color="red")
		self.labelText.insert("insert", item)
		self.setLabelFromText()

	def _keyChangeCB(self, *args):
		self.keyModel.setMajorChange()

	def _keyTypingCB(self, fromAfter=False):
		# wait for a pause in typing before updating key...
		if fromAfter:
			self._typingHandler = None
			self._setKeyModelComponents()
			return
		handle = getattr(self, '_typingHandler', None)
		if handle:
			self.componentsFrame.after_cancel(handle)
		self._typingHandler = self.componentsFrame.after(500,
				lambda: self._keyTypingCB(fromAfter=True))

	def _labelBGColorCB(self, opt):
		curLabel = self.model.curLabel
		if curLabel:
			curLabel.background = self.labelBGColor.get()
			self.model.setMajorChange()

	def _labelBGDisplayCB(self):
		curLabel = self.model.curLabel
		bgOpt = self.solidBackgroundOption
		if bgOpt.expandedVar.get():
			bgOpt.configure(relief='solid', bd=2)
			bgOpt.frame.grid(**bgOpt.frameGridKw)
			if curLabel:
				curLabel.background = self.labelBGColor.get()
				curLabel.margin = self.labelBGMargin.get()
				curLabel.outline = self.labelBGOutline.get()
		else:
			bgOpt.configure(relief='flat', bd=0)
			bgOpt.frame.grid_forget()
			if curLabel:
				curLabel.background = None
		self.model.setMajorChange()

	def _labelBGMarginCB(self, opt):
		curLabel = self.model.curLabel
		if curLabel:
			curLabel.margin = self.labelBGMargin.get()
			self.model.setMajorChange()

	def _labelBGOutlineCB(self, opt):
		curLabel = self.model.curLabel
		if curLabel:
			curLabel.outline = self.labelBGOutline.get()
			self.model.setMajorChange()

	def _labelBGStandardize(self):
		if len(self.model.labels) < 2:
			return

		curLabel = self.model.curLabel
		for label in self.model.labels:
			label.background = curLabel.background
			label.margin = curLabel.margin
			label.outline = curLabel.outline
		self.model.setMajorChange()

	def _labelChangeCB(self, option):
		curLabel = self.model.curLabel
		self.model.setMajorChange()
		val = option.get()
		attrName = option.attribute
		for c in self._selChars():
			setattr(c, attrName, val)

	def _labelListing(self, label):
		text = unicode(label)
		if '\n' in text:
			newline = text.index('\n')
			text= text[:newline] + "..."
		if not text:
			text = "<empty>"
		return "(%.2f, %.2f) %s" % (label.pos[0], label.pos[1], text)

	def _mouseFuncCB(self):
		self.status("")
		if not self.mouseLabelingVar.get():
			if hasattr(self, "_prevMouse"):
				setButtonFunction("1", (), self._prevMouse)
				delattr(self, "_prevMouse")
		elif self.mlLabelVar.get() == self.MOUSE_LABEL_TEXT:
			if not hasattr(self, "_prevMouse"):
				self._prevMouse = getFuncName("1", ())
			setButtonFunction("1", (), "place text")
		elif self.mlLabelVar.get() == self.MOUSE_ARROW_TEXT:
			if not hasattr(self, "_prevMouse"):
				self._prevMouse = getFuncName("1", ())
			setButtonFunction("1", (), "place arrow")
		else:
			if not hasattr(self, "_prevMouse"):
				self._prevMouse = getFuncName("1", ())
			setButtonFunction("1", (), "place key")

	def _moveLabel(self, viewer, event):
		pos = self._eventToPos(viewer, event, self._moveOffset)
		self.model.moveLabel(pos)
		curLabel = self.model.curLabel
		self.labelTable.setData(self.model.labels)
		self.labelTable.select(curLabel)
		
	def _pageRaisedCB(self, pageName):
		if pageName == self.LABELS:
			pageItem = self.MOUSE_LABEL_TEXT
			if not self.model.labels:
				self.status("Click mouse button 1 in graphics\n"
						"window to place first label",
						color=self.EmphasisColor)
			for index in range(0, self.fileMenu.index('end')+1):
				self.fileMenu.entryconfigure(index, state='normal')
		elif pageName == self.ARROWS:
			pageItem = self.MOUSE_ARROW_TEXT
			self.status("Drag mouse to position arrow",
						color=self.EmphasisColor)
			for index in range(0, self.fileMenu.index('end')+1):
				self.fileMenu.entryconfigure(index, state='normal')
		else:
			pageItem = self.MOUSE_KEY_TEXT
			self.status("Drag mouse to position/size key",
						color=self.EmphasisColor)
			for index in range(0, self.fileMenu.index('end')+1):
				self.fileMenu.entryconfigure(index, state='disabled')
		self.mlLabelVar.set(pageItem)
		# just setting the var doesn't cause the callback, and
		# yet using invoke() toggles the var, so set it _opposite_
		# to what's desired before calling invoke()
		self.mouseLabelingVar.set(False)
		self.mouseModeButton.invoke()
		
	def _pickLabel(self, viewer, event):
		w, h = viewer.windowSize
		pos = self._eventToPos(viewer, event)
		label, self._moveOffset = self.model.pickLabel(pos, w, h)
		if label is None:
			label = self.newLabel(pos)
			self._moveOffset = (0, 0)
		self.changeToLabel(label)
		self.labelText.component('text').focus_set()

	def _readFile(self, okayed, dialog):
		if not okayed:
			return
		from Ilabel import readFiles
		readFiles(dialog.getPaths(), clear=dialog.deleteExistingVar.get())

	def _readFileCB(self):
		if not hasattr(self, "_readFileDialog"):
			self._readFileDialog = ReadFileDialog(
				command=self._readFile, clientPos='s')
		self._readFileDialog.enter()

	def _restoreScene(self, trigName, myData, scene):
		self._restoreSession(scene.tool_settings.get('2D Labels (gui)', None))

	def _restoreSession(self, info):
		if info is None:
			# scene without GUI showing
			self.Close()
			return
		if info.get("dialog shown", True):
			self.enter()
		if info["sel ranges"]:
			self.labelText.tag_add("sel", *info["sel ranges"])
		self._updateTextAttrWidgets()
		self.labelText.edit_modified(False)
		if 'arrows' in info:
			self.arrowsModel.restore(info['arrows'])
			self.arrowTable.setData(self.arrowsModel.arrows)
		if "key position" not in info:
			from ColorKey import getKeyModel
			km = getKeyModel(create=False)
			if km and km.getKeyPosition():
				self._setKeyRgbasAndLabels(km.getRgbasAndLabels())
			else:
				self.notebook.selectpage(self.LABELS)
			if info["mouse func"] == "normal":
				self.mouseLabelingVar.set(True)
				self.mouseModeButton.invoke()
			return
		self.keyModel.setKeyPosition(info["key position"], fromGui=True)
		self.keyModel.setColorTreatment(info["color depiction"], fromGui=True)
		self.keyModel.setLabelSide(info["label positions"], fromGui=True)
		self.keyModel.setLabelColor(info["label color"], fromGui=True)
		self.keyModel.setJustification(info["label justification"],
			fromGui=True)
		self.keyModel.setLabelOffset(info["label offset"], fromGui=True)
		if "label spacing" in info:
			self.keyModel.setNumLabelSpacing(info["label spacing"],
				fromGui=True)
		self.keyModel.setFontSize(info["font size"], fromGui=True)
		self.keyModel.setFontStyle(info["font typeface"], fromGui=True)
		if "font name" in info:
			self.keyModel.setFontTypeface(info["font name"], fromGui=True)
		self.keyModel.setBorderColor(info["border color"], fromGui=True)
		self.keyModel.setBorderWidth(info["border width"], fromGui=True)
		self.keyModel.setTickMarks(info["show ticks"], fromGui=True)
		self.keyModel.setTickLength(info.get("tick length", 10), fromGui=True)
		self.keyModel.setTickThickness(info.get("tick thickness", 4),
			fromGui=True)
		self.keyConfigure(info["colors/labels"])
		if info["key position"]:
			self.notebook.selectpage(self.COLOR_KEY)
		else:
			self.notebook.selectpage(self.LABELS)
		if info["mouse func"] == "normal":
			self.mouseLabelingVar.set(True)
			self.mouseModeButton.invoke()

	def _saveScene(self, trigName, myData, scene):
		scene.tool_settings['2D Labels (gui)'] = self._sessionInfo()

	def _saveSession(self, triggerName, myData, sessionFile):
		print>>sessionFile, """
def restore2DLabelDialog(info):
	from chimera.dialogs import find
	from Ilabel.gui import IlabelDialog
	dlg = find(IlabelDialog.name)
	if dlg is not None:
		dlg.destroy()
	dlg = find(IlabelDialog.name, create=True)
	dlg._restoreSession(info)

import SimpleSession
SimpleSession.registerAfterModelsCB(restore2DLabelDialog, %s)

""" % repr(self._sessionInfo())

	def _selChars(self):
		chars = []
		curLabel = self.model.curLabel
		if curLabel:
			sel = self.labelText.tag_ranges("sel")
			if sel:
				sline, schar = [int(x)
					for x in str(sel[0]).split('.')]
				eline, echar = [int(x)
					for x in str(sel[1]).split('.')]
				sline -= 1
				eline -= 1
				for li, line in enumerate(curLabel.lines):
					if li < sline:
						continue
					if li > eline:
						break
					if sline == eline:
						chars.extend(line[schar:echar])
					elif li == sline:
						chars.extend(line[schar:])
					elif li == eline:
						chars.extend(line[:echar])
					else:
						chars.extend(line)
			else:
				for l in curLabel.lines:
					chars.extend(l)
		return chars

	def _sessionInfo(self):
		info = {}
		info["sel ranges"] = tuple([str(tr)
				for tr in self.labelText.tag_ranges("sel")])
		if self.mouseLabelingVar.get():
			info["mouse func"] = "labeling"
		else:
			info["mouse func"] = "normal"
		info["dialog shown"] = self.uiMaster().winfo_ismapped()
		return info

	for attrName in ("borderColor", "borderWidth", "colorTreatment", "fontSize",
			"fontStyle", "fontTypeface", "justification", "labelColor",
			"labelOffset", "labelPos", "labelSide", "numLabelSpacing", "tickLength",
			"tickMarks", "tickThickness"):
		capped = attrName[0].upper() + attrName[1:]
		exec("def _setKey" + capped + "(self, val): "
			+ "self.key" + capped + ".set(val)")

	def _setKeyModelComponents(self, opt=None):
		self.keyModel.setRgbasAndLabels(zip([w.rgba for w in self.wells],
			[l.variable.get() for l in self.labels]), fromGui=True)

	def _setKeyRgbasAndLabels(self, ral):
		if len(self.wells) != len(ral):
			self.numComponents.set(len(ral))
			self._componentsCB(len(ral), update=False)
		for well, label, rl in zip(self.wells, self.labels, ral):
			rgba, text = rl
			well.showColor(rgba, doCallback=False)
			label.variable.set(text, invoke_callbacks=False)
		if self.notebook.getcurselection() != self.COLOR_KEY:
			self.notebook.selectpage(self.COLOR_KEY)

	def _setTextFromLabel(self, label):
		if not label:
			newText = ''
		else:
			newText = unicode(label)
		self.labelText.component('text').configure(state='normal')
		self.labelTable.select(label)
		self.labelText.settext(newText)
		if not label:
			return
		text = self.labelText.component('text')
		lineIndex = 1
		for line in self.model.curLabel.lines:
			charIndex = 0
			for c in line:
				text.tag_add(id(c),
					"%d.%d" % (lineIndex, charIndex))
				charIndex += 1
			text.tag_add(id(line), "%d.%d" % (lineIndex, charIndex))
			lineIndex += 1

	def _sizeOrMoveArrow(self, viewer, event):
		pos = self._eventToPos(viewer, event, self._arrowDeltaPos)
		if self.curArrow:
			if self._arrowPart == self.curArrow.HEAD:
				if pos != self.curArrow.start:
					self.curArrow.end = pos
					self.arrowsModel.setMajorChange()
					self.arrowTable.refresh()
			elif self._arrowPart == self.curArrow.TAIL:
				if pos != self.curArrow.end:
					self.curArrow.start = pos
					self.arrowsModel.setMajorChange()
					self.arrowTable.refresh()
			else:
				start, end = self.curArrow.start, self.curArrow.end
				mid = ((start[0]+end[0])/2.0, (start[1]+end[1])/2.0)
				delta = (pos[0]-mid[0], pos[1]-mid[1])
				if delta:
					self.curArrow.start = (start[0]+delta[0], start[1]+delta[1])
					self.curArrow.end = (end[0]+delta[0], end[1]+delta[1])
					self.arrowsModel.setMajorChange()
					self.arrowTable.refresh()

		elif pos != self.arrowStart:
			from Arrows import Arrow
			self.curArrow = self.arrowsModel.addArrow(self.arrowStart, pos,
				color=contrastWithBG(), weight=self.arrowWeightOpt.get(),
				head=self.arrowheadStyleOpt.get())
			self.arrowTable.setData(self.arrowsModel.arrows)
			self.arrowTable.select(self.curArrow)

	def _sizeOrMoveKey(self, viewer, event):
		pos = self._eventToPos(viewer, event)
		kp = self.keyModel.getKeyPosition()
		if self.grabPos:
			deltas = [pos[axis] - self.grabPos[axis]
							for axis in [0, 1]]
			newKp = []
			for old in kp:
				newKp.append((old[0] + deltas[0], old[1] + deltas[1]))
			self.grabPos = pos
		elif len(kp) == 1:
			newKp = kp + [pos]
		else:
			newKp = kp[:]
			newKp[1] = pos
		self.keyModel.setKeyPosition(newKp, fromGui=True)
		
	def _startOrGrabArrow(self, viewer, event):
		w, h = viewer.windowSize
		pos = self._eventToPos(viewer, event)
		self.curArrow, self._arrowPart, self._arrowDeltaPos = \
				self.arrowsModel.pickArrow(pos, w, h)
		if self.curArrow is None:
			self.arrowStart = pos
		else:
			self.arrowTable.select(self.curArrow)
			self._updateArrowAttrWidgets()

	def _startOrGrabKey(self, viewer, event):
		pos = self._eventToPos(viewer, event)
		kp = self.keyModel.getKeyPosition()
		if kp and len(kp) == 2:
			# possible grab;
			# see if in middle third of long side...
			p1, p2 = kp
			x1, y1 = p1
			x2, y2 = p2
			if abs(x2 - x1) < abs(y2 - y1):
				longAxis = 1
				ymin = min(y2, y1)
				ymax = max(y2, y1)
				b1 = (2* ymin + ymax) / 3.0
				b2 = (2* ymax + ymin) / 3.0
				o1 = min(x1, x2)
				o2 = max(x1, x2)
			else:
				longAxis = 0
				xmin = min(x2, x1)
				xmax = max(x2, x1)
				b1 = (2* xmin + xmax) / 3.0
				b2 = (2* xmax + xmin) / 3.0
				o1 = min(y1, y2)
				o2 = max(y1, y2)
			if b1 < pos[longAxis] < b2 \
			and o1 < pos[1-longAxis] < o2:
				self.grabPos = pos
				return
		self.grabPos = None
		self.keyModel.setKeyPosition([pos])
		self.status("Grab middle of key to reposition",
						color=self.EmphasisColor)

	def _tableCB(self, sel):
		if not sel:
			return
		self.changeToLabel(sel)

	def _textCB(self, e):
		text = self.labelText.component('text')
		if not text.tk.call((text._w, 'edit', 'modified')):
		#if not text.edit_modified():
			return
		# this callback can happen _before_ the change
		# actually occurs, so do the processing after idle
		text.after_idle(self._handleTextChange)

	def _updateArrowAttrWidgets(self):
		self._arrowTableCB(self.arrowTable.selected())

	def _updateBackgroundOptions(self, label):
		bgOpt = self.solidBackgroundOption
		if bool(label.background) != bgOpt.expandedVar.get():
			# can't call invoke(), need parent callback
			bgOpt.expandedVar.set(bool(label.background))
			bgOpt.collapseChange()
			if label.background:
				bgOpt.configure(relief='solid', bd=2)
			else:
				bgOpt.configure(relief='flat', bd=0)
		if label.background:
			self.labelBGColor.set(label.background)
			self.labelBGMargin.set(label.margin)
			self.labelBGOutline.set(label.outline)

	def _updateTextAttrWidgets(self, e=None):
		rgba = None
		multiple = False
		for c in self._selChars():
			if rgba is None:
				rgba = c.rgba
			elif rgba != c.rgba:
				multiple = True
				break
		if rgba is not None:
			self.colorWell.showColor(rgba, multiple=multiple,
							doCallback=False)
			self.labelFontSize.display(self._selChars())
			self.labelFontStyle.display(self._selChars())
			self.labelFontTypeface.display(self._selChars())
		if self.model.curLabel:
			self._updateBackgroundOptions(self.model.curLabel)

	def _writeFile(self, okayed, dialog):
		if not okayed:
			return
		from Ilabel import writeFile
		writeFile(dialog.getPaths()[0])

	def _writeFileCB(self):
		if not hasattr(self, "_writeFileDialog"):
			from OpenSave import SaveModeless
			self._writeFileDialog = SaveModeless(command=self._writeFile,
				title="Write 2D Labels Info")
		self._writeFileDialog.enter()

from chimera.tkoptions import SymbolicEnumOption
oglFont = chimera.OGLFont
from Ilabel import FONT_STYLE_LABELS, FONT_STYLE_VALUES
class FontStyle(SymbolicEnumOption):
	attribute = "style"
	labels = FONT_STYLE_LABELS
	values = FONT_STYLE_VALUES

from Ilabel import FONT_TYPEFACE_LABELS, FONT_TYPEFACE_VALUES
class FontTypeface(SymbolicEnumOption):
	attribute = "fontName"
	labels = FONT_TYPEFACE_LABELS
	values = FONT_TYPEFACE_VALUES

from OpenSave import OpenModeless
class ReadFileDialog(OpenModeless):
	title="Read 2D Labels Info"

	def fillInUI(self, parent):
		OpenModeless.fillInUI(self, parent)
		self.deleteExistingVar = Tkinter.IntVar(parent)
		self.deleteExistingVar.set(False)
		Tkinter.Checkbutton(self.clientArea, variable=self.deleteExistingVar,
			text="Delete existing labels").grid()
		
from chimera import dialogs
dialogs.register(IlabelDialog.name, IlabelDialog)
