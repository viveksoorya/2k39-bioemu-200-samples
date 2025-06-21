from Tkinter import Frame
class TreeTable(Frame):

	def __init__(self, master, title, browsecmd=None, command=None,
			header=False, selectMode=None, height=None, width=None):
		Frame.__init__(self, master)
		self.title = title
		options = list()
		if header:
			options.append("hlist.header 1")
		if selectMode:
			options.append("hlist.selectMode %s" % selectMode)
		if height:
			options.append("hlist.height %s" % height)
		if width:
			options.append("hlist.width %s" % width)
		self.browsecmd = browsecmd
		self.command = command
		self.options = '\n'.join(options)
		self.tree = None
		self.columns = list()
		self.rows = list()
		self.cells = dict()
		self.numTreeColumns = -1
		self.numTreeRows = -1
		# The "used" members are for tracking what is in the
		# hlist widget.  They are copies of the equivalent
		# members made when the TreeTable is launched.
		self.usedTreeColumns = -1
		self.usedTreeRows = -1
		self.usedColumns = None
		self.usedRows = None
		self.usedCells = None
		self.sortable = None
		self.sortedRow = None

	def addColumn(self, text, callback=None):
		column = TreeTableColumn(text, callback)
		self.columns.append(column)
		return column

	def addRow(self, text, parentRow=None, sortable=False):
		row = TreeTableRow(self, text, parentRow, sortable)
		if parentRow is None:
			self.rows.append(row)
		return row

	def addCell(self, row, col, text, callback=None):
		cell = TreeTableCell(row, col, text, callback)
		row.addCell(cell)
		col.addCell(cell)
		self.cells[(row, col)] = cell

	def getCell(self, row, col):
		return self.cells[(row, col)]

	def setCellText(self, row, col, text):
		self.getCell(row, col).setText(self.tree.hlist, text)

	def launch(self):
		rows = self._flattenRows(self.rows)
		self.sortable = False
		for row in rows:
			if row.sortable:
				self.sortable = True
				break
		if len(self.columns) < 2:
			self.sortable = False	# Can only sort multiple columns
		self._setupTree(rows, self.columns)
		# Copy "used" members after _setupTree so that we
		# can clean up properly from previous setup
		from copy import copy
		self.usedColumns = copy(self.columns)
		self.usedUnsortedColumns = copy(self.columns)
		self.usedRows = copy(self.rows)
		self.usedCells = copy(self.cells)
		hlist = self.tree.hlist
		if self.sortable:
			leadOffset = 2
		else:
			leadOffset = 1
		# Note that columns and rows must be filled in before
		# cells in order to set column indices and row paths
		# before use by cells
		for index, column in enumerate(self.usedColumns):
			column.makeUI(hlist, index + leadOffset)
		self.rowMap = dict()
		for row in rows:
			row.makeUI(hlist, self.sortable)
			self.rowMap[row.getName()] = row
		for cell in self.usedCells.itervalues():
			cell.makeUI(hlist)
		self.tree.autosetmode()
		self.tree.pack(fill="both", expand=True)

	def _flattenRows(self, rows):
		allRows = list()
		for r in rows:
			allRows.append(r)
			if r.subRows:
				allRows.extend(self._flattenRows(r.subRows))
		return allRows

	def _setupTree(self, rows, columns):
		if len(rows) <= 0:
			raise ValueError("Launching empty table")
		# We cannot resize a tree, so if we need more columns,
		# we need to destroy the old one and make a new one
		numColumns = len(columns) + 1	# Add one for "tree" column
		if self.sortable:
			numColumns += 1		# Add one for "sort" column
		if self.tree and numColumns > self.numTreeColumns:
			hlist = self.tree.hlist
			for column in self.usedColumns:
				column.unmakeUI(hlist)
			for row in self.usedRows:
				row.unmakeUI(hlist)
			for cell in self.cells.itervalues():
				cell.unmakeUI(hlist)
			self._destroyImages()
			self.tree.destroy()
			self.tree = None
			self.numTreeColumns = -1
		if self.tree is None:
			from Tix import Tree
			options = (self.options +
					"\nhlist.columns %d" % numColumns)
			self.tree = Tree(self, options=options)
			if self.browsecmd:
				self.tree.hlist.config(browsecmd=self.browsecmd)
			if self.command:
				self.tree.hlist.config(command=self.command)
			self._createImages()
			if self.title:
				self.tree.hlist.header_create(0,
							itemtype="text",
							text=self.title,
							relief="groove")
			if self.sortable:
				self.tree.hlist.header_create(1,
							itemtype="text",
							text=" ",
							relief="flat")
			self.numTreeColumns = self.numUsedColumns = numColumns
			self.numTreeRows = self.numUsedRows = len(rows)
		else:
			hlist = self.tree.hlist
			for i in range(numColumns, self.numUsedColumns):
				self._eraseUsedColumn(hlist, i)
			self.numUsedColumns = numColumns
			for i in range(len(rows), self.numUsedRows):
				self._eraseUsedRow(hlist, i)
			self.numUsedRows = len(rows)

	def _eraseUsedColumn(self, hlist, columnIndex):
		column = self.usedColumns[columnIndex]
		column.unmakeUI(hlist)
		for rowIndex in range(self.numUsedRows):
			cell = self.usedCells[(row, column)]
			cell.unmakeUI(hlist)

	def _eraseUsedRow(self, hlist, rowIndex):
		row = self.usedRows[rowIndex]
		path = row.getName()
		for columnIndex in range(self.numUsedColumns):
			cell = self.usedCells[(row,
						self.usedColumns[columnIndex])]
			cell.unmakeUI(hlist)
		row.unmakeUI(hlist)

	def _destroyImages(self):
		self.imageUnsorted = None
		self.imageSortedAscending = None
		self.imageSortedDescending = None
		self.styleNormalText = None
		self.styleSelectText = None
		self.styleNormalTextimage = None
		self.styleSelectTextimage = None
		self.styleNormalWindow = None
		self.styleSelectWindow = None
		self.styleNormalImage = None
		self.styleSelectImage = None

	def _createImages(self):
		from PIL import Image, ImageDraw, ImageTk
		im = Image.new('1', (12, 12), 0)
		d = ImageDraw.Draw(im)
		d.ellipse((2, 2, 10, 10), fill=1)
		self.imageUnsorted = ImageTk.BitmapImage(im, master=self.tree)
		im = Image.new('1', (12, 12), 0)
		d = ImageDraw.Draw(im)
		d.polygon((1, 1, 10, 5, 1, 10), fill=1)
		self.imageSortedAscending = ImageTk.BitmapImage(im,
							master=self.tree)
		im = Image.new('1', (12, 12), 0)
		d = ImageDraw.Draw(im)
		d.polygon((10, 1, 1, 5, 10, 10), fill=1)
		self.imageSortedDescending = ImageTk.BitmapImage(im,
							master=self.tree)
		import Tix
		self.colorNormal = self.tree.hlist["background"]
		self.colorSelect = self.tree.hlist["selectbackground"]
		normalKw = { "background": self.colorNormal }
		selectKw = { "background": self.colorSelect }
		self.styleNormalText = Tix.DisplayStyle("text", **normalKw)
		self.styleSelectText = Tix.DisplayStyle("text", **selectKw)
		self.styleNormalImagetext = Tix.DisplayStyle("imagetext",
								**normalKw)
		self.styleSelectImagetext = Tix.DisplayStyle("imagetext",
								**selectKw)
		self.styleNormalWindow = Tix.DisplayStyle("window", **normalKw)
		self.styleSelectWindow = Tix.DisplayStyle("window", **selectKw)
		self.styleNormalImage = Tix.DisplayStyle("image", **normalKw)
		self.styleSelectImage = Tix.DisplayStyle("image", **selectKw)

	def reorderColumns(self, columns=None):
		if columns is None:
			columns = self.usedUnsortedColumns
		if columns == self.usedColumns:
			# Set to be the same as current order
			return
		if self.sortable:
			leadOffset = 2
		else:
			leadOffset = 1
		hlist = self.tree.hlist
		# Relocate all the columns first to establish
		# the correct column indices, then move the cells
		for column in columns:
			column.preRelocate(hlist)
		for index, column in enumerate(columns):
			column.relocate(hlist, index + leadOffset)
		for column in columns:
			column.relocateCells(hlist)
		from copy import copy
		self.usedColumns = copy(columns)

	def sortingRow(self, row):
		if self.sortedRow != row and self.sortedRow is not None:
			self.sortedRow.setUnsorted()
		if row.sortState is None:
			self.sortedRow = None
		else:
			self.sortedRow = row

	def selectedRows(self):
		return [ self.rowMap[path]
				for path in self.tree.hlist.info_selection() ]

	def highlightCell(self, cell, on):
		cell.highlight(self, self.tree.hlist, on)

	def highlightRow(self, row, on, deselect=True):
		row.highlight(self, self.tree.hlist, on, deselect)

	def highlightColumn(self, column, on):
		column.highlight(self, self.tree.hlist, on)

	def clearHighlights(self):
		self.tree.hlist.selection_clear()

	def openRow(self, row):
		self.tree.open(row.name)

	def displayRow(self, row):
		if row.parent is not None:
			self.openRow(row.parent)
			self.displayRow(row.parent)

	def makeVisible(self, row):
		self.tree.hlist.yview(row.name)


