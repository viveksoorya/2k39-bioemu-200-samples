"""
This module consists of three main classes: Preferences, Category and Option.
There is also a utility class: HiddenCategory.

Preferences handles the overall tasks of managing the user interface panel,
loading and saving preferences values to files.  It does so by dividing the
values into categories, each of which consists of a list of options.

Each option saves three values: the factory "default" value, the per-user
"saved" value, and the "current" value.  When saving an option value to
file, it's the "saved" value that gets written.  When operating Chimera,
it's the "current" value that determines the program behavior.  This
separation is important because sometimes the values are different; for
example, when a session is loaded, the "current" preferences values are
set, but not the "saved" values.

HiddenCategory is for simplifying use of Preferences for extensions.
To save extension-specific options, the extension can create an instance
of HiddenCategory and use it like a dictionary.  Any changes to the
category is automatically saved.  Option values must be "normal" Python
types that can be written using repr and recreated via eval.

"""

import sys
import os
import pprint
from chimera.replyobj import reportException as showException

class Option:
	"Option is one value managed by a single UI element"

	def __init__(self, cat, defValue, callback, closure, UIkw={}):
		"Initialize option in category."

		self._cat = cat
		self._default = defValue
		self._savedValue = defValue
		self._callback = callback
		self._closure = closure
		self.value = defValue
		self._ui = None
		self._UIkw = UIkw
		if closure and hasattr(closure[0], 'prefConv'):
			self.valToPref, self.prefToVal = closure[0].prefConv
		else:
			self.valToPref = self.prefToVal = None
		if self.valToPref:
			self.value = self._savedValue = self.valToPref(defValue)

	def set(self, value, fromTkoption=False, asSaved=False, fromPref=False):
		"Set value of option."

		if not fromTkoption and self._ui:
			if fromPref and self.prefToVal:
				self._ui.set(self.prefToVal(value))
			else:
				self._ui.set(value)
		if not fromPref and self.valToPref:
			value = self.valToPref(value)
		if self.value == value:
			return
		self.value = value
		if self._callback:
			self._callback(self)
		if asSaved:
			self.makeCurrentSaved()

	def get(self, forPrefSave=False):
		"Retrieve value of option."

		if self.prefToVal and not forPrefSave:
			return self.prefToVal(self.value)
		return self.value

	def savedValue(self, forPrefSave=False):
		"Return saved value of option."

		if self.prefToVal and not forPrefSave:
			return self.prefToVal(self._savedValue)
		return self._savedValue

	def defaultValue(self):
		"Return default value of option."

		return self._default

	def closure(self):
		"Return instance data for option."

		return self._closure

	def setClosure(self, closure):
		"Set instance data for option."

		self._closure = closure

	def ui(self):
		"Return the user interface element for this option"

		return self._ui

	def setUI(self, ui):
		"Set the user interface element for this option"

		self._ui = ui

	def destroy(self):
		"Destroy this option."

		pass
	
	def UIkw(self):
		"Return keyword dictionary to use when creating this option UI"

		return self._UIkw

	def makeCurrentSaved(self):
		"Make current value be the saved value."

		self._savedValue = self.value

	def resetValue(self):
		"Set current value from default value."

		self.set(self._default)

	def restoreValue(self):
		"Set current value from saved value."

		self.set(self._savedValue, fromPref=True)


