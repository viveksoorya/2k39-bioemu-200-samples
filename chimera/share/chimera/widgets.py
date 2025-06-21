# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: widgets.py 41686 2018-03-16 20:14:40Z pett $

"""various useful chimera-specific widgets"""

import chimera
import Pmw
from CGLtk.Table import SortableTable

class ModelListBase:
	def __init__(self):
		from chimera import openModels as om, triggers
		if not hasattr(self, '_triggers'):
			self._triggers = [
				(om.triggers, om.ADDMODEL,
						self._modelsChange, None),
				(om.triggers, om.REMOVEMODEL,
						self._modelsChange, None),
				(triggers, 'Model', self._modelRename, None),
			]
		self._handlers = []

		# the widget half of the class needs to have it's __init__
		# called first so that this will work...
		if isinstance(self, SortableTable):
			self.bind('<Map>', self.__map)
			self.bind('<Unmap>', self.__unmap)
		else:
			hull = self.component('hull')
			hull.bind('<Map>', self.__map)
			hull.bind('<Unmap>', self.__unmap)

	def refresh(self):
		# can be needed if 'filtFunc' specified
		self._modelsChange()

	def __map(self, event):
		if self._handlers:
			return
		for triggers, trigName, cb, data in getattr(self, '_triggers',
									[]):
			self._handlers.append((triggers, trigName,
				triggers.addHandler(trigName, cb, data)))
		self._modelsChange()

	def _sleepCheck(self, doCallback=True):
		if not self._handlers and not hasattr(self, '_recursion'):
			# the list maintenance code is "asleep" (i.e. we're
			# unmapped -- force an update
			self._recursion = True
			self._modelsChange(doCallback=doCallback)
			delattr(self, '_recursion')

	def __unmap(self, event):
		self._deleteHandlers()

	def _modelRename(self, trigger, x, changes):
		if 'name changed' in changes.reasons:
			self._modelsChange()

	def _deleteHandlers(self):
		if not self._handlers:
			return
		while self._handlers:
			triggers, trigName, handler = self._handlers.pop()
			triggers.deleteHandler(trigName, handler)

	def destroy(self):
		if chimera:
			self._deleteHandlers()
			try:
				self.itemMap.clear()
				self.valueMap.clear()
			except AttributeError:
				# attributes may be unset because widget was
				# never displayed (eg in a tab that was
				# never exposed)
				pass