class TreeTableColumn:

	def __init__(self, text, callback=None):
		self.text = text
		self.callback = callback
		self.label = None
		self.columnIndex = None
		self.cells = list()

	def __repr__(self):
		return "<TreeTableColumn '%s'>" % self.text

	def addCell(self, cell):
		self.cells.append(cell)

	def makeUI(self, hlist, columnIndex):
		self.columnIndex = columnIndex
		if self.callback:
			if self.label is None:
				import Tkinter
				self.label = Tkinter.Label(hlist,
							text=self.text,
							relief="flat",
							bg=hlist["background"])
				def cb(event, callback=self.callback):
					callback(self)
				self.label.bind("<Button-1>", cb)
			hlist.header_create(columnIndex,
						itemtype="window",
						window=self.label,
						relief="groove")
		else:
			hlist.header_create(columnIndex,
						itemtype="text",
						text=self.text,
						relief="groove")

	def unmakeUI(self, hlist):
		hlist.header_delete(self.columnIndex)
		if self.label:
			self.label.destroy()
			self.label = None

	def preRelocate(self, hlist):
		hlist.header_delete(self.columnIndex)
		for cell in self.cells:
			hlist.item_delete(cell.row.getName(), self.columnIndex)

	def relocate(self, hlist, columnIndex):
		self.makeUI(hlist, columnIndex)

	def relocateCells(self, hlist):
		for cell in self.cells:
			cell.relocate(hlist)

	def highlight(self, table, hlist, on):
		if on:
			color = table.colorSelect
		else:
			color = table.colorNormal
		if self.label:
			self.label.config(background=color)
		hlist.header_configure(self.columnIndex, headerbackground=color)