class Category:
	"Category manages a list of options"

	def __init__(self, pref, onDisplay=None, onHide=None):
		"Initialize category with no options."

		self._pref = pref
		self._options = {}
		self._unknownOpts = {}
		self._order = None
		self._ui = None
		self._loaded = 0
		self._onDisplay = onDisplay
		self._onHide = onHide

	def add(self, name, defaultValue, callback, closure, UIkw={},
			optionFactory=Option, optKw={}, notifyUI=True):
		"Add an option to this category."

		self._options[name] = optionFactory(self, defaultValue,
					callback, closure, UIkw=UIkw, **optKw)
		self._destroyUI(notifyUI)

	def remove(self, name, notifyUI=True):
		"Remove an option from this category."

		self._options[name].destroy()
		del self._options[name]
		self._destroyUI(notifyUI)

	def set(self, name, value, **kw):
		"Set value of a named option."

		self._options[name].set(value, **kw)

	def get(self, name, forPrefSave=False):
		"Retrieve value of named option."

		return self._options[name].get(forPrefSave=forPrefSave)

	def getOption(self, name):
		"Retrieve named option."

		return self._options[name]

	def options(self):
		"Return list of option names."

		return self._options.keys()

	def setOrder(self, order):
		"Set the order of presentation of options."

		if self._order == order:
			return
		self._order = order
		self._destroyUI(notifyUI=True)

	def destroy(self, notifyUI=True):
		"Destroy this category."

		self._destroyUI(notifyUI)
		for o in self._options.values():
			o.destroy()

	def _destroyUI(self, notifyUI):
		if not self._ui:
			return
		for opt in self._options.values():
			opt.setUI(None)
		self._ui.destroy()
		self._ui = None
		if notifyUI:
			self._pref.notifyUI()

	def hidden(self):
		return 0

	def ui(self, master=None):
		"Return the UI element for this entire category."

		if self._ui:
			return self._ui
		import Tkinter
		self._ui = Tkinter.Frame(master)
		self._ui.columnconfigure(0, weight=0)
		self._ui.columnconfigure(1, weight=1)
		if self._order:
			order = self._order
		else:
			order = self._options.keys()
			order.sort()
		row = 0
		for name in order:
			opt = self._options[name]
			closure = opt.closure()
			if closure:
				inst = closure[0](self._ui, row, name,
					opt.get(), lambda t, o=opt:
					    o.set(t.get(), fromTkoption=True),
					**opt.UIkw())
				opt.setUI(inst)
			row = row + 1
		if self._onDisplay:
			self._ui.bind("<Map>", self._onDisplay)
		if self._onHide:
			self._ui.bind("<Unmap>", self._onHide)
		return self._ui

	def load(self, optDict, notifyUI=True):
		"Set category option values."

		for name, value in optDict.items():
			try:
				opt = self._options[name]
			except KeyError:
				self._unknownOpts[name] = value
			else:
				opt.set(value, asSaved=True, fromPref=True)
		if notifyUI:
			self._pref.notifyUI()
		self._loaded = 1

	def isLoaded(self):
		return self._loaded

	def save(self):
		"Save non-default option values into a dictionary."

		optDict = {}
		for name, opt in self._options.items():
			value = opt.savedValue(forPrefSave=True)
			if value == opt.defaultValue():
				continue
			if not pprint.isreadable(value):
				continue
			optDict[name] = value
		optDict.update(self._unknownOpts)
		return optDict

	def makeCurrentSaved(self):
		"Make current value be the saved value."

		for opt in self._options.values():
			opt.makeCurrentSaved()

	def resetValues(self):
		"Set current value from default value."

		for opt in self._options.values():
			opt.resetValue()

	def restoreValues(self):
		"Set current value from saved value."

		for opt in self._options.values():
			opt.restoreValue()