class ModelScrolledListBoxBase(ModelListBase, Pmw.ScrolledListBox):
	"""maintain a list of items dependent on molecules/models

	   keep list up to date as molecules are opened and closed
	   while keeping the selected item the same

	   'autoselect' keyword controls what happens when nothing would
	   be selected.  If 'single', then if there is exactly one item it
	   will be selected and otherwise the selection remains empty.  If
	   'all' then all items will become selected.  If None, the selection
	   remains empty.  Default: 'all' for molecules and None for chains.

	   _itemNames() needs to be implemented by subclasses
	"""

	ExtendedBalloonHelp = "Click to choose item\n" \
		"Drag to choose range\n" \
		"Control-click to toggle item\n" \
		"Shift-click to choose range\n  (starting from previous item)"

	def __init__(self, *args, **kw):
		kw['listbox_exportselection'] = 0
		# a disabled listbox won't show the initial items...
		if 'listbox_state' in kw:
			state = kw['listbox_state']
			del kw['listbox_state']
		else:
			state = 'normal'
		if 'autoselect' in kw:
			self.autoselect = kw['autoselect']
			del kw['autoselect']
		else:
			self.autoselect = self.autoselectDefault
		balloonDefault = \
			kw.get('listbox_selectmode', 'browse').lower() == 'extended'
		balloon = kw.pop("balloon", balloonDefault)
		balloonText = kw.pop("balloonText", self.ExtendedBalloonHelp)
		Pmw.ScrolledListBox.__init__(self, *args, **kw)
		listbox = self.component('listbox')
		listbox.config(state=state)
		if balloon:
			from help import register
			register(listbox, balloon=balloonText)
		ModelListBase.__init__(self)

	config = configure = Pmw.ScrolledListBox.configure

	def destroy(self):
		ModelListBase.destroy(self)
		Pmw.ScrolledListBox.destroy(self)

	def get(self, *args, **kw):
		self._sleepCheck()
		val = Pmw.ScrolledListBox.get(self, *args, **kw)
		if isinstance(val, basestring):
			val = [val]
		return map(lambda m: self.itemMap[m], val)

	def getvalue(self):
		self._sleepCheck()
		itemName = Pmw.ScrolledListBox.getvalue(self)
		if self.component('listbox').cget('selectmode') in [
							'multiple', 'extended']:
			return map(lambda m: self.itemMap[m], itemName)
		if itemName:
			return self.itemMap[itemName[0]]
		return None

	def setvalue(self, val, doCallback=True):
		if not isinstance(val, list):
			if isinstance(val, (tuple, set)):
				val = list(val)
			elif val is None:
				val = []
			else:
				val = [val]
		if not val or isinstance(val[0], basestring):
			Pmw.ScrolledListBox.setvalue(self, val)
		else:
			self._sleepCheck(doCallback)
			Pmw.ScrolledListBox.setvalue(self,
				[self.valueMap[v] for v in val if self.filtFunc(v)])

	def _modelsChange(self, *args, **kw):
		state = self.cget('listbox_state')
		self.component('listbox').config(state='normal')
		delRecursion = False
		if not hasattr(self, '_recursion'):
			self._recursion = True
			delRecursion = True
		prevVal = self.getvalue()
		sel = Pmw.ScrolledListBox.getvalue(self)
		items = self._itemNames()
		filtered = list(filter(lambda s: s in items, sel))
		if self.autoselect:
			if self.autoselect == "single":
				if not filtered and len(items) == 1:
					filtered = items
			elif self.autoselect == "all":
				if not filtered:
					filtered = items
		self.setlist(items)
		self.setvalue(filtered)
		curVal = self.getvalue()
		if delRecursion:
			delattr(self, '_recursion')
		if self['selectioncommand'] and (tuple(filtered) != tuple(sel)
				or curVal != prevVal):
			if 'doCallback' not in kw or kw['doCallback']:
				self['selectioncommand']()
		self.component('listbox').config(state=state)

class ModelOptionMenuBase(ModelListBase, Pmw.OptionMenu):
	"""maintain a menu of items dependent on molecules/models

	   keep menu up to date as molecules are opened and closed
	   while keeping the selected item the same

	   _itemNames() needs to be implemented by subclasses
	"""

	def __init__(self, *args, **kw):
		kw['items'] = self._itemNames()
		if 'initialitem' in kw:
			item = kw['initialitem']
			if isinstance(item, chimera.Selectable):
				kw['initialitem'] = self.valueMap[item]
		elif kw['items']:
			kw['initialitem'] = 0
		if 'command' in kw and kw['command']:
			kw['command'] = lambda txt, cb=kw['command']: \
							cb(self.getvalue())
		Pmw.OptionMenu.__init__(self, *args, **kw)
		ModelListBase.__init__(self)

	def configure(self, *args, **kw):
		if 'command' in kw and kw['command']:
			kw['command'] = lambda txt, cb=kw['command']: \
							cb(self.getvalue())
		Pmw.OptionMenu.configure(self, *args, **kw)
	config = configure

	def destroy(self):
		ModelListBase.destroy(self)
		Pmw.OptionMenu.destroy(self)

	def getvalue(self):
		self._sleepCheck()
		itemName = Pmw.OptionMenu.getvalue(self).decode('utf-8')
		if itemName:
			return self.itemMap[itemName]
		return None

	def invoke(self, index=Pmw.SELECT):
		if index == Pmw.SELECT:
			if self['command']:
				# can't Pmw.invoke on an itemless menu,
				# so just in case...
				return self['command']("ignored")
		elif isinstance(index, int):
			return Pmw.OptionMenu.invoke(self, index)
		else:
			if isinstance(index, basestring):
				Pmw.OptionMenu.setvalue(self, index)
			else:
				self._sleepCheck()
				Pmw.OptionMenu.setvalue(self,
							self.valueMap[index])
			return Pmw.OptionMenu.invoke(self)
		
	def setvalue(self, val):
		if isinstance(val, basestring):
			Pmw.OptionMenu.setvalue(self, val)
		else:
			self._sleepCheck()
			Pmw.OptionMenu.setvalue(self, self.valueMap[val])
			Pmw.OptionMenu.invoke(self)

	def _modelsChange(self, *args, **kw):
		pre = Pmw.OptionMenu.getvalue(self)
		preVal = self.itemMap.get(pre, None)
		items = self._itemNames()
		self.setitems(items)
		from tkgui import windowSystem
		if windowSystem == 'x11':
			# On X11 menus do not scroll.  Use multiple columns.
			m = self.component('menu')
			entries_per_column = 35
			for i in range(entries_per_column, len(items),
				       entries_per_column):
				m.entryconfigure(i, columnbreak = 1)
		post = Pmw.OptionMenu.getvalue(self)
		postVal = self.itemMap.get(post, None)
		if (pre != post or preVal != postVal) and self['command']:
			if 'doCallback' not in kw or kw['doCallback']:
				self.invoke()