class TreeTableRow:

	RowIdentifierId = 0

	def __init__(self, table, text, parent, sortable):
		self.table = table
		self.text = text
		self.parent = parent
		self.sortable = sortable
		self.name = None
		self.subRows = list()
		self.label = None
		self.cells = list()
		self.sortState = None
		self._sortCache = None
		if parent:
			parent.addSubRow(self)

	def addSubRow(self, row):
		self.subRows.append(row)

	def getName(self):
		return self.name

	def setName(self, name):
		self.name = name

	def makeName(self):
		self.name = "row%d" % TreeTableRow.RowIdentifierId
		TreeTableRow.RowIdentifierId += 1
		return self.name

	def addCell(self, cell):
		self.cells.append(cell)
		self._sortCache = None

	def makeUI(self, hlist, sortable):
		if self.parent is None:
			add = hlist.add
			path = self.makeName()
		else:
			add = hlist.add_child
			path = self.parent.getName()
		path = add(path, itemtype="text", text=self.text)
		if self.parent is not None:
			self.setName(path)
			hlist.hide_entry(path)
		if not sortable or not self.sortable:
			return
		import Tkinter
		bg = hlist["background"]
		self.label = Tkinter.Label(hlist, bg=bg, relief="flat",
						image=self.table.imageUnsorted)
		self.label.pack(side="left", fill="x")
		self.label.bind("<Button-1>", self._sortCB)
		self.sortState = None
		hlist.item_create(path, 1, itemtype="window", window=self.label)

	def unmakeUI(self, hlist):
		if self.label:
			self.label.destroy()
			self.label = None
		hlist.item_delete(self.name, 0)

	def _sortCB(self, event=None):
		if self.sortState is None:
			self.sortState = "up"
		elif self.sortState == "up":
			self.sortState = "down"
		elif self.sortState == "down":
			self.sortState = None
		if self.sortState is None:
			self.label.config(image=self.table.imageUnsorted)
			self.table.reorderColumns()
		elif self.sortState == "up":
			self.label.config(image=self.table.imageSortedAscending)
			sortArray = self._getSortColumns()
			sortArray.sort(_ascendingCmp)
			columns = [ col for value, col in sortArray ]
			self.table.reorderColumns(columns)
		elif self.sortState == "down":
			self.label.config(image=self.table.imageSortedDescending)
			sortArray = self._getSortColumns()
			sortArray.sort(_descendingCmp)
			columns = [ col for value, col in sortArray ]
			self.table.reorderColumns(columns)
		self.table.sortingRow(self)

	def _getSortColumns(self):
		if self._sortCache is not None:
			return self._sortCache
		valueMap = dict([ (cell.col, cell.sortValue())
					for cell in self.cells ])
		for col in self.table.usedColumns:
			if col not in valueMap:
				valueMap[col] = None
		self._sortCache = [ (value, col)
					for col, value in valueMap.iteritems() ]
		return self._sortCache

	def setUnsorted(self):
		if self.sortable:
			self.sortState = None
			self.label.config(image=self.table.imageUnsorted)

	def highlight(self, table, hlist, on, deselect=True):
		if deselect:
			hlist.selection_clear()
		if on:
			hlist.selection_set(self.name)

