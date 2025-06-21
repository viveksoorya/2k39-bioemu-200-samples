"""Read Maestro ASCII format file"""

IndexAttribute = "i_chimera_index"

class MaestroString:

	import re
	REIdent = re.compile(r"(?P<value>[A-Za-z_][^\s{}[\]]+)")
	REString = re.compile(r'\"(?P<value>([^"\\]|\\.)*)\"')
	REString2 = re.compile(r"(?P<value>[^\s{}[\]]+)")
	REValue = re.compile(r"(?P<value>\S+)")
	REComment = re.compile(r"#.*")
	REFloat = re.compile(r"^(?P<value>\d+(?=[.eE])(\.\d*)?([eE]\d+))$")
	REInteger = re.compile(r"^(?P<value>\d+)$")
	del re

	TokenEOF = 0
	TokenEndList = 1
	TokenIdent = 2
	TokenString = 3
	TokenValue = 3

	MatchTokenList = [
		(	TokenIdent,	REIdent		),
		(	TokenString,	REString	),
		(	TokenString,	REString2	),
	]
	MatchValueList = [
		(	TokenValue,	REString	),
		(	TokenValue,	REValue		),
	]

	def __init__(self, data, parseContents=True):
		"""Read Maestro format data from string"""

		self.data = data
		self.parseContents = parseContents

	def __iter__(self):
		self.length = len(self.data)
		self.index = 0
		self.lineno = 1
		self.eof = False
		self._nextToken()
		# Always parse first block since it has the
		# version information
		block = self._readBlock()
		if block:
			yield block
		if not self.parseContents:
			# Reset index to start of token so
			# _readUnparsedBlock starts at the right place
			self.index = self._tokenIndex
		while not self.eof:
			if self.parseContents:
				block = self._readBlock()
			else:
				block = self._readUnparsedBlock()
			if block:
				yield block

	def estimateBlockCount(self):
		"""Return approximate number of "Molecule" blocks."""
		count = 0
		start = 0
		while True:
			start = self.data.find("f_m_ct", start)
			if start == -1:
				return count
			count += 1
			start += 6

	def _readBlock(self, depth=0):
		"""Read a single block and assign all attribute values."""
		#print "_readBlock", depth

		tokenType, tokenValue = self.token
		if tokenType is self.TokenEOF:
			return None

		# Read block name and size if present
		if tokenType is self.TokenIdent:
			name = tokenValue
			tokenType, tokenValue = self._nextToken()
			if tokenType != '[':
				size = 1
				multivalued = False
			else:
				tokenType, tokenValue = self._nextToken()
				size = self._getInteger(tokenValue)
				multivalued = True
				tokenType, tokenValue = self._nextToken()
				if tokenType != ']':
					self._syntaxError("unclosed block size")
				tokenType, tokenValue = self._nextToken()
		else:
			name = None
			size = 1
			multivalued = False
		block = Block(name, size)

		# Open block
		if tokenType != '{':
			if name is not None:
				self._syntaxError("missing block open brace")
			else:
				return None

		# Read block attribute names
		attrNames = list()
		while not self.eof:
			tokenType, tokenValue = self._nextToken()
			if tokenType == self.TokenEndList:
				break
			attrNames.append(tokenValue)
			#print "attribute name:", tokenValue
		if multivalued:
			# For multivalued blocks, the first attribute
			# column is always the index
			attrNames.insert(0, IndexAttribute)
			#print "insert attribute name:", IndexAttribute
		#print "number of rows:", size

		# Read block attribute values
		for row in range(size):
			for i in range(len(attrNames)):
				tokenType, tokenValue = self._nextValue()
				if tokenType in (self.TokenIdent,
							self.TokenString):
					#print "set", row, attrNames[i], tokenValue
					block.setAttribute(self, row,
								attrNames[i],
								tokenValue)
				else:
					self._syntaxError("data value expected")
		tokenType, tokenValue = self._nextToken()
		if tokenType == self.TokenEndList:
			self._nextToken()

		# Read subblocks
		while not self.eof:
			subblock = self._readBlock(depth + 1)
			if subblock is None:
				break
			block.addSubBlock(subblock)

		# Close block
		tokenType, tokenValue = self.token
		if tokenType != '}':
			self._syntaxError("missing block close brace")
		self._nextToken()
		return block

	def _nextToken(self):
		self._skipWhitespace()
		self._tokenIndex = self.index
		if self.index >= self.length:
			self.eof = True
			self.token = (self.TokenEOF, "<EOF>")
			return self.token
		if self.data[self.index] in "{}[]":
			c = self.data[self.index]
			self.index += 1
			self.token = (c, c)
			return self.token
		if self.data[self.index:self.index+3] == ":::":
			self.index += 3
			self.token = (self.TokenEndList, ":::")
			return self.token
		m = self.REComment.match(self.data, self.index)
		if m is not None:
			self.index = m.end()
			return self._nextToken()
		for tokenType, pattern in self.MatchTokenList:
			m = pattern.match(self.data, self.index)
			if m is not None:
				self.index = m.end()
				self.token = (tokenType, m.group("value"))
				return self.token
		self._syntaxError("unrecognized token")

	def _nextValue(self):
		self._skipWhitespace()
		if self.index >= self.length:
			self.eof = True
			self.token = (self.TokenEOF, "<EOF>")
			return self.token
		if self.data[self.index:self.index+3] == ":::":
			self.index += 3
			self.token = (self.TokenEndList, ":::")
			return self.token
		for tokenType, pattern in self.MatchValueList:
			m = pattern.match(self.data, self.index)
			if m is not None:
				self.index = m.end()
				self.token = (tokenType, m.group("value"))
				return self.token
		self._syntaxError("unrecognized value")

	def _skipWhitespace(self):
		while self.index < self.length:
			c = self.data[self.index]
			if c == '\n':
				self.lineno += 1
			if not c.isspace():
				break
			self.index += 1

	def _readUnparsedBlock(self):
		"""Read a single block as a chunk of text."""

		#print "_readUnparsedBlock"
		self._skipWhitespace()
		if self.index >= self.length:
			self.eof = True
			return None
		start = n = self.index
		depth = 0
		while n < self.length:
			if self.data[n] == '{':
				n += 1
				depth += 1
			elif self.data[n] == '}':
				n += 1
				depth -= 1
				if depth == 0:
					break
			elif self.data[n] in "'\"":
				quote = self.data[n]
				n += 1
				while n < self.length:
					if self.data[n] == '\\':
						n += 2
					elif self.data[n] == quote:
						n += 1
						break
					else:
						n += 1
			elif self.data[n] == '\n':
				self.lineno += 1
				n += 1
			else:
				n += 1
		else:
			self._syntaxError("unclosed block")
		self.index = n
		self.eof = self.index >= self.length
		return UnparsedBlock(self.data[start:n])

	def _getValue(self, name, value):
		try:
			return getValue(name, value)
		except ValueError:
			raise ValueError(
				"value (%s) does not match attribute (%s) type"
				% (value, name))

	def _getInteger(self, value):
		try:
			return int(value)
		except ValueError:
			raise ValueError(
				"expected integer and got \"%s\"" % value)

	def _syntaxError(self, msg):
		raise SyntaxError("line %d: %s (current token: %s %s)" %
					(self.lineno, msg, self.token[0],
						self.token[1]))