class ModelSortableTableBase(ModelListBase, SortableTable):
	"""maintain a table of items dependent on molecules/models

	   keep list up to date as molecules are opened and closed
	   while keeping the selected item the same

	   'autoselect' keyword controls what happens when nothing would
	   be selected.  If 'single', then if there is exactly one item it
	   will be selected and otherwise the selection remains empty.  If
	   'all' then all items will become selected.  If None, the selection
	   remains empty.  Default: 'all' for molecules and None for chains.

	   _itemNames() needs to be implemented by subclasses
	"""

	def __init__(self, *args, **kw):
		if 'autoselect' in kw:
			self.autoselect = kw['autoselect']
			del kw['autoselect']
		else:
			self.autoselect = self.autoselectDefault
		SortableTable.__init__(self, *args, **kw)
		ModelListBase.__init__(self)

	config = configure = SortableTable.configure

	def destroy(self):
		ModelListBase.destroy(self)
		SortableTable.destroy(self)

	def launch(self, *args, **kw):
		self.addColumn(self.columnTitle, lambda v, s=self: s.valueMap[v])
		values = [ self.itemMap[item] for item in self._itemNames() ]
		SortableTable.setData(self, values)
		SortableTable.launch(self, *args, **kw)
		if self.autoselect and self.data:
			if self.autoselect == "all" or (
			self.autoselect == "single" and len(self.data) == 1):
				self.select(self.data)
				if self.userBrowseCmd:
					self.userBrowseCmd(self.data)

	def refresh(self, *args, **kw):
		# allow calls internal to SortableTable
		if self._stInternalCall():
			SortableTable.refresh(self, *args, **kw)
		else:
			raise AssertionError("Direct use of refresh method illegal for %s"
				% self.__class__.__name__)

	def select(self, *args, **kw):
		self._sleepCheck()
		return SortableTable.select(self, *args, **kw)

	def selected(self, *args, **kw):
		self._sleepCheck()
		return SortableTable.selected(self, *args, **kw)

	def setData(self, *args, **kw):
		# allow calls internal to SortableTable
		if self._stInternalCall():
			SortableTable.setData(self, *args, **kw)
		else:
			raise AssertionError("Direct use of setData method illegal for %s"
				% self.__class__.__name__)

	def _modelsChange(self, *args, **kw):
		delRecursion = False
		if not hasattr(self, '_recursion'):
			self._recursion = True
			delRecursion = True
		prevVal = self.selected()
		items = self._itemNames()
		filtered = [pv for pv in prevVal if pv in self.valueMap]
		if self.autoselect:
			if self.autoselect == "single":
				if not filtered and len(self.valueMap) == 1:
					filtered = self.valueMap.keys()
			elif self.autoselect == "all":
				if not filtered:
					filtered = self.valueMap.keys()
		values = [ self.itemMap[item] for item in self._itemNames() ]
		SortableTable.setData(self, values)
		self.select(filtered)
		if delRecursion:
			delattr(self, '_recursion')
		if self.userBrowseCmd and filtered != prevVal:
			if 'doCallback' not in kw or kw['doCallback']:
				self.userBrowseCmd(filtered)

	def _stInternalCall(self):
		import inspect
		import os.path
		stack = inspect.stack()
		head, fname = os.path.split(stack[2][1])
		del stack
		if head:
			folder = os.path.split(head)[-1]
		else:
			return False
		return folder == "CGLtk" and fname.startswith("Table.py")

