# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: FindDialog.py 40141 2014-09-25 19:59:59Z pett $

import chimera
from chimera.baseDialog import ModelessDialog
from chimera import replyobj
import Pmw, Tkinter

class BaseFindDialog(ModelessDialog):
	buttons = ("OK", "Apply", "Cancel")
	default = "OK"

	def __init__(self, mav, *args, **kw):
		self.mav = mav
		ModelessDialog.__init__(self, *args, **kw)

	def fillInUI(self, parent):
		from itertools import count
		self.row = count()
		parent.columnconfigure(0, weight=1)
		self.seqEntry = Pmw.EntryField(parent, labelpos='w',
			label_text=self.entryLabel, validate=self.validate,
			entry_width=10)
		entryRow = self.row.next()
		self.seqEntry.grid(row=entryRow, column=0, sticky='ew')
		from MAViewer import SeqMenu
		self.targetMenu = SeqMenu(parent, self.mav, includeAllOption=True,
			initialitem=SeqMenu.AllOptionText, labelpos='w', label_text='in')
		self.targetMenu.grid(row=entryRow, column=1, sticky='w')
		self.upcaseVar = Tkinter.IntVar(parent)
		self.upcaseVar.set(self.upcaseDefault)
		if self.offerUpcaseOption:
			checkbox = Tkinter.Checkbutton(parent, variable=self.upcaseVar,
				text="Convert to uppercase before matching")
			checkbox.grid(row=self.row.next(), column=0, columnspan=2, sticky='w')

	def destroy(self):
		self.mav = None
		ModelessDialog.destroy(self)

	def Apply(self):
		search = self.seqEntry.get().strip()
		if not search:
			replyobj.error("No search value specified\n")
			return
		if self.upcaseVar.get():
			search = search.upper()
		searchRegion = self.mav.regionBrowser.getRegion("search result",
				outline="dodger blue", fill="white", create=1)
		seqs = self.targetMenu.getvalue()

		matches = []
		searchType, func = self.searchInfo
		self.mav.status("Searching...", blankAfter=0)
		for seq in seqs:
			if searchType == "self":
				seqMatches = eval("self.%s(seq, search)" % func)
			else:
				seqMatches = eval("seq.%s(search)" % func)
			for start, end in seqMatches:
				matches.append([seq, seq, start, end])

		if not matches:
			replyobj.error("No matches found\n")
			return

		if len(matches) > 1:
			msg = "%d matches found" % len(matches)
		else:
			msg = "1 match found"
		self.mav.status(msg)

		searchRegion.clear()
		searchRegion.addBlocks(matches)

		self.mav.seeRegion(searchRegion)

class FindDialog(BaseFindDialog):
	"""Find sequence patterns"""

	help = "ContributedSoftware/multalignviewer/multalignviewer.html#findsub"
	title = "Find Subsequence"
	validate = 'alphabetic'
	entryLabel = "Find subsequence"
	upcaseDefault = True
	offerUpcaseOption = True
	searchInfo = ("self", "_seqMatch")

	def fillInUI(self, parent):
		BaseFindDialog.fillInUI(self, parent)
		from chimera.selection.seq import AmbiguityMenu
		self.ambMenu = AmbiguityMenu(parent)
		self.ambMenu.grid(row=self.row.next(), column=0, columnspan=2)

	def _seqMatch(self, seq, subseq):
		pattern = self.ambMenu.text2pattern(subseq)
		import re
		expr = re.compile(pattern)
		return seq.patternMatch(expr)

class PrositeDialog(BaseFindDialog):
	"""Find PROSITE patterns"""

	help = "ContributedSoftware/multalignviewer/multalignviewer.html#findpro"
	title = "Find PROSITE Pattern"
	validate = None
	entryLabel = "Find PROSITE pattern"
	upcaseDefault = False
	offerUpcaseOption = False
	searchInfo = ("seq", "prositeMatch")

class RegexDialog(BaseFindDialog):
	"""Find regular expressions"""

	help = "ContributedSoftware/multalignviewer/multalignviewer.html#findregex"
	title = "Find Regular Expression"
	validate = None
	entryLabel = "Find regular expression"
	upcaseDefault = True
	offerUpcaseOption = True
	searchInfo = ("seq", "regexMatch")


# though FindSeqNameDialog doesn't use BaseFindDialog, it seemed natural to
# put it in this module
class FindSeqNameDialog(ModelessDialog):
	help = "ContributedSoftware/multalignviewer/multalignviewer.html#namesearch"
	title = "Find Sequence Name"
	buttons = ("Find", "Close")
	default = "Find"
	provideStatus = True
	statusPosition = "left"

	def __init__(self, mav, *args, **kw):
		self.mav = mav
		self.lastMatch = None
		ModelessDialog.__init__(self, *args, **kw)

	def fillInUI(self, parent):
		from itertools import count
		self.matchTypeMenu = Pmw.OptionMenu(parent, labelpos='w',
			label_text="Find sequence whose name",
			items=["contains", "is exactly"], initialitem=0)
		self.matchTypeMenu.grid(row=0, column=0, sticky='e')

		parent.columnconfigure(1, weight=1)
		self.seqEntry = Pmw.EntryField(parent, entry_width=20)
		self.seqEntry.grid(row=0, column=1, sticky='ew')

	def destroy(self):
		self.mav = None
		ModelessDialog.destroy(self)

	def Apply(self):
		target = self.seqEntry.getvalue()
		# allow multiple Applies to find later matches...
		lastMatch = self.lastMatch
		if lastMatch == None or lastMatch+1 >= len(self.mav.seqs):
			seqs = self.mav.seqs
		else:
			seqs = self.mav.seqs[lastMatch+1:] + self.mav.seqs[:lastMatch+1]
		match = None
		numMatches = 0
		if self.matchTypeMenu.getvalue() == "contains":
			for seq in seqs:
				if target in seq.name:
					numMatches += 1
					if match is None:
						match = seq
			if match is None:
				self.mav.status("No sequence name contains '%s'" % target,
					color='red')
				self.enter()
				return
		else:
			for seq in seqs:
				if target == seq.name:
					numMatches += 1
					if match is None:
						match = seq
			if match is None:
				self.mav.status("No sequence name is '%s'" % target,
					color='red')
				self.enter()
				return
		self.mav.seeSeq(match, highlightName=True)
		self.lastMatch = self.mav.seqs.index(match)
		if numMatches == 1:
			self.status("1 match found")
		else:
			self.status("%d matches ('Find' again for next match)" % numMatches)

	Find = Apply

	def Close(self):
		self.mav.dehighlightName()
		ModelessDialog.Close(self)

