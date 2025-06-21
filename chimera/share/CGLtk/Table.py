import Tkinter
import Pmw

class ScrolledTable(Pmw.MegaWidget):
	"""A scrollable table widget that supports titles that stay put.
	
	The widget should be used like a Frame, with sub-widgets added
	using the Grid geometry manager.  Do *not* set the column or
	row weights, unless you like unpredictable results."""

	def __init__(self, parent=None, **kw):

		# Define the megawidget options.
		INITOPT = Pmw.INITOPT
		optiondefs = (
			('horizfraction',  0.05,         INITOPT),
			('hscrollmode',    'dynamic',    INITOPT),
			('labelmargin',    0,            INITOPT),
			('labelpos',       None,         INITOPT),
			('scrollmargin',   2,            INITOPT),
			('vertfraction',   0.05,         INITOPT),
			('vscrollmode',    'dynamic',    INITOPT),
		)
		self.defineoptions(kw, optiondefs,
				dynamicGroups=('Columntitle', 'Rowtitle'))

		# Initialise the base class (after defining the options).
		Pmw.MegaWidget.__init__(self, parent)

		# Create the components.
		interior = Pmw.MegaWidget.interior(self)

		# Create the vertical scrollbar
		self._vsb = self.createcomponent('vertscrollbar',
			(), 'Scrollbar',
			Tkinter.Scrollbar, (interior,),
			orient='vertical', command=self._vScroll
		)
		if self['vscrollmode'] != 'none':
			interior.columnconfigure(4,
						minsize=self['scrollmargin'])
			self._vsb.grid(column=5, row=3, sticky='wns')

		# Create the horizontal scrollbar
		self._hsb = self.createcomponent('horizscrollbar',
			(), 'Scrollbar',
			Tkinter.Scrollbar, (interior,),
			orient='horizontal', command=self._hScroll
		)
		if self['hscrollmode'] != 'none':
			interior.rowconfigure(4, minsize=self['scrollmargin'])
			self._hsb.grid(column=3, row=5, sticky='new')

		# Create the column clipper
		self._colClipper = self.createcomponent('columnclipper',
			(), 'Titleclipper',
			Tkinter.Frame, (interior,), bd=0)
		self._colClipper.grid(column=3, row=2, sticky='w')

		# Create the column frame
		self._colFrame = self.createcomponent('columnframe',
			(), 'Titleframe',
			Tkinter.Frame, (self._colClipper,), bd=0)
		self._colFrame.place(x=0, y=0)

		# Create the row clipper
		self._rowClipper = self.createcomponent('rowclipper',
			(), 'Titleclipper',
			Tkinter.Frame, (interior,), bd=0)
		self._rowClipper.grid(column=2, row=3, sticky='n')

		# Create the row frame
		self._rowFrame = self.createcomponent('rowframe',
			(), 'Titleframe',
			Tkinter.Frame, (self._rowClipper,), bd=0)
		self._rowFrame.place(x=0, y=0)

		# Create the main content clipper
		self._clipper = self.createcomponent('clipper',
			(), None,
			Tkinter.Frame, (interior,), bd=0)
		self._clipper.grid(column=3, row=3, sticky='nsew')

		# Create the main content frame
		self._frame = self.createcomponent('frame',
			(), None,
			Tkinter.Frame, (self._clipper,), bd=0)
		self._frame.grid(column=1, row=1, sticky='nsew')

		interior.columnconfigure(3, weight=1)
		interior.rowconfigure(3, weight=1)

		self.createlabel(interior, childCols=4, childRows=4)

		self._colTitles = {}
		self._rowTitles = {}

		if self['hscrollmode'] == 'dynamic' \
		and self['vscrollmode'] == 'dynamic':
			self.__config = self._configureXY
		elif self['vscrollmode'] == 'dynamic':
			self.__config = self._configureY
		elif self['hscrollmode'] == 'dynamic':
			self.__config = self._configureX
		else:
			self.__config = self._configureFixed
		self._reqwidth = 0
		self._reqheight = 0

		self._clipper.bind('<Configure>', self._configure)
		self._frame.bind('<Configure>', self._configureContent)

		self.initialiseoptions(ScrolledTable)

	def columnTitles(self, withKw=0):
		"""Return the column titles (a dictionary of column=>title).
		
		If 'withKw', the dictionary value is a 2-tuple of the title
		and the keyword dictionary used for title-widget construction.
		Also, in this case textvariable titles haven't been massaged
		into strings."""

		return self._titles(self._colTitles, withKw)

	def setColumnTitle(self, column, title, **kw):
		"Set the title for a column (column index starts at 0)."
		self._setTitle(self._colTitles, column, title, kw)
		if not title:
			self._frame.columnconfigure(column, minsize=0)

	def rowTitles(self, withKw=0):
		"""Return the row titles (a dictionary of row=>title).
		
		If 'withKw', the dictionary value is a 2-tuple of the title
		and the keyword dictionary used for title-widget construction.
		Also, in this case textvariable titles haven't been massaged
		into strings."""

		return self._titles(self._rowTitles, withKw)

	def setRowTitle(self, row, title, **kw):
		"Set the title for a row (row index starts at 0)."
		self._setTitle(self._rowTitles, row, title, kw)
		if not title:
			self._frame.rowconfigure(row, minsize=0)

	def showTitles(self):
		"Show row/column titles of an empty table"
		self._updateColumnLabels(force=1)
		self._updateRowLabels(force=1)

	def _setTitle(self, dict, key, value, kw):
		if value:
			dict[key] = (value, kw)
		else:
			try:
				del dict[key]
			except KeyError:
				pass

	def _configureContent(self, event):
		if event.width == self._reqwidth \
		and event.height == self._reqheight:
			return
		self._reqwidth = event.width
		self._reqheight = event.height
		self._configure(event, reuse=0)

	def _configure(self, event, reuse=1):
		reqWidth = self._frame.winfo_reqwidth()
		reqHeight = self._frame.winfo_reqheight()
		w, h = self.__config(reqWidth, reqHeight)
		if self['vscrollmode'] != 'none':
			vStart = self._vsb.get()[-2]
			self._height = float(reqHeight)
			self._vScale = h / self._height
			self._vScroll('moveto', str(vStart))
		if self['hscrollmode'] != 'none':
			hStart = self._hsb.get()[-2]
			self._width = float(reqWidth)
			self._hScale = w / self._width
			self._hScroll('moveto', str(hStart))
		self._updateColumnLabels(force=1, reuse=reuse)
		self._updateRowLabels(force=1, reuse=reuse)

	def _configureXY(self, reqWidth, reqHeight):
		# both scrollbars are automatic

		# never map/unmap more than one scrollbar at a time in
		# this routine.  Since each mapping/unmapping will cause
		# a Configure callback, we want to have the 'ismapped'
		# states accurately reflect the Configure event fields.
		# This won't be true if we do multiple mappings between
		# Configure events.
		clipW = maxW = self._clipper.winfo_width()
		clipH = maxH = self._clipper.winfo_height()
		if self._vsb.winfo_ismapped():
			maxW = maxW + self._vsb.winfo_reqwidth()
		if self._hsb.winfo_ismapped():
			maxH = maxH + self._hsb.winfo_reqheight()

		if reqHeight > maxH:
			if self._vsb.winfo_ismapped():
				maxW = clipW
			else:
				maxW = (clipW - self._vsb.winfo_reqwidth())
				self._vsb.grid(column=5, row=3, sticky='wns')
				return maxW, maxH
			if reqWidth > maxW:
				if self._hsb.winfo_ismapped():
					maxH = clipH
				else:
					maxH = (clipH
						- self._hsb.winfo_reqheight())
					self._hsb.grid(column=3, row=5,
								sticky='new')
			else:
				self._hsb.grid_forget()
		elif reqWidth > maxW:
			if self._hsb.winfo_ismapped():
				maxH = clipH
			else:
				maxH = (clipH - self._hsb.winfo_reqheight())
				self._hsb.grid(column=3, row=5, sticky='new')
				return maxW, maxH
			if reqHeight > maxH:
				if self._vsb.winfo_ismapped():
					maxW = clipW
				else:
					maxW = (clipW
						- self._vsb.winfo_reqwidth())
					self._vsb.grid(column=5, row=3,
								sticky='wns')
			else:
				self._vsb.grid_forget()
		else:
			if self._vsb.winfo_ismapped():
				self._vsb.grid_forget()
			else:
				self._hsb.grid_forget()
		return maxW, maxH

	def _configureY(self, reqWidth, reqHeight):
		# vertical scrollbar is automatic, horizontal is not
		clipW = maxW = self._clipper.winfo_width()
		clipH = self._clipper.winfo_height()
		if reqHeight > clipH:
			if not self._vsb.winfo_ismapped():
				maxW = (clipW - self._vsb.winfo_reqwidth())
				self._vsb.grid(column=5, row=3, sticky='wns')
		else:
			self._vsb.grid_forget()
		return maxW, clipH

	def _configureX(self, reqWidth, reqHeight):
		# horizontal scrollbar is automatic, vertical is not
		clipW = self._clipper.winfo_width()
		clipH = maxH = self._clipper.winfo_height()
		if reqWidth > clipW:
			if not self._hsb.winfo_ismapped():
				maxH = (clipH - self._hsb.winfo_reqheight())
				self._hsb.grid(column=3, row=5, sticky='new')
		else:
			self._hsb.grid_forget()
		return clipW, maxH

	def _configureFixed(self, reqWidth, reqHeight):
		# neither scrollbar is automatic
		clipW = self._clipper.winfo_width()
		clipH = self._clipper.winfo_height()
		return clipW, clipH

	def _titles(self, titleDict, withKw):
		# if returning keywords, assume rebuilding titles is
		# desired, therefore don't massage textvarible titles
		# into strings
		if withKw:
			from copy import copy
			return copy(titleDict)

		ret = {}
		for k, v in titleDict.items():
			title = v[0]
			if not isinstance(title, basestring):
				# textvariable
				title = title.get()
			ret[k] = title
		return ret

	def _updateColumnLabels(self, force=0, reuse=0):
		if not reuse:
			for component in self.components():
				if component[:6] == "column" \
				and component[6].isdigit():
					self.destroycomponent(component)
		maxHeight = 0
		totalWidth = 0
		cols, rows = self._frame.grid_size()
		if force and self._colTitles:
			cols = max(self._colTitles.keys()) + 1
		for c in range(cols):
			slaves = self._frame.grid_slaves(column=c)
			if not slaves:
				width = 0
			else:
				width = max(map(lambda s: s.winfo_reqwidth(),
									slaves))
			self._colFrame.columnconfigure(c, minsize=width)
			if slaves or self._colTitles.has_key(c):
				if not self._colTitles.has_key(c):
					self._colTitles[c] = ("", {})
				text, userkw = self._colTitles[c]
				kw = {}
				if not userkw.has_key('pyclass'):
					kw.update({
						'bd': 2,
						'relief': 'groove'
					})
				kw.update(userkw)
				if isinstance(text, basestring):
					kw['text'] = text
				else:
					kw['textvariable'] = text
				componentName = "column%d" % c
				if reuse:
					try:
						title = self.component(
								componentName)
					except KeyError:
						title = None
				if not reuse or title == None:
					title = self.createcomponent(
							componentName,
							(), "Columntitle",
							Tkinter.Label,
							(self._colFrame,), **kw)
					title.grid(row=0, column=c, sticky='ew')
				titleWidth = title.winfo_reqwidth()
				titleHeight = title.winfo_reqheight()
				if titleHeight > maxHeight:
					maxHeight = titleHeight
			else:
				titleWidth = 0
			if titleWidth > width:
				self._frame.columnconfigure(c,
							minsize=titleWidth)
				totalWidth = totalWidth + titleWidth
			else:
				self._frame.columnconfigure(c, minsize=0)
				totalWidth = totalWidth + width
		if cols > 0 and totalWidth == 0:
			self._frame.update_idletasks()
			self._updateColumnLabels()
			return
		self._colClipper.config(height=maxHeight, width=totalWidth)

	def _updateRowLabels(self, force=0, reuse=0):
		if not reuse:
			for component in self.components():
				if component[:3] == "row" \
				and component[3].isdigit():
					self.destroycomponent(component)
		maxWidth = 0
		totalHeight = 0
		cols, rows = self._frame.grid_size()
		if force and self._rowTitles:
			rows = max(self._rowTitles.keys()) + 1
		for r in range(rows):
			slaves = self._frame.grid_slaves(row=r)
			if not slaves:
				height = 0
			else:
				height = max(map(lambda s: s.winfo_reqheight(),
									slaves))
			self._rowFrame.rowconfigure(r, minsize=height)
			if self._rowTitles.has_key(r):
				text, userkw = self._rowTitles[r]
				kw = {}
				if not userkw.has_key('pyclass'):
					kw.update({
						'bd': 2,
						'relief': 'groove'
					})
				kw.update(userkw)
				if isinstance(text, basestring):
					kw['text'] = text
				else:
					kw['textvariable'] = text
				componentName = "row%d" % r
				if reuse:
					try:
						title = self.component(
								componentName)
					except KeyError:
						title = None
				if not reuse or title == None:
					title = self.createcomponent(
							componentName,
							(), "Rowtitle",
							Tkinter.Label,
							(self._rowFrame,), **kw)
					title.grid(row=r, column=0, sticky='ew')
				titleHeight = title.winfo_reqheight()
				titleWidth = title.winfo_reqwidth()
				if titleWidth > maxWidth:
					maxWidth = titleWidth
			else:
				titleHeight = 0
			if titleHeight > height:
				self._frame.rowconfigure(r, minsize=titleHeight)
				totalHeight = totalHeight + titleHeight
			else:
				totalHeight = totalHeight + height
		if rows > 0 and totalHeight == 0:
			self._frame.update_idletasks()
			self._updateRowLabels()
			return
		self._rowClipper.config(width=maxWidth, height=totalHeight)

	def _vScroll(self, cmd, *args):
		s, e = self._scroll(cmd, self._vScale, self._vsb, args,
							self['vertfraction'])
		y = -int(self._height * s)
		self._rowFrame.place(y=y)
		self._frame.place(y=y)
		return s, e

	def _hScroll(self, cmd, *args):
		s, e = self._scroll(cmd, self._hScale, self._hsb, args,
							self['horizfraction'])
		x = -int(self._width * s)
		self._colFrame.place(x=x)
		self._frame.place(x=x)
		return s, e

	def _scroll(self, cmd, scale, sb, args, fract):
		if cmd == 'moveto':
			start = float(args[0])
		elif cmd == 'scroll':
			start = sb.get()[-2]
			if args[1] == 'units':
				start = start + float(args[0]) * scale * fract
			elif args[1] == 'pages':
				start = start + float(args[0]) * scale
		if start < 0:
			start = 0
		if scale > 1:
			start = 0
			end = 1
		else:
			end = start + scale
			if end > 1:
				end = 1
				start = end - scale
		sb.set(start, end)
		return start, end

	def interior(self):
		return self._frame
	