class ModelItems:
	columnTitle = "Model"
	def __init__(self, listFunc=chimera.openModels.list, sortFunc=None,
					filtFunc=lambda m: True, **kw):
		self.listFunc = listFunc
		self.filtFunc = filtFunc
		if sortFunc is None:
			from chimera.misc import oslModelCmp
			sortFunc = lambda m1, m2: oslModelCmp(m1.oslIdent(),
								m2.oslIdent())
		self.sortFunc = sortFunc
		self._remKw = kw

	def _itemNames(self):
		self.itemMap = {}
		self.valueMap = {}
		models = [m for m in self.listFunc() if self.filtFunc(m)]
		models.sort(self.sortFunc)
		items = []
		for m in models:
			if isinstance(m, chimera.Model):
				# below works if m.name is u'71B6\u4eee1'
				# so I don't know why I thought I needed
				# m.name.decode('utf8') before
				item = "%s (%s)" % (m.name, m.oslIdent())
			else:
				item = m
			self.itemMap[item] = m
			self.valueMap[m] = item
			items.append(item)
		return items

class MoleculeItems(ModelItems):
	columnTitle = "Model"
	def __init__(self, **kw):
		f = lambda m: isinstance(m,  chimera.Molecule) and getattr(m, "isRealMolecule", True)
		if 'filtFunc' in kw:
			kw['filtFunc'] = lambda m, f=f, ff=kw['filtFunc']: f(m) and ff(m)
		else:
			kw['filtFunc'] = f
		ModelItems.__init__(self, **kw)

class MoleculeChainItems:
	columnTitle = "Chain"
	def __init__(self, filtFunc=lambda m: True, **kw):
		self.filtFunc = filtFunc
		self._remKw = kw
		# actually override the triggers of ModelListBase
		self._triggers = [(chimera.triggers, 'Residue',
							self._resCB, None)]

	def _itemNames(self):
		self.itemMap = {}
		self.valueMap = {}
		molecules = chimera.openModels.list(
						modelTypes=[chimera.Molecule])
		from chimera.misc import oslModelCmp
		molecules.sort(lambda m1, m2: oslModelCmp(m1.oslIdent(),
								m2.oslIdent()))
		items = []
		for m in molecules:
			for s in m.sequences():
				if not self.filtFunc(s):
					continue
				item = s.fullName()
				self.itemMap[item] = s
				self.valueMap[s] = item
				items.append(item)
		return items

	def _resCB(self, trigName, myData, trigData):
		if trigData.created or trigData.deleted or 'id changed' in trigData.reasons:
			# delay until sequences are up to date
			def cb(*args):
				from triggerSet import ONESHOT
				self._modelsChange()
				return ONESHOT
			chimera.triggers.addHandler('new frame', cb, None)

class AtomItems:
	columnTitle = "Atom"
	def __init__(self, filtFunc=lambda m: True, **kw):
		self.filtFunc = filtFunc
		self.addNumbering = kw.pop('numbering', False)
		self._remKw = kw
		# actually override the triggers of ModelListBase
		self._triggers = [(chimera.triggers, 'Atom', self._atomCB, None)]

	def _atomCB(self, trigName, myData, trigData):
		if trigData.created or trigData.deleted:
			self._modelsChange()

	def _itemNames(self):
		self.itemMap = {}
		self.valueMap = {}
		filtFunc = self.filtFunc
		atoms = [a for m in chimera.openModels.list(modelTypes=
			[chimera.Molecule]) for a in m.atoms if filtFunc(a)]
		from chimera.misc import oslCmp
		atoms.sort(lambda a1, a2: oslCmp(a1.oslIdent(), a2.oslIdent()))
		items = []
		for i, a in enumerate(atoms):
			item = str(a)
			if self.addNumbering:
				item += " (%d/%d)" % (i+1, len(atoms))
			self.itemMap[item] = a
			self.valueMap[a] = item
			items.append(item)
		return items

