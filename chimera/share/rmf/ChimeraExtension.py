# -----------------------------------------------------------------------------
# Register rmf file reader.
#
def open_rmf_file(path):
	import rmf
	return rmf.open_rmf(path)

from chimera import fileInfo, FileInfo
fileInfo.register('Rich Molecular Format', open_rmf_file,
			['.rmf', '.rmf3', '.rmfz'], ['rmf'],
			category=FileInfo.STRUCTURE)
fileInfo.registerAlias('Rich Molecular Format', 'Rich Molecule Format')

def _rmf_alias(rmf_name="", depth=4, skip_prefix=1):
	# First find the RMF instance matching the given name
	targets = set()
	import chimera
	for m in chimera.openModels.list():
		try:
			r = m.rmf()
		except AttributeError:
			continue
		if r is None:
			continue
		if not rmf_name or r.name == rmf_name:
			targets.add(r)
	if not targets:
		raise chimera.UserError("No matching RMF model found.")
	def add_alias(c, names):
		if len(names) >= depth:
			return 0
		from chimera import selection
		s = selection.ItemizedSelection()
		c.addChimeraObjects(s)
		names.append(c.name)
		count = 0
		if not s.empty():
			sel_name = make_sel_name(names)
			try:
				sel = selection.savedSels[sel_name]
			except KeyError:
				# Not defined, no action needed
				pass
			else:
				s.merge(selection.EXTEND, sel)
			print "adding \"%s\": %d atoms/bonds" % (sel_name, len(s))
			selection.saveSel(sel_name, s)
			count += 1
		for sc in c.components:
			count += add_alias(sc, names)
		names.pop(-1)
		return count
	def make_sel_name(names):
		keep = [ sanitize(n) for n in names[skip_prefix:depth] ]
		return '/'.join(keep)
	def sanitize(n):
		return ''.join([ c for c in n if c.isalnum() or c == '_' ])
	count = 0
	for r in targets:
		names = []
		count += add_alias(r.rootComponent, names)
	from chimera import replyobj
	replyobj.status("Added %d aliases for %d RMF files" %
						(count, len(targets)))

def rmf_alias(cmdName, args, ra=_rmf_alias):
	from Midas.midas_text import doExtensionFunc
	doExtensionFunc(ra, args)

from Midas.midas_text import addCommand
addCommand("rmfalias", rmf_alias)