def _descendingCmp(left, right):
	if left is None:
		if right is None:
			return 0
		return 1
	if right is None:
		return -1
	return cmp(left, right)

def _ascendingCmp(left, right):
	if left is None:
		if right is None:
			return 0
		return -1
	if right is None:
		return 1
	return -cmp(left, right)


class TreeTableCell:
	
	def __init__(self, row, col, text, callback):
		self.row = row
		self.col = col
		self.text = text
		self.callback = callback
		self.label = None
		self._sortValue = None

	def sortValue(self):
		if self._sortValue is None:
			try:
				self._sortValue = float(self.text)
			except ValueError:
				self._sortValue = self.text
		return self._sortValue

	def makeUI(self, hlist):
		path = self.row.getName()
		columnIndex = self.col.columnIndex
		if self.callback:
			if self.label is None:
				import Tkinter
				self.label = Tkinter.Label(hlist, text=self.text,
							relief="flat",
							bg=hlist["background"])
				def cb(event, callback=self.callback):
					callback(self)
				self.label.bind("<Button-1>", cb)
			hlist.item_create(path, columnIndex,
						itemtype="window",
						window=self.label)
		else:
			hlist.item_create(path, columnIndex,
						itemtype="text",
						text=self.text)

	def unmakeUI(self, hlist):
		if self.label:
			self.label.destroy()
			self.label = None
		hlist.item_delete(self.row.getName(), self.col.columnIndex)

	def setText(self, hlist, text):
		self.text = text
		path = self.row.getName()
		columnIndex = self.col.columnIndex
		hlist.item_configure(path, columnIndex, text=self.text)

	def relocate(self, hlist):
		self.makeUI(hlist)

	def highlight(self, table, hlist, on):
		if self.label:
			if on:
				style = table.styleSelectWindow
				color = table.colorSelect
			else:
				style = table.styleNormalWindow
				color = table.colorNormal
			self.label.config(background=color)
		else:
			if on:
				style = table.styleSelectText
			else:
				style = table.styleNormalText
		hlist.item_configure(self.row.getName(),
					self.col.columnIndex,
					style=style)

if __name__ == "chimeraOpenSandbox":
	from chimera.baseDialog import ModelessDialog
	class TreeTableDialog(ModelessDialog):

		def __init__(self, text, dialogKw={}, *args, **kw):
			self.text = text
			self._htArgs = (args, kw)
			ModelessDialog.__init__(self, **dialogKw)

		def fillInUI(self, parent):
			args, kw = self._htArgs
			del self._htArgs
			self.treeTable = TreeTable(parent, self.text, *args, **kw)
			self.treeTable.pack(fill="both", expand=True)

	def cb(cell):
		print "cb", cell

	d = TreeTableDialog("Restraint", header=True, selectMode="extended")
	tt = d.treeTable
	f0Col = tt.addColumn("Frame 0")
	f1Col = tt.addColumn("Frame 1")
	row0 = tt.addRow("First", sortable=False)
	tt.addCell(row0, f0Col, 1.2)
	tt.addCell(row0, f1Col, 1.3)
	row1 = tt.addRow("Second", sortable=False)
	tt.addCell(row1, f0Col, 10.2, callback=cb)
	tt.addCell(row1, f1Col, 10.1, callback=cb)
	row01 = tt.addRow("First.First", parentRow=row0, sortable=True)
	tt.addCell(row01, f0Col, 100.2)
	tt.addCell(row01, f1Col, 100.2)
	tt.launch()