class MetalItems(AtomItems):
	columnTitle = "Metal"
	def __init__(self, **kw):
		from elements import metals
		f = lambda a, metals=metals: a.element in metals
		if 'filtFunc' in kw:
			kw['filtFunc'] = lambda a, f=f, ff=kw['filtFunc']: f(a) and ff(a)
		else:
			kw['filtFunc'] = f
		AtomItems.__init__(self, **kw)

	def _atomCB(self, trigName, myData, trigData):
		if trigData.created or trigData.deleted \
		or 'element changed' in trigData.reasons:
			self._modelsChange()

class ExtendedModelItems(ModelItems):
	def __init__(self, labels=[], **kw):
		from chimera.misc import oslModelCmp
		def sortFunc(m1, m2):
			m1IsStr = isinstance(m2, basestring)
			m2IsStr = isinstance(m1, basestring)
			if m1IsStr and m2IsStr:
				return cmp(m1, m2)
			if m1IsStr:
				return -1
			if m2IsStr:
				return 1
			return oslModelCmp(m1.oslIdent(), m2.oslIdent())
		kw['sortFunc'] = kw.pop('sortFunc', sortFunc)
		kw['listFunc'] = lambda labs=labels, f=kw.pop('listFunc',
					chimera.openModels.list): labs+f()
		ModelItems.__init__(self, **kw)

class ExtendedMoleculeItems(ExtendedModelItems):
	def __init__(self, **kw):
		kw['listFunc'] = kw.pop('listFunc', lambda:
			chimera.openModels.list(modelTypes=[chimera.Molecule]))
		ExtendedModelItems.__init__(self, **kw)

class MoleculeScrolledListBox(ModelScrolledListBoxBase, MoleculeItems):
	autoselectDefault = "all"
	def __init__(self, master, listbox_height=4, **kw):
		MoleculeItems.__init__(self, **kw)
		ModelScrolledListBoxBase.__init__(self, master,
					listbox_height=listbox_height, **kw)

class MoleculeChainScrolledListBox(ModelScrolledListBoxBase,
							MoleculeChainItems):
	autoselectDefault = None
	def __init__(self, master, listbox_height=8, **kw):
		MoleculeChainItems.__init__(self, **kw)
		ModelScrolledListBoxBase.__init__(self, master,
				listbox_height=listbox_height, **self._remKw)

class ModelScrolledListBox(ModelScrolledListBoxBase, ModelItems):
	autoselectDefault = "all"
	def __init__(self, master, listbox_height=4, **kw):
		ModelItems.__init__(self, **kw)
		ModelScrolledListBoxBase.__init__(self, master,
				listbox_height=listbox_height, **self._remKw)

class MetalScrolledListBox(ModelScrolledListBoxBase, MetalItems):
	autoselectDefault = None
	def __init__(self, master, listbox_height=8, **kw):
		MetalItems.__init__(self, **kw)
		ModelScrolledListBoxBase.__init__(self, master,
				listbox_height=listbox_height, **self._remKw)

class MoleculeOptionMenu(ModelOptionMenuBase, MoleculeItems):
	def __init__(self, *args, **kw):
		MoleculeItems.__init__(self, **kw)
		ModelOptionMenuBase.__init__(self, *args, **self._remKw)

class MoleculeChainOptionMenu(ModelOptionMenuBase, MoleculeChainItems):
	def __init__(self, *args, **kw):
		MoleculeChainItems.__init__(self, **kw)
		ModelOptionMenuBase.__init__(self, *args, **self._remKw)

class MetalOptionMenu(ModelOptionMenuBase, MetalItems):
	def __init__(self, *args, **kw):
		MetalItems.__init__(self, **kw)
		ModelOptionMenuBase.__init__(self, *args, **self._remKw)

class ModelSortableTable(ModelSortableTableBase, ModelItems):
	autoselectDefault = "all"
	def __init__(self, *args, **kw):
		ModelItems.__init__(self, **kw)
		ModelSortableTableBase.__init__(self, *args, **self._remKw)