import Tkinter
class SortableTable(Tkinter.Frame):
	""" typically you addColumn()s, setData(), and launch()

	    however if you saved state with getRestoreInfo(), you just setData()
	    and then launch() with the restoreInfo keyword

	    'automultilineHeaders' controls whether header titles can be 
	    automatically split into multiple lines on word boundaries

	    'allowUserSorting' controls whether mouse clicks on column
	    headers will sort the columns.

	    'menuInfo', if provided, should be a (menu, pref dict,
	    defaults dict, fallback default) tuple.
	    The menu will be populated with checkbutton entries as columns
	    are added, controlling what columns are displayed.  The pref dict
	    will be used to store displayed column preferences (under the key
	    "SortableTable info"). The defaults dict controls whether the
	    column is shown by default (i.e. if the addColumn() 'display'
	    keyword is omitted).  The dictionary should have column titles
	    as keys and booleans as values (True = displayed). The fallback
	    default is used if the column isn't in the dictionary.
		The menuInfo tuple can optionally have a fifth element ("displayCB")
		which, if not None, is called when a column is configured
		in/out of the table.  It is called with a single argument:
		the configured column (whose 'display' attr corresponds to
		the state _after_ the change).
		----
		Alternatively, 'menuInfo' can be a tuple of (frame, pref dict,
		defaults dict, fallback default, displayCB, wrap length, num
		checkbutton cols).  In this case a frame will be populated with
		checkbuttons.  The differences: the user will be able to explicitly
		control when a set of columns is saved as the default (and when that
		default is restored); if 'wrap length' is not None, it controls the
		initial maxiumum column width (in inches) before wrapping occurs;
		if 'num checkbutton cols' is not None, the number of columns to
		lay the checkbutton out in (otherwise automatically determined).
	"""
	PREF_KEY = "SortableTable info"
	PREF_SUBKEY_COL_DISP = "default col display"
	PREF_SUBKEY_WRAP = "col wrap width"
	def __init__(self, master, automultilineHeaders=True, menuInfo=None,
						allowUserSorting=True,
						allowCopy=False):
		self.tixTable = None
		self.data = None
		self.columns = []
		self.sorting = None
		self.allowUserSorting = allowUserSorting
		self.allowCopy = allowCopy
		self.automultilineHeaders = automultilineHeaders
		self.menuInfo = menuInfo
		if menuInfo:
			prefDict = menuInfo[1]
			prefs = prefDict.get(self.PREF_KEY, {})
			if isinstance(prefs.get(self.PREF_SUBKEY_COL_DISP, True), bool):
				# convert old-style or non-existent prefs to current
				from copy import copy
				if prefs:
					val = copy(prefs)
				else:
					val = copy(menuInfo[2])
				prefDict[self.PREF_KEY] = {self.PREF_SUBKEY_COL_DISP: val}
			if isinstance(menuInfo[0], Tkinter.Frame):
				import itertools
				row = itertools.count()
				self._colChkButFrame = Tkinter.Frame(menuInfo[0])
				self._colChkButFrame.grid(row=row.next(), column=0, sticky='w')
				self._colCheckButtons = {}
				if menuInfo[-2] is not None:
					f = Tkinter.Frame(menuInfo[0])
					f.grid(row=row.next(), column=0, sticky='w')
					wrapVal = prefDict.get(self.PREF_KEY, {}).get(self.PREF_SUBKEY_WRAP,
							menuInfo[-2])
					if isinstance(wrapVal, basestring):
						amount = float(wrapVal[:-1])
						if wrapVal[-1] == "i":
							units = "inches"
						else:
							units = "cm"
					else:
						amount = wrapVal
						units = "inches"
					from chimera.tkoptions import FloatOption
					self._colWrapWidthOpt = FloatOption(f, 0, "Maximum column width",
							amount, self._colWrap, min=1.0, width=4)
					self._colWrapUnitsMenu = Pmw.OptionMenu(f, command=self._colWrap,
							initialitem=units, items=["inches", "cm"])
					self._colWrapUnitsMenu.grid(row=0, column=2)
				f = Tkinter.Frame(menuInfo[0])
				f.grid(row=row.next(), column=0, sticky='w')
				Tkinter.Label(f, text="Show columns").grid(row=0, column=0)
				Tkinter.Button(f, text="All", command=self._showAllColumns).grid(
						row=0, column=1)
				Tkinter.Button(f, text="Default", command=self.showDefault).grid(
						row=0, column=2)
				Tkinter.Button(f, text="Standard", command=self._showStandard).grid(
						row=0, column=3)
				Tkinter.Button(f, text="Set Default", command=self.setDefault).grid(
						row=0, column=4)
		Tkinter.Frame.__init__(self, master)
		try:
			from chimera import chimage
			self.upArrow = chimage.get("uparrow.png", self)
			self.downArrow = chimage.get("downarrow.png", self)
		except ImportError:
			self.upArrow = "^"
			self.downArrow = "v"
		self._sortCache = None
		self._lastBrowseSel = None
		self._highlighted = []
		self._widgetData = {}

	def addColumn(self, title, dataFetch, format="%s", display=None,
			titleDisplay=True, anchor='center', wrapLength=0, balloon=None,
			font='TkTextFont', headerPadX=None, headerPadY=None,
			entryPadX=None, entryPadY=None, refresh=True, color=None,
			headerAnchor=None):
		"""if format is the type bool, use column of checkbuttons;
		   if format is a tuple, then use a color well; the tuple
		   should be two booleans: None okay, alpha okay.
		   format can be a function that takes a data item argument
		   and returns the displayable representation.
		"""
		titles = [c.title for c in self.columns]
		if title in titles:
			return self.columns[titles.index(title)]
		if display == None:
			if self.menuInfo:
				menu, prefDict, displayDefaults, fallback \
								= self.menuInfo[:4]
				lookup = prefDict.get(self.PREF_KEY).get(self.PREF_SUBKEY_COL_DISP,
							displayDefaults)
				display = lookup.get(title, fallback)
			else:
				display = True
		if self.menuInfo and isinstance(self.menuInfo[0], Tkinter.Frame) \
		and self.menuInfo[-2] is not None:
			wrapLength = self._userWrapLength()
		if headerAnchor is None:
			headerAnchor = anchor
		c = SortableColumn(title, dataFetch, format, titleDisplay,
			anchor, wrapLength, font, headerPadX, headerPadY,
			entryPadX, entryPadY, color, headerAnchor)

		if display != c.display:
			self.columnUpdate(c, display=display)
		self.columns.append(c)
		if refresh:
			self.refresh(rebuild=True)
		if self.menuInfo:
			self._addColumnMenuEntry(c, display, balloon)
		return c

	def columnUpdate(self, column, **kw):
		immediateRefresh = kw.pop('immediateRefresh', True)
		needRefresh = column._update(**kw)
		if needRefresh and immediateRefresh:
			self.refresh(rebuild=True)
		if self.menuInfo and 'display' in kw:
			try:
				self._vars[column.title].set(kw['display'])
			except:
				pass
		return needRefresh

	def destroy(self):
		self.data = self._sortCache = self.userBrowseCmd = None
		if self.tixTable:
			self.tixTable.destroy()
		Tkinter.Frame.destroy(self)
		
	def getRestoreInfo(self):
		"""return info needed for 'restoreInfo' arg of launch()"""
		saveSorting = self.sorting
		if saveSorting:
			sortCol, forward = saveSorting
			saveSorting = (self.columns.index(sortCol), forward)
		if self.menuInfo and isinstance(self.menuInfo[0], Tkinter.Frame) \
		and self.menuInfo[-2] is not None:
			wrapInfo = (self._colWrapWidthOpt.get(), self._colWrapUnitsMenu.getvalue())
		else:
			wrapInfo = None
		return (6, saveSorting,
			[int(s) for s in self.tixTable.hlist.info_selection()],
			[c._getRestoreInfo() for c in self.columns],
			self.highlightedIndices(),
			(self.title, self.titleFont, self.titleSticky), wrapInfo)

	def highlight(self, hlList):
		sortData = self._sortedData()
		old = set([sortData.index(hl) for hl in self._highlighted])
		new = set([sortData.index(hl) for hl in hlList])
		if old == new:
			return
		hlist = self.tixTable.hlist
		if hlist is None:
			return
		removeList = old - new
		addList = new - old
		clist = [c for c in self.columns if c.display]
		for row in removeList:
			for col,column in enumerate(clist):
				hlist.item_configure(row, col,
						style=column.textStyle)
		for row in addList:
			for col,column in enumerate(clist):
				hlist.item_configure(row, col,
						style=column.highlightStyle)
		self._highlighted = hlList

	def highlighted(self):
		return self._highlighted

	def highlightedIndices(self):
		sortData = self._sortedData()
		return [sortData.index(hl) for hl in self._highlighted]

	def launch(self, browseCmd=None, selectMode="extended", restoreInfo=None,
			title=None, titleFont="TkHeadingFont", titleSticky="ew", rows=10):
		self.initialRows = rows
		self.userBrowseCmd = browseCmd
		self.selectMode = selectMode
		if restoreInfo:
			version = restoreInfo[0]
			if version == 1:
				(version, sorting, selection,
					columnInfo) = restoreInfo
			elif version in [2,3]:
				(version, sorting, selection,
					columnInfo, highlight) = restoreInfo
			elif version in [4,5]:
				(version, sorting, selection,
					columnInfo, highlight, titleInfo) = restoreInfo
				title, titleFont, titleSticky = titleInfo
			else:
				(version, sorting, selection,
					columnInfo, highlight, titleInfo, wrapInfo) = restoreInfo
				title, titleFont, titleSticky = titleInfo
				if wrapInfo:
					amount, units = wrapInfo
					self._colWrapWidthOpt.set(amount)
					self._colWrapUnitsMenu.setvalue(units)
			existingCols = dict([(c.title, c) for c in self.columns])
			if version < 3:
				for header, fetch, format, display in columnInfo:
					if header in existingCols:
						self.columnUpdate(existingCols[header],
								format=format, display=display)
					else:
						self.addColumn(header, fetch, format=format,
								display=display)
			elif version == 3:
				for header, fetch, format, display, anchor in columnInfo:
					if header in existingCols:
						self.columnUpdate(existingCols[header], format=format,
								display=display, anchor=anchor)
					else:
						self.addColumn(header, fetch, format=format,
									display=display, anchor=anchor)
			elif version == 4:
				for header, fetch, format, display, anchor, font in columnInfo:
					if header in existingCols:
						self.columnUpdate(existingCols[header], format=format,
								display=display, anchor=anchor, font=font)
					else:
						self.addColumn(header, fetch, format=format,
									display=display, anchor=anchor, font=font)
			else:
				for header, fetch, format, display, anchor, font, titleDisplay, \
						wrapLength, hpadx, hpady, epadx, epady, color in columnInfo:
					if header in existingCols:
						self.columnUpdate(existingCols[header], format=format,
								display=display, anchor=anchor, font=font,
								wrapLength=wrapLength, headerPadX=hpadx,
								headerPadY=hpady, entryPadX=epadx, entryPadY=epady)
					else:
						self.addColumn(header, fetch, format=format, display=display,
							anchor=anchor, font=font, titleDisplay=titleDisplay,
							wrapLength=wrapLength, headerPadX=hpadx, headerPadY=hpady,
							entryPadX=epadx, entryPadY=epady, color=color)
			if sorting:
				colIndex, forward = sorting
				col = self.columns[colIndex]
				self.sortBy(col)
				if not forward:
					self.sortBy(col)
			sortData = self._sortedData()
			sel = [sortData[i] for i in selection]
		else:
			sel = None
		self.title, self.titleFont, self.titleSticky = \
								title, titleFont, titleSticky
		if self.title == None:
			self.tableRow = 0
		else:
			self.tableRow = 1
			self.titleLabel = Tkinter.Label(self, text=title, font=titleFont)
			self.titleLabel.grid(row=0, column=0, sticky=titleSticky)
		self.columnconfigure(0, weight=1)
		self.rowconfigure(self.tableRow, weight=1)
		self._constructEmptyTable()
		if self.menuInfo and isinstance(self.menuInfo[0], Tkinter.Frame):
			self._arrangeColCheckButtons()
		self.refresh(selection=sel)
		self.requestFullWidth()
		if restoreInfo:
			if version > 2:
				self.highlight([sortData[i] for i in highlight])

	def middleRow(self):
		sortedData = self._sortedData()
		if sortedData is None or len(sortedData) == 0:
			return None
		v0,v1 = self.tixTable.vsb.get()
		middle = sortedData[int(0.5 * (v0+v1) * len(sortedData))]
		return middle

	def refresh(self, selection=None, rebuild=False):
		if not self.tixTable:
			return
		# cull dead data
		liveData = [d for d in self.data
				if not getattr(d, '__destroyed__', False)]
		if len(liveData) != len(self.data):
			self.setData(liveData)
			return
		if selection is None:
			selection = self._selected()
		from color.ColorWell import ColorWell
		activeWellKeys = []
		if rebuild:
			self._constructEmptyTable()
			hlist = self.tixTable.hlist
		else:
			# avoid deleting headers, since it makes entire widget
			# change size
			hlist = self.tixTable.hlist
			for row in range(getattr(self, '_prevRows', 0)):
				hlist.delete_entry(row)
		for k, widget in self._widgetData.items():
			if isinstance(widget, ColorWell) and widget.active:
				activeWellKeys.append(k)
			widget.destroy()
		self._widgetData.clear()
		# data in the sorting column may have changed...
		self._sortCache = None
		sortData = self._sortedData()
		for row, datum in enumerate(sortData):
			for col, column in enumerate([c for c in self.columns
								if c.display]):
				if col == 0:
					hlist.add(row)
				self._createCell(hlist, row, col, datum, column)
		activeWells = []
		for awk in activeWellKeys:
			try:
				activeWells.append(self._widgetData[awk])
			except KeyError:
				pass
		if activeWells and len(set([w.rgba for w in activeWells])) == 1:
			for w in activeWells:
				w.activate()
		# have to cache number of rows, since
		# hlist.info_exists(row) seemingly always returns True
		self._prevRows = len(sortData)
		for s in selection:
			if s in sortData:
				hlist.selection_set(sortData.index(s))

	def removeColumn(self, columnName, refresh=True):
		titles = [c.title for c in self.columns]
		if not columnName in titles:
			return
		if self.sorting:
			sortCol, forward = self.sorting
			if sortCol.title == columnName:
				self.sorting = None
		del self.columns[titles.index(columnName)]
		if refresh:
			self.refresh(rebuild=True)
		if self.menuInfo:
			self._removeColumnMenuEntry(columnName)
		
	def requestFullWidth(self):
		clist = [c for c in self.columns if c.display]
		if clist:
			# Attempt to display table full width.
			h = self.tixTable.hlist
			w = sum([int(h.column_width(c)) +
				 2*int(col.textStyle['padx'])
				 for c,col in enumerate(clist)])
			import tkFont
			fw = tkFont.Font(font=h.cget('font')).measure('0')
			# half an inch or so seems to be randomly added
			# so try to compensate...
			h.configure(width = max(w/fw - 5, 0))

	def select(self, selection):
		sortData = self._sortedData()
		hlist = self.tixTable.hlist
		hlist.selection_clear()
		if self.selectMode in ["single", "browse"]:
			selection = [selection]
		for s in selection:
			if s in sortData:
				hlist.selection_set(sortData.index(s))

	def selected(self):
		sortedData = self._sortedData()
		retVals = [sortedData[int(s)]
				for s in self.tixTable.hlist.info_selection()]
		if self.selectMode in ["single", "browse"]:
			if retVals:
				return retVals[0]
			else:
				return None
		return retVals

	def setData(self, data):
		if self.tixTable:
			curSel = self._selected()
		else:
			curSel = []
		self.data = data[:]
		self._sortCache = None
		dataSet = set([id(v) for v in data])
		self._highlighted = []
		remSel = [i for i in curSel if id(i) in dataSet]
		self.refresh(selection=remSel)
		if len(curSel) != len(remSel):
			self._browseCmd(None)

	def showRow(self, data):
		sortedData = self._sortedData()
		if sortedData is None or not data in sortedData:
			return
		row = sortedData.index(data)
		self.tixTable.hlist.see(row)

	def sortBy(self, column):
		if self.tixTable:
			selection = self._selected()
		else:
			selection = None
		if self.sorting:
			sortCol, forward = self.sorting
			self._setColumnSortIndicator(sortCol, None)
			if column == sortCol:
				self.sorting = (column, not forward)
			else:
				self.sorting = (column, True)
		else:
			self.sorting = (column, True)
		self._setColumnSortIndicator(*self.sorting)
		self._sortCache = None
		self.refresh(selection=selection)

	def updateCellWidget(self, datum, column, contents=None, widget=None):
		if contents is None:
			contents = column.displayValue(datum)
		if widget is None:
			widget = self._widgetData[(datum, column)]
		from PIL.ImageTk import PhotoImage
		if isinstance(contents, PhotoImage):
			widget.configure(image=contents)
		elif type(contents) == bool:
			widget.configure(image=self._ckButImage(contents))
		else:
			color, noneOkay, alphaOkay = contents
			if hasattr(color, 'rgba'):
				from chimera import MaterialColor
				cval = color.rgba()
			else:
				cval = color
			widget.showColor(cval, doCallback=False)
	
	def saveTable(self):
		"""
		return strings ready for print out the table into text file
		"""
		#TODO to be tested!!!
		ss = ''
		for c in self.columns:
			ss += c.title
			ss += '\t'
		ss += '\n'
		for d in self.data:
			for c in self.columns:
				ss += str( c.displayValue(d) )
			ss += '\n'
		return ss

	def tableValuesString(self, selectedOnly = False, separator = ','):

		from StringIO import StringIO
		f = StringIO()
		col = [c for c in self.columns if c.display]
		f.write(csvLine([c.title for c in col]))
		rows = self._selected() if selectedOnly and self.tixTable else self._sortedData()
		for r in rows:
			fields = [c.displayValue(r) for c in col]
			# Don't export images or other non-string values.
			sfields = [v if isinstance(v,basestring) else ''
				   for v in fields]
			f.write(csvLine(sfields))
		return f.getvalue()

	def _addColumnMenuEntry(self, col, display, balloon):
		# use a variable (and hold a reference)
		# so that we can have the checkbutton 'on' initially
		import Tkinter
		if not hasattr(self, '_vars'):
			self._vars = {}
		menu = self.menuInfo[0]
		v = Tkinter.IntVar(menu)
		self._vars[col.title] = v
		v.set(display)
		cmd = lambda c=col: self._colDispChange(c)
		if len(self.menuInfo) > 4 and self.menuInfo[4]: # displayCB defined
			cb = self.menuInfo[4]
			cb(col)
			cmd = lambda c=col, subcmd=cmd, cb=cb: (subcmd(c) or True) and cb(c)
		if isinstance(menu, Tkinter.Frame):
			if hasattr(self, 'title'):
				# we've been launch()ed
				for cb in self._colCheckButtons.values():
					cb.grid_remove()
			self._colCheckButtons[col.title] = Tkinter.Checkbutton(self._colChkButFrame,
					text=col.title, variable=v, command=cmd)
			if balloon:
				try:
					from chimera import help
				except ImportError:
					pass
				else:
					help.register(self._colCheckButtons[col.title], balloon=balloon)
			if hasattr(self, 'title'):
				self._arrangeColCheckButtons()
		else:
			menu.add_checkbutton(label=col.title, variable=v, command=cmd)

	def _removeColumnMenuEntry(self, columnName):
		menu = self.menuInfo[0]
		if isinstance(menu, Tkinter.Frame):
			self._colCheckButtons[columnName].grid_forget()
			del self._colCheckButtons[columnName]
			for cb in self._colCheckButtons.values():
				cb.grid_remove()
			self._arrangeColCheckButtons()
		else:
			i = menu.index(columnName)
			menu.delete(i)
		del self._vars[columnName]

	def _arrangeColCheckButtons(self):
		names = self._colCheckButtons.keys()
		if not names:
			return
		names.sort(lambda n1,n2: cmp(n1.lower(), n2.lower()))
		numCols = self.menuInfo[-1]
		numButtons = len(names)
		from math import sqrt, ceil
		if numCols is None:
			numCols = int(sqrt(numButtons)+0.5)
		numRows = int(ceil(numButtons/float(numCols)))
		row = col = 0
		for name in names:
			self._colCheckButtons[name].grid(row=row, column=col, sticky='w')
			row += 1
			if row >= numRows:
				row = 0
				col += 1

	def _browseCmd(self, tixArg):
		if self.allowCopy:
			self.focus_set()
		if not self.userBrowseCmd:
			return
		# prevent multiple callbacks if selection doesn't change
		# during browse
		curSel = self._selected()
		if self._lastBrowseSel != None \
		and curSel == self._lastBrowseSel:
			return
		self._lastBrowseSel = curSel
		self.userBrowseCmd(self.selected())

	def _ckButImage(self, val):
		if val:
			imageName = "ck_on"
		else:
			imageName = "ck_off"
		return self.tixTable.tk.call("tix", "getimage", imageName)

	def _colDispChange(self, col):
		self.columnUpdate(col, display=not col.display)
		menu, prefDict = self.menuInfo[:2]
		if not isinstance(menu, Tkinter.Frame):
			displayStates = {}
			for c in self.columns:
				displayStates[c.title] = c.display
			prefDict[self.PREF_KEY] = displayStates

	def _columnHeader(self, hlist, column):
		frame = Tkinter.Frame(hlist)
		l1 = Tkinter.Label(frame, text=self._headerText(column),
							foreground=column.color, takefocus=True)
		l1.grid(row=0, column=0)
		frame.columnconfigure(0, weight=1)
		if self.allowUserSorting:
			command = lambda e, c=column: self.sortBy(c)
			l1.bind("<ButtonRelease>", command)
			l2 = column.indicator = Tkinter.Label(frame)
			l2.bind("<ButtonRelease>", command)
			l2.grid(row=0, column=1)
			l2.grid_remove()
			if self.sorting:
				sortColumn, forward = self.sorting
				if sortColumn == column:
					self._setColumnSortIndicator(column, forward)
		return frame

	def _colWrap(self, *args):
		wrapLength = self._userWrapLength()
		needRefresh = False
		for col in self.columns:
			needRefresh = self.columnUpdate(col, wrapLength=wrapLength,
					immediateRefresh=False) or needRefresh
		if needRefresh:
			self.refresh(rebuild=True)

	def _constructEmptyTable(self):
		if self.tixTable:
			self.tixTable.grid_forget()
			self.tixTable.destroy()
		clist = [c for c in self.columns if c.display]
		import Tix
		self.tixTable = t = Tix.ScrolledHList(self, options=
			"""hlist.columns %d
			hlist.height %d
			hlist.header 1
			hlist.selectMode %s
			hlist.indicator 0"""
			% (len(clist), self.initialRows, self.selectMode))
		t.grid(row=self.tableRow, column=0, sticky="nsew")
		t.hlist.config(browsecmd=self._browseCmd)
		for colNum, column in enumerate([c for c in self.columns
								if c.display]):
			t.hlist.header_create(colNum, itemtype='window',
				style=column.headerStyle,
				window=self._columnHeader(t.hlist, column))
		if self.allowCopy:
			self.bind("<<Copy>>", self._copy)

	def _createCell(self, hlist, row, col, datum, column):
		contents = column.displayValue(datum)
		if isinstance(contents, basestring):
			hlist.item_create(row, col, itemtype="text",
					style=column.textStyle,
					text=contents)
			return
		# widgets...
		from PIL.ImageTk import PhotoImage
		if isinstance(contents, PhotoImage):
			lbl = Tkinter.Label(hlist, borderwidth=0)
			if hasattr(contents, 'button_press_callback'):
				lbl.bind('<ButtonPress>',
					 contents.button_press_callback)
			widget = self._widgetData[(datum, column)] = lbl
			hlist.item_create(row, col,
					itemtype="window", window=lbl,
					style=column.imageStyle)
		elif type(contents) == bool:
			but = Tkinter.Checkbutton(hlist,
					command=lambda d=datum, c=column: self._widgetCB(d, c),
					indicatoron=False, borderwidth=0)
			widget = self._widgetData[(datum, column)] = but
			hlist.item_create(row, col,
					itemtype="window", window=but,
					style=column.checkButtonStyle)
		else:
			color, noneOkay, alphaOkay = contents
			from color.ColorWell import ColorWell
			if hasattr(color, 'rgba'):
				from chimera import MaterialColor
				cval = color.rgba()
				cb = lambda clr, d=datum, c=column:\
					self._widgetCB(d, c, newVal=MaterialColor(*clr))
			else:
				cval = color
				cb = lambda clr, d=datum, c=column:\
					self._widgetCB(d, c, newVal=clr)
			well = ColorWell(hlist, cval,
					callback=cb, width=18,
					height=18, noneOkay=noneOkay,
					wantAlpha=alphaOkay)
			widget = self._widgetData[(datum, column)] = well
			hlist.item_create(row, col,
					itemtype="window", window=well,
					style=column.colorWellStyle)

		self.updateCellWidget(datum, column, contents=contents, widget=widget)

	def _headerText(self, column):
		if not column.titleDisplay:
			return ""
		rawText = column.title
		if not self.automultilineHeaders:
			return rawText
		words = rawText.strip().split()
		if len(words) < 2:
			return rawText
		longest = max([len(w) for w in words])
		while True:
			bestDiff = bestIndex = None
			for i in range(len(words)-1):
				w1, w2 = words[i:i+2]
				curDiff = max(abs(longest - len(w1)),
						abs(longest - len(w2)))
				diff = abs(longest - len(w1) - len(w2) - 1)
				if diff >= curDiff:
					continue
				if bestDiff == None or diff < bestDiff:
					bestDiff = diff
					bestIndex = i
			if bestDiff == None:
				break
			words[bestIndex:bestIndex+2] = [" ".join(
						words[bestIndex:bestIndex+2])]
		return '\n'.join(words)
	
	def _selected(self):
		sel = self.selected()
		if not isinstance(sel, (list, tuple)):
			if sel:
				sel = [sel]
			else:
				sel = []
		return sel

	def _setColumnSortIndicator(self, column, forward):
		if not self.tixTable or not self.allowUserSorting:
			return
		if forward is None:
			column.indicator.grid_remove()
		else:
			if forward:
				image = self.upArrow
			else:
				image = self.downArrow
			if isinstance(image, str):
				column.indicator.configure(text=image)
			else:
				column.indicator.configure(image=image)
			column.indicator.grid()

	def setDefault(self, default=None):
		# only application when column controls are in a frame
		prefDict = self.menuInfo[1]
		if default is None:
			if self.menuInfo[-2] is not None:
				amount = self._colWrapWidthOpt.get()
				wrap = "%g%s" % (amount, self._colWrapUnitsMenu.getvalue()[0])
			else:
				wrap = None
			shown = {}
			for col in self.columns:
				shown[col.title] = col.display
		else:
			if self.menuInfo[-2] is None:
				shown, wrap = default, None
			else:
				shown, wrap = default
		if wrap is not None:
			self._setSubpref(prefDict, self.PREF_SUBKEY_WRAP, wrap)
		self._setSubpref(prefDict, self.PREF_SUBKEY_COL_DISP, shown)

	def _setSubpref(self, prefDict, subpref, val):
		# since main preference is a dict, need to create a new dict so that
		# the preferences system notices it has changed
		prevPrefs = prefDict[self.PREF_KEY]
		from copy import copy
		newPrefs = copy(prevPrefs)
		newPrefs[subpref] = val
		prefDict[self.PREF_KEY] = newPrefs

	def _showAllColumns(self):
		needRefresh = False
		for col in self.columns:
			needRefresh = self.columnUpdate(col, display=True,
					immediateRefresh=False) or needRefresh
		if needRefresh:
			self.refresh(rebuild=True)

	def showDefault(self):
		# only application when column controls are in a frame
		kw = {'immediateRefresh': False}
		menu, prefDict, displayDefaults, fallback = self.menuInfo[:4]
		if self.menuInfo[-2] is not None:
			wrap = prefDict.get(self.PREF_KEY).get(
					self.PREF_SUBKEY_WRAP, "%gi" % self.menuInfo[-2])
			self._colWrapWidthOpt.set(float(wrap[:-1]))
			if wrap[-1] == "i":
				val = "inches"
			else:
				val = "cm"
			self._colWrapUnitsMenu.setvalue(val)
			wrap = self._userWrapLength() # adjusts for Tk prob
		else:
			wrap = 0
		kw['wrapLength'] = wrap

		needRefresh = False
		for col in self.columns:
			lookup = prefDict.get(self.PREF_KEY).get(self.PREF_SUBKEY_COL_DISP,
						displayDefaults)
			kw['display'] = lookup.get(col.title, fallback)
			needRefresh = self.columnUpdate(col, **kw) or needRefresh
		if needRefresh:
			self.refresh(rebuild=True)

	def _showStandard(self):
		kw = {'immediateRefresh': False}
		menu, prefDict, displayDefaults, fallback = self.menuInfo[:4]
		if isinstance(menu, Tkinter.Frame) and self.menuInfo[-2] is not None:
			self._colWrapWidthOpt.set(self.menuInfo[-2])
			self._colWrapUnitsMenu.setvalue("inches")
			wrap = self._userWrapLength() # adjusts for Tk prob
		else:
			wrap = 0
		kw['wrapLength'] = wrap

		needRefresh = False
		for col in self.columns:
			kw['display'] = displayDefaults.get(col.title, fallback)
			needRefresh = self.columnUpdate(col, **kw) or needRefresh
		if needRefresh:
			self.refresh(rebuild=True)

	def _sortedData(self):
		if self._sortCache:
			return self._sortCache
		if self.sorting:
			sortData = self.data[:]
			sortColumn, forward = self.sorting
			sortData.sort(lambda d1, d2: cmp(sortColumn.value(d1),
							sortColumn.value(d2)))
			if not forward:
				sortData.reverse()
		else:
			sortData = self.data
		self._sortCache = sortData
		return sortData

	def _userWrapLength(self):
		amount = self._colWrapWidthOpt.get()
		if amount is None:
			return 0
		if self._colWrapUnitsMenu.getvalue() == "inches":
			conversion = "i"
		else:
			conversion = "c"
		from chimera.tkgui import windowSystem
		if windowSystem == "aqua" and self.winfo_pixels("1i") == 72:
			# Tk aqua always reports 72 dpi; make a kludge adjustment
			amount *= (96.0 / 72.0)
		return "%g%s" % (amount, conversion)

	def _widgetCB(self, datum, column, newVal=None):
		widget = self._widgetData[(datum, column)]
		if column.displayFormat == bool:
			newVal = not column.value(datum)
			# set widget first, since setting attribute may rebuild table
			widget.configure(image=self._ckButImage(newVal))
			column.setValue(datum, newVal)
		else:
			column.setValue(datum, newVal)

	def _copy(self, event=None):

		lines = list()
		for item in self._selected():
			cols = [ c.displayValue(item) for c in self.columns ]
			lines.append('\t'.join(cols) + '\n')
		text = ''.join(lines)
		self.clipboard_clear()
		self.clipboard_append(text)