class Block:

	def __init__(self, name, size):
		self.name = name
		self.size = size
		self.attributeRows = [ dict() for i in range(size) ]
		self.subBlocks = list()
		self.attributeNames = list()

	def addSubBlock(self, block):
		self.subBlocks.append(block)

	def getSubBlock(self, name):
		for sb in self.subBlocks:
			if sb.name == name:
				return sb
		return None

	def setAttribute(self, mb, row, name, value):
		if row == 0:
			self.attributeNames.append(name)
		attrs = self.attributeRows[row]
		# Use "mb._getValue" instead of "getValue" to 
		# generate better error message
		attrs[name] = mb._getValue(name, value)

	def getAttribute(self, name, row=0):
		return self.attributeRows[row][name]

	def getAttributeMap(self, row=0):
		return self.attributeRows[row]

	def write(self, f, indent=0):
		prefix = " " * indent
		contentPrefix = " " * (indent + 2)
		if self.name:
			name = self.name
			sep = " "
		else:
			name = ""
			sep = ""
		if self.size > 1:
			size = "[%d]" % self.size
		else:
			size = ""
		print >> f, "%s%s%s%s{" % (prefix, name, size, sep)

		for name in self.attributeNames:
			if name == IndexAttribute:
				continue
			print >> f, "%s%s" % (contentPrefix, name)
		print >> f, "%s:::" % contentPrefix
		for row in self.attributeRows:
			f.write(contentPrefix)
			for name in self.attributeNames:
				value = printableValue(name, row[name])
				print >> f, value,
			print >> f

		for block in self.subBlocks:
			block.write(f, indent + 2)

		print >> f, "%s}" % prefix
		print >> f


class UnparsedBlock:

	def __init__(self, text):
		self.text = text

	def write(self, f, indent=0):
		print >> f, self.text
		print >> f


class MaestroFile(MaestroString):

	def __init__(self, f, *args, **kw):
		if isinstance(f, basestring):
			f = file(f)
			closeWhenDone = True
		else:
			closeWhenDone = False
		try:
			MaestroString.__init__(self, f.read(), *args, **kw)
		finally:
			if closeWhenDone:
				f.close()


def getValue(name, value):
	"""Convert text string into value based on attribute name"""
	if value == "<>":
		return None
	if name[0] == 'i':
		return int(value)
	elif name[0] == 'r':
		return float(value)
	elif name[0] == 's':
		return value
	elif name[0] == 'b':
		return int(value) != 0
	else:
		raise ValueError("unknown attribute type: %s" % name)

def printableValue(name, value):
	"""Convert value into text string based on attribute name"""
	if value is None:
		return "<>"
	if name[0] == 'i':
		return "%d" % value
	elif name[0] == 'r':
		return "%g" % value
	elif name[0] == 's':
		v = value.replace('\\', '\\\\').replace('"', '\\"')
		if v != value:
			return '"%s"' % v
		for c in v:
			if c.isspace():
				needQuotes = True
				break
		else:
			needQuotes = len(v) == 0
		if not needQuotes:
			return v
		else:
			return '"%s"' % v
	elif name[0] == 'b':
		return "%d" % value
	else:
		raise ValueError("unknown attribute type: %s" % name)

if __name__ == "__main__":
	print MaestroFile("kegg_dock5.mae")