class MoleculeSortableTable(ModelSortableTableBase, MoleculeItems):
	autoselectDefault = "all"
	def __init__(self, *args, **kw):
		MoleculeItems.__init__(self, **kw)
		ModelSortableTableBase.__init__(self, *args, **self._remKw)

class MoleculeChainSortableTable(ModelSortableTableBase, MoleculeChainItems):
	autoselectDefault = None
	def __init__(self, *args, **kw):
		MoleculeChainItems.__init__(self, **kw)
		ModelSortableTableBase.__init__(self, *args, **self._remKw)

class MetalSortableTable(ModelSortableTableBase, MetalItems):
	autoselectDefault = None
	def __init__(self, *args, **kw):
		MetalItems.__init__(self, **kw)
		ModelSortableTableBase.__init__(self, *args, **self._remKw)

class ModelOptionMenu(ModelOptionMenuBase, ModelItems):
	def __init__(self, *args, **kw):
		ModelItems.__init__(self, **kw)
		ModelOptionMenuBase.__init__(self, *args, **self._remKw)

class ExtendedModelOptionMenu(ModelOptionMenuBase, ExtendedModelItems):
	def __init__(self, *args, **kw):
		ExtendedModelItems.__init__(self, **kw)
		ModelOptionMenuBase.__init__(self, *args, **self._remKw)

class ExtendedMoleculeOptionMenu(ModelOptionMenuBase, ExtendedMoleculeItems):
	def __init__(self, *args, **kw):
		ExtendedMoleculeItems.__init__(self, **kw)
		ModelOptionMenuBase.__init__(self, *args, **self._remKw)

class NewModelOptionMenu(ExtendedModelOptionMenu):
	def __init__(self, *args, **kw):
		kw['labels'] = kw.pop('labels', ["new model"])
		ExtendedModelOptionMenu.__init__(self, *args, **kw)

class NewMoleculeOptionMenu(ExtendedMoleculeOptionMenu):
	def __init__(self, *args, **kw):
		kw['labels'] = kw.pop('labels', ["new model"])
		ExtendedMoleculeOptionMenu.__init__(self, *args, **kw)

import Tkinter
class DisclosureFrame(Tkinter.Frame):

	def __init__(self, master, **kw):
		Tkinter.Frame.__init__(self, master)
		self.columnconfigure(0, weight=1)
		self.rowconfigure(1, weight=1)
		self._expandedVar = Tkinter.IntVar(master)
		try:
			collapsed = kw["collapsed"]
		except KeyError:
			collapsed = True
		else:
			del kw['collapsed']
		try:
			self.collapseCmd = kw["collapsecmd"]
		except KeyError:
			self.collapseCmd = None
		self._expandedVar.set(not collapsed)
		kw["variable"] = self._expandedVar
		kw["command"] = self.collapseChange
		kw["indicatoron"] = False
		kw["anchor"] = "w"
		kw["justify"] = "left"
		kw["selectcolor"] = ""
		kw["relief"] = "flat"
		kw["offrelief"] = kw["relief"]
		self.header = Tkinter.Checkbutton(self, **kw)
		self.header.grid(row=0, sticky="ew")
		from chimera import chimage
		self._rightarrow = chimage.get("rightarrow.png", self.header)
		self.header.config(image=self._rightarrow)
		self._downarrow = chimage.get("downarrow.png", self.header)
		self.header.config(selectimage=self._downarrow)
		self.header.config(compound="left")
		self.frame = Tkinter.Frame(self)
		self.collapseChange()

	def collapseChange(self):
		if self._expandedVar.get():
			self.config(relief="groove", bd=2)
			self.frame.grid(row=1, sticky="nsew")
			if self.collapseCmd:
				self.collapseCmd(self, False)
		else:
			self.config(relief="flat", bd=0)
			self.frame.grid_forget()
			if self.collapseCmd:
				self.collapseCmd(self, True)

	def isCollapsed(self):
		return not self._expandedVar.get()

	def enable(self):
		self.header.config(state="normal")

	def disable(self):
		self.header.config(state="disabled")