def csvLine(fields, separator = ','):
	return ','.join([csvEscape(f, separator) for f in fields]) + '\n'

def csvEscape(f, separator = ','):
	fq = f.replace('"', '""')
	if separator in fq or '\n' in fq:
		fq = '"' + fq + '"'
	return fq

class SortableColumn:
	def __init__(self, title, dataFetch, displayFormat, titleDisplay,
			anchor, wrapLength, font, headerPadX, headerPadY,
			entryPadX, entryPadY, color, headerAnchor):
		self._setFetch(dataFetch)
		self.display = True
		self.font, self.fontFamily, self.fontSize = self._convertFont(font)
		for attr in ("title", "displayFormat", "titleDisplay", "anchor",
					"wrapLength", "headerPadX", "headerPadY",
					"entryPadX", "entryPadY", "color", "headerAnchor"):
			setattr(self, attr, eval(attr))
		self._computeStyles()
	
	def displayValue(self, instance):
		val = self.value(instance)
		if isinstance(self.displayFormat, basestring):
			if val is None:
				return ""
			return self.displayFormat % val
		elif callable(self.displayFormat):
			return self.displayFormat(val)
		elif isinstance(self.displayFormat, tuple):
			return (val,) + self.displayFormat
		return val

	def value(self, instance):
		if callable(self.dataFetch):
			return self.dataFetch(instance)
		fetched = instance
		try:
			for fetch in self.dataFetch.split('.'):
				fetched = getattr(fetched, fetch)
		except AttributeError:
			return None
		return fetched

	def setValue(self, instance, val):
		if callable(self.dataFetch):
			raise ValueError("Don't know how to set values for"
				" column %s" % self.title)
		fields = self.dataFetch.split('.')
		for fetch in fields[:-1]:
			instance = getattr(instance, fetch)
		setattr(instance, fields[-1], val)

	def _computeStyles(self):
		for attr in ('headerPadX', 'headerPadY', 'entryPadX', 'entryPadY',
				'anchor', 'wrapLength', 'headerAnchor'):
			exec("%s = self.%s" % (attr, attr))
		family, size = self.fontFamily, self.fontSize
		if headerPadX == None:
			headerPadX = 0
		if headerPadY == None:
			headerPadY = 0
		if entryPadX == None:
			textPadX = ".05i"
			wellPadX = checkButtonPadX = imagePadX = 0
		else:
			textPadX = wellPadX = checkButtonPadX = imagePadX = entryPadX
		if self.entryPadY == None:
			textPadY = wellPadY = checkButtonPadY = imagePadY = 0
		else:
			textPadY = wellPadY = checkButtonPadY = imagePadY = entryPadY

		import Tix
		self.textStyle = Tix.DisplayStyle("text", anchor=anchor,
			font=(family, size), wraplength=wrapLength,
			padx=textPadX, pady=textPadY)
		self.highlightStyle = Tix.DisplayStyle("text", anchor=anchor,
			font=(family, size, "bold"), wraplength=wrapLength,
			padx=textPadX, pady=textPadY)
		self.checkButtonStyle = Tix.DisplayStyle("window",
			anchor=anchor, padx=checkButtonPadX, pady=checkButtonPadY)
		self.colorWellStyle = Tix.DisplayStyle("window",
			anchor=anchor, padx=wellPadX, pady=wellPadY)
		self.imageStyle = Tix.DisplayStyle("window",
			anchor=anchor, padx=imagePadX, pady=imagePadY)
		self.headerStyle = Tix.DisplayStyle("window", anchor=headerAnchor,
			padx=headerPadX, pady=headerPadY)

	def _convertFont(self, font):
		import tkFont
		fontInfo = tkFont.Font(font=font).actual()
		family, size = fontInfo['family'], fontInfo['size']
		if isinstance(font, basestring):
			return font, family, size
		return (family, size), family, size

	def _getRestoreInfo(self):
		if callable(self._saveableFetch):
			raise ValueError("%s column is not saveable due to"
				" directly callable fetch value" % self.title)
		return (self.title, self._saveableFetch, self.displayFormat,
				self.display, self.anchor, self.font, self.titleDisplay,
				self.wrapLength, self.headerPadX, self.headerPadY,
				self.entryPadX, self.entryPadY, self.color)

	def _setFetch(self, dataFetch):
		if getattr(self, "_saveableFetch", None) == dataFetch:
			return False
		self._saveableFetch = self.dataFetch = dataFetch
		# some attributes may just happen to have the same name
		# as built-in functions (e.g. "id"), so don't eval pure
		# alphanumeric strings...
		if not (isinstance(dataFetch, basestring)
						and dataFetch.isalnum()):
			try:
				self.dataFetch = eval(dataFetch)
			except:
				pass
		return True

	def _update(self, dataFetch=None, format=None, display=None,
			anchor=None, wrapLength=None, font=None, headerPadX=None,
			headerPadY=None, entryPadX=None, entryPadY=None):
		changed = False
		if dataFetch != None:
			changed = self._setFetch(dataFetch)
		if format != None and format != self.displayFormat:
			self.displayFormat = format
			changed = True
		if display != None and display != self.display:
			self.display = display
			changed = True
		recompute = False
		if font:
			font, self.fontFamily, self.fontSize = self._convertFont(font)
		for attr in ('anchor', 'wrapLength', 'font',
					'headerPadX', 'headerPadY', 'entryPadX', 'entryPadY'):
			shouldSet = eval("%s != None and %s != self.%s"
								% (attr, attr, attr))
			if shouldSet:
				setattr(self, attr, eval(attr))
				recompute = True
		if recompute:
			changed = True
			self._computeStyles()
		return changed