class Preferences:
	"Preferences manages categories of options."

	def __init__(self, filename=None, catFactory=Category):
		"Initialize preferences with no categories."

		self._category = {}
		self._aliases = {}
		self._inheritMemory = {}
		self._filename = filename
		self._categoryFactory = catFactory
		self._uiPanel = None
		self._loadDict = {}
		self._ignoreSave = 0
		self._readonly = False

	def setUIPanel(self, panel):
		"Set the user interface panel (for notification)."

		self._uiPanel = panel

	def setFilename(self, filename):
		"Set the file to load and save option values."

		self._filename = filename

	def filename(self):
		return self._filename

	def setReadonly(self, value):
		"Set the file as readonly so we don't try to overwrite."

		self._readonly = value

	def isReadonly(self):
		return self._readonly

	def load(self, filename):
		"""Load preferences from file.

		If a preference is not set in what was read in,
		then it is set to its default value."""

		if not filename:
			raise IOError, 'No preferences file found'
		f = open(filename, 'rU')
		contents = f.read()
		f.close()
		if not contents:
			self_loadDict = {}
		else:
			try:
				self._loadDict = eval(contents, {}, {})
			except SyntaxError:
				from chimera import replyobj
				replyobj.warning('Ignoring malformed preferences file\n')
		for name, optDict in self._loadDict.items():
			try:
				cat = self._category[name]
				cat.load(optDict, notifyUI=False)
				del self._loadDict[name]
			except KeyError:
				pass
		self.notifyUI()

	def save(self, filename=None):
		"""Save preferences to file.

		Only the differences from the default values are saved."""

		if self._ignoreSave:
			return
		if not filename:
			filename = self._filename
			if self._readonly and filename:
				return
		if not filename:
			from chimera import replyobj
			replyobj.warning('Cannot find writable directory for '
						'saving preferences file\n')
			return
		saveDict = {}
		for name, cat in self._category.items():
			catDict = cat.save()
			if catDict:
				saveDict[name] = catDict
		for name, optDict in self._loadDict.items():
			if self._category.has_key(name):
				continue
			saveDict[name] = optDict
		if not saveDict:
			if filename == self._filename:
				try:
					os.remove(filename)
				except OSError:
					pass
			else:
				from chimera import replyobj
				replyobj.warning('All options using '
							'default values\n')
			return
		prefDir = os.path.dirname(filename)
		if not os.path.isdir(prefDir):
			if os.path.exists(prefDir):
				try:
					os.remove(prefDir)
				except OSError:
					pass
			try:
				os.makedirs(prefDir)
			except (IOError, OSError, WindowsError):
				showException(
					'Cannot create preferences folder: %s'
								% prefDir)
				return
		from CGLutil.SafeSave import SafeSave
		try:
			with SafeSave(filename) as f:
				pprint.pprint(saveDict, f)
		except:
			showException('Error writing preferences file: %s'
								% filename)

	def _loadCategory(self, category, cat, inherit, convert):
		# Set any preloaded options
		#
		# "inherit" is a list of values to inherit
		# from other (probably old) categories.
		# If the category we are trying to load
		# already exists (either in its current name
		# or an alias), we don't bother inheriting
		# anything.  Otherwise, we gather the inherited
		# values into a dictionary and get the category
		# to load them.  Each element of "inherit" is
		# a 4-tuple of: (1) the option name
		# in the new category, (2) the old category name,
		# (3) the old category option name, and (4) a
		# function for transforming the old option value
		# into the new option value.  If function (4) is
		# None, no transformation is made.  If present, it
		# is given three arguments: the name of the old
		# category, the name of the option, and the old
		# saved value from the dictionary; its return
		# value replaces the value retrieved from the
		# preferences file.
		#
		# "convert" is a list of categories to convert to
		# the current category.  Each element of "convert"
		# is a 2-tuple of the old category and a conversion
		# function.  The function is called with the name
		# of the old category, the name of the option, and
		# the old value.  The return value is saved in the
		# current category with the same option name.
		#
		found = False
		for name in self._loadDict.keys():
			try:
				trueName = self._aliases[name]
			except KeyError:
				pass
			else:
				if trueName == category:
					found = True
					cat.load(self._loadDict[name])
					self._inheritMemory[name] = (self._loadDict[name], cat)
					del self._loadDict[name]
		if found:
			return

		d = dict()
		if convert:
			for oldCategory, xf in convert:
				for k, v in self._loadDict[oldCategory].items():
					if k in cat:
						continue
					d[k] = xf(oldCategory, k, v)
		for v in inherit:
			newName, oldCategory, oldName, xf = v
			try:
				oldValue = self._loadDict[oldCategory][oldName]
			except KeyError:
				try:
					oldDict, oldCat = self._inheritMemory[oldCategory]
					oldValue = oldDict[oldName]
				except KeyError:
					continue
				del oldCat._unknownOpts[oldName]
			if callable(xf):
				d[newName] = xf(oldCategory, newName, oldValue)
			else:
				d[newName] = oldValue
		if d:
			cat.load(d)
			cat.save()

	def addCategory(self, category, factory=None, autoload=True,
			aliases=[], inherit=[], convert=[], **kw):
		"Add a new category to preferences."

		if factory is None:
			factory = self._categoryFactory
		self._aliases[category] = category
		for alias in aliases:
			self._aliases[alias] = category
		cat = factory(self, **kw)
		self._category[category] = cat
		if autoload:
			self._loadCategory(category, cat, inherit, convert)
		return cat

	def register(self, category, options, inherit=[], convert=[], **kw):
		"""Register preferences.

		"options" should be either (1) a dictionary whose key is
		the name of the options and whose values are 3-tuples of
		the form (uiOptionType, defaultValue, callback) or a 4-tuples
		of the form (uiOptionType, defaultValue, callback, UIkeywords),
		or a 5-tuple of the form (uiOptionType, defaultValue, callback,
		UIkeywords, preferencesOptionKeywords), or (2) a list of those
		dictionaries, optionally interspersed with preference Option
		subclasses that will be used for the subsequent options.

		The uiOptionType should be a subclass of tkOptions.Option:
		BooleanOption, StringOption, etc. The defaultValue should be
		of the appropriate type. If callback is None, then (presumably)
		a preferences change doesn't have any effect until the
		application is restarted.  UIkeywords is a keyword dictionary
		that is passed in to the GUI option when it is created.
		preferencesOptionKeywords is a keyword dictionary that is
		passed to the preferences option."""

		cat = self.addCategory(category, autoload=False, **kw)
		optionFactory = Option
		if isinstance(options, dict):
			options = [options]
		for opt in options:
			if not isinstance(opt, dict):
				optionFactory = opt
				continue
			for k, v in opt.items():
				if len(v) == 3:
					uiOpt, defValue, callback = v
					UIkw = {}
					optKw = {}
				elif len(v) == 4:
					uiOpt, defValue, callback, UIkw = v
					optKw = {}
				elif len(v) == 5:
					uiOpt, defValue, callback, UIkw, optKw = v
				else:
					raise ValueError("wrong number of option values")
				cat.add(k, defValue, callback, [uiOpt], 
					UIkw=UIkw, optionFactory=optionFactory,
					optKw=optKw, notifyUI=False)
		self._loadCategory(category, cat, inherit, convert)
		self.notifyUI()

	def deregister(self, category):
		"""Deregister preferences.

		The given category is removed from the list of active
		preferences categories.  This means the user will no
		longer see it in the preferences panel."""

		self._category[category].destroy(notifyUI=False)
		del self._category[category]
		self.notifyUI()

	def set(self, category, name, value, **kw):
		"Set value of a named option in a given category."

		self._category[category].set(name, value, **kw)

	def get(self, category, name, forPrefSave=False):
		"Retrieve value of named option in given category."

		return self._category[category].get(name,
						forPrefSave=forPrefSave)

	def getOption(self, category, name):
		"Retrieve named option in given category."

		return self._category[category].getOption(name)

	def categories(self):
		"Return a list of category names."

		names = []
		for name, cat in self._category.items():
			if not cat.hidden():
				names.append(name)
		return names

	def options(self, category):
		"Return a list of option names in given category."

		return self._category[category].options()

	def ui(self, category, master=None):
		"Return the UI element for given category."

		try:
			self._ignoreSave = 1
			return self._category[category].ui(master)
		finally:
			self._ignoreSave = 0

	def notifyUI(self):
		"Notify interface panel that something changed."

		if self._uiPanel:
			self._uiPanel.categoriesChanged()

	def setOrder(self, category, order):
		"Set order of options in given category."

		self._category[category].setOrder(order)

	def makeCurrentSaved(self, category):
		"Make category current values be the values to save."

		self._category[category].makeCurrentSaved()

	def resetValues(self, category):
		"Set category current values from default values."

		self._category[category].resetValues()

	def restoreValues(self, category):
		"Set category current values from saved values."

		self._category[category].restoreValues()


