# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: Label.py 37895 2012-12-10 18:42:21Z pett $


import chimera

class Label:
	"""an entire label, possibly multi-line, composed of Characters"""
	shown = True

	def __init__(self, pos, model, background=None, margin=9.0, outline=0.0):
		self.pos = pos
		self.model = model
		# one list of characters per line
		self.lines = [[]]
		self.background = background
		self.margin = margin
		self.outline = outline
		self.opacity = 1.0

	def clear(self):
		for line in self.lines:
			for c in line:
				c.destroy()
		self.lines = [[]]

	def destroy(self):
		self.clear()
		self.model = None

	def __setattr__(self, attrName, val):
		if attrName == 'shown':
			if self.shown == val:
				return
			if unicode(self):
				self.model.setMajorChange()
		self.__dict__[attrName] = val

	def changeAttrs(self, size=None, color=None, style=None, typeface=None, opacity=None,
			background=False, margin=None, outline=None):
		chars = []
		[chars.extend(line) for line in self.lines]

		for c in chars:
			if color != None:
				c.rgba = color.rgba()[0:3] + (c.rgba[3],)
			if size != None:
				c.size = size
			if style != None:
				c.style = style
			if typeface != None:
				c.fontName = typeface
		if opacity != None:
			self.opacity = opacity
		if background != False:
			self.background = background
		if margin != None:
			self.margin = margin
		if outline != None:
			self.outline = outline

	def set(self, text):
		self.clear()
		self.lines = [ [Character(y) for y in x] for x in text.splitlines() ]
		if not self.lines:
			self.lines =[[]]
		
	def __unicode__(self):
		return self.text()

	def text(self):
		text = ""
		for line in self.lines:
			for c in line:
				text += unicode(c)
			text += '\n'
		return text[:-1]

	def animInterp(self, startData, where, endData):
		if startData is None:
			self.opacity = where * endData["opacity"]
			self.shown = endData["shown"] and not where == 0.0
			return
		if endData is None:
			self.opacity = (1.0 - where) * startData["opacity"]
			self.shown = startData["shown"] and not where == 1.0
			return
		self.shown = startData["shown"] or endData["shown"]
		if not self.shown:
			return
		sopacity, eopacity = startData["opacity"], endData["opacity"]
		if not startData["shown"]:
			sopacity = 0.0
		if not endData["shown"]:
			eopacity = 0.0
		self.opacity = sopacity + where * (eopacity - sopacity)
		sx, sy = startData["args"][0]
		ex, ey = endData["args"][0]
		self.pos = (sx + where * (ex-sx), sy + where * (ey-sy))
		skw, ekw = startData["kw"], endData["kw"]
		sbg, ebg = skw["background"], ekw["background"]
		if sbg is None or ebg is None:
			if where < 0.5:
				self.background = sbg
			else:
				self.background = ebg
		else:
			self.background = tuple([s + where * (e-s) for s,e in zip(sbg, ebg)])
		smargin, emargin = skw["margin"], ekw["margin"]
		self.margin = smargin + where * (emargin - smargin)
		soutline, eoutline = skw["outline"], ekw["outline"]
		self.outline = soutline + where * (eoutline - soutline)

		slines, elines = startData["lines"], endData["lines"]
		if where < 0.5:
			self._restoreLines(slines)
		else:
			self._restoreLines(elines)
		interpolable = True
		if len(slines) != len(elines):
			interpolable = False
		else:
			for sline, eline in zip(slines, elines):
				if len(sline) != len(eline):
					interpolable = False
					break
				for sc, ec in zip(sline, eline):
					if sc["args"] != ec["args"]:
						# characters don't match...
						interpolable = False
						break
				else:
					continue
				break
		if interpolable:
			for sline, line, eline in zip(slines, self.lines, elines):
				for schar, char, echar in zip(sline, line, eline):
					char._animInterp(schar, where, echar)
		# else:
		# since a Label.restore() was called by parent, no need to restore
		# characters individually

	def _restoreLines(self, lineInfo):
		self.lines = []
		# Helvetica/Times/Courier became Sans Serif/Serif/Fixed
		fontMap = {
			'Helvetica': 'Sans Serif',
			'Times': 'Serif',
			'Courier': 'Fixed'
		}
		for l in lineInfo:
			for cinfo in l:
				try:
					fn = cinfo["kw"]["fontName"]
				except KeyError:
					continue
				if fn in fontMap:
					cinfo["kw"]["fontName"] = fontMap[fn]
			self.lines.append([Character(*cinfo["args"],
						**cinfo["kw"]) for cinfo in l])

	def _restoreSession(self, info):
		self._restoreLines(info["lines"])
		if "shown" in info:
			self.shown = info["shown"]
		if "opacity" in info:
			self.opacity = info["opacity"]

	def _sessionInfo(self):
		info = {}
		info["args"] = (self.pos,)
		info["kw"] = {
			'background': self.background,
			'margin': self.margin,
			'outline': self.outline
		}
		info["shown"] = self.shown
		info["opacity"] = self.opacity
		lines = []
		for l in self.lines:
			lines.append([c._sessionInfo() for c in l])
		info["lines"] = lines
		return info