def tableize(text, targetLen=25):
	"""make long strings more 'table friendly'"""
	text = text.strip()
	if not text:
		return ""
	words = text.split()
	lines = []
	curLine = words.pop(0)
	while(words):
		word = words.pop(0)
		if len(curLine) >= targetLen:
			lines.append(curLine)
			curLine = word
			continue
		addedLen = len(curLine) + len(word) + 1
		if addedLen < targetLen:
			curLine += " " + word
			continue
		if targetLen - len(curLine) < addedLen - targetLen:
			lines.append(curLine)
			curLine = word
		else:
			curLine += " " + word

	lines.append(curLine)
	return "\n".join(lines)

if __name__ == '__main__':
	app = Tkinter.Frame(width=200, height=300)
	app.pack(expand=Tkinter.TRUE, fill=Tkinter.BOTH)
	nextRow = 10
	def addRow():
		global nextRow
		for col in range(11):
			label = Tkinter.Label(table.interior(),
					text='R:%d, C:%d' % (nextRow, col),
					bd=2, relief=Tkinter.SUNKEN)
			label.grid(column=col, row=nextRow, sticky='ew')
		nextRow = nextRow + 1
	b = Tkinter.Button(app, text='Add Row', command=addRow)
	b.pack()
	table = ScrolledTable(app)
	table.pack(expand=Tkinter.TRUE, fill=Tkinter.BOTH)
	for row in range(10):
		for col in range(11):
			label = Tkinter.Label(table.interior(),
						text='R:%d, C:%d' % (row, col),
						bd=2, relief=Tkinter.SUNKEN)
			label.grid(column=col, row=row, sticky='ew')
	for col in range(5):
		table.setColumnTitle(col, 'Column %d' % col)
	for row in range(8):
		table.setRowTitle(row, 'Row %d' % row)
	app.mainloop()