class HiddenCategory(Category):

	def __init__(self, pref, optDict=None):
		"Constructor.  'optDict' is the option dictionary"

		Category.__init__(self, pref)
		if optDict:
			self._defaultOptions = optDict.copy()
			self._options = optDict
		else:
			self._defaultOptions = {}
		self._changed = 0

	def hidden(self):
		"HiddenCategory instances never show up in Preferences panel"

		return 1

	def ui(self, master=None):
		"HiddenCategory instances usually does not have a UI"

		return None

	def changeDefault(self, key, value):
		self._defaultOptions[key] = value

	def getDefault(self, key):
		return self._defaultOptions.get(key, None)

	def set(self, key, value, saveToFile=True):
		"Set a preferences value and save to file."

		if self._options.has_key(key) and self._options[key] == value:
			return
		self._options[key] = value
		self._changed = 1
		if saveToFile:
			self.saveToFile()

	def load(self, optDict, notifyUI=True):
		"Load default preferences values."

		for k, v in optDict.items():
			self.set(k, v, saveToFile=False)
		self._changed = 0
		self._loaded = 1

	def save(self):
		"Return the option dictionary as what needs to be save."

		optDict = {}
		for name, value in self._options.items():
			try:
				if value == self._defaultOptions[name]:
					continue
			except KeyError:
				pass
			if not pprint.isreadable(value):
				continue
			optDict[name] = value
		return optDict

	def saveToFile(self, force=False):
		"Save to file if anything has changed"
		if self._changed or force:
			self._pref.save()
			self._changed = 0

	# Methods below implement mapping type interface
	def __len__(self):
		return len(self._options)
	def __getitem__(self, key):
		return self._options[key]
	def __setitem__(self, key, value):
		self.set(key, value)
	def __delitem__(self, key):
		del self._options[key]
		self.saveToFile(force=True)
	def clear(self):
		if len(self._options) > 0:
			self._options.clear()
			self.saveToFile(force=True)
	def copy(self):
		raise ValueError, "cannot copy HiddenCategory instance"
	def __contains__(self, k):
		return self._options.__contains__(k)
	def keys(self):
		return self._options.keys()
	def update(self, d):
		for k, v in d.items():
			self.set(k, v)
		self.saveToFile()
	def values(self):
		return self._options.values()
	def get(self, *args, **kw):
		return self._options.get(*args)
	def setdefault(self, k, *args):
		try:
			return self._options[k]
		except KeyError:
			if len(args) == 1:
				self.set(k, args[0])
				return args[0]
			else:
				raise
	def popitem(self):
		v = self._options.popitem()
		self.saveToFile(force=True)
		return v