_fonts = {}

class Character:
	"""individual character in a label"""

	def __init__(self, c, fontName='Sans Serif', size=24,
					rgba=(1.,1.,1.,1.), baselineOffset = 0,
					style=chimera.OGLFont.normal):
		self._fontName = fontName
		self._size = size
		self._rgba = rgba
		self._style = style
		self._font = None
		self._baselineOffset = baselineOffset
		self._makeFont()
		self._char = c

	def _fontKey(self):
		return (self._fontName, self._size, self._style)

	def _makeFont(self):
		self._delFont()
		key = self._fontKey()
		try:
			font = _fonts[key]
		except KeyError:
			font = chimera.OGLFont(*key)
			_fonts[key] = font
		self._font = font
	
	def _delFont(self, *args):
		self._font = None

	def _animInterp(self, startData, where, endData):
		skw, ekw = startData["kw"], endData["kw"]
		prevSize = self._size
		self._size = int(skw["size"] + where * (ekw["size"] - skw["size"]) + 0.5)
		if self._size != prevSize:
			self._makeFont()
		self._baselineOffset = skw["baselineOffset"] + where * (
				ekw["baselineOffset"] - skw["baselineOffset"])
		rgba = []
		for s, e in zip(skw["rgba"], ekw["rgba"]):
			rgba.append(s + where * (e-s))
		self._rgba = tuple(rgba)

	def _restoreSession(self, info):
		self._char = info["char"]
		self._size = info["size"]
		self._rgba = info["rgba"]
		self._fontName = info["fontName"]
		self._style = info["style"]
		self._baselineOffset = info["baselineOffset"]
		self._makeFont()

	def _sessionInfo(self):
		info = {}
		info["args"] = (self._char,)
		info["kw"] = {
			"rgba": self._rgba,
			"size": self._size,
			"fontName": self._fontName,
			"style": self._style,
			"baselineOffset": self._baselineOffset
		}
		return info

	def __str__(self):
		# allow high-bit-set 8-bit characters...
		# (that would otherwise be unconvertible unicode)
		return chr(ord(self._char))
		
	def __unicode__(self):
		return unicode(self._char)
		
	def __getattr__(self, attr):
		if attr in ("rgba", "fontName", "size", "style", "font",
							"baselineOffset"):
			try:
				return self.__dict__["_" + attr]
			except KeyError:
				pass
		raise AttributeError, "Unknown attribute '%s'" % attr

	def __setattr__(self, attr, val):
		if attr in ("rgba", "baselineOffset"):
			self.__dict__["_" + attr] = val
		elif attr in ("size", "fontName", "style"):
			self.__dict__["_" + attr] = val
			self._makeFont()
		else:
			self.__dict__[attr] = val

	def destroy(self):
		self._delFont()
