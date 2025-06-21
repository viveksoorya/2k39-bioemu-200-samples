#!/bin/env python
# vim: set fileencoding=utf-8 :
# Copyright © 2010 Regents of the University of California.
# All Rights Reserved.
#
# Make X11 desktop menu, icon, and mime types with xdg-utils
#
# Usage:
#
#	chimera --nogui --silent --script "xdg-setup.py [un]install"
#

from __future__ import with_statement
import sys, os, codecs

verbose = False
system_generated = False

# remember locale codes are frequently different than country codes
localized_chimera = {
	'af': u'Chimera',	# Afrikaans
	'cs': u'Přízrak',	# Czech
	'da': u'Chiemra',	# Danish
	'de': u'Chimäre',	# German
	'el': u'Χίμαιρα',	# Greek
	'en': u'Chimera',	# English
	'es': u'Quimera',	# Spanish
	'fi': u'Kauhukuva',	# Finish
	'fr': u'Chimère',	# French
	'hr': u'Himera',		# Croatian
	#'hu': 'Mesebeli szörny',		# Hungarian
	'in': u'Angan-angan',	# Indonesian
	'it': u'Chimera',	# Italian
	'ja': u'キメラ',		# Japanese
	'ko': u'키메라',		# Korean
	'nl': u'Chimera',	# Dutch
	'no': u'Chimera',	# Norwegian
	'pl': u'Chimera',	# Polish
	'pt': u'Quimera',	# Portuguese
	'ro': u'Himeră', 	# Romainian
	'ru': u'Химера',		# Russian
	'sr': u'Химера',		# Serbian
	'sk': u'Prízrak',	# Slovak
	'sv': u'Chimera',	# Swedish
	'th': u'ความเพ้อฝัน',	# Thai
	'tr': u'Kuruntu',	# Turkish
	'uk': u'Химера',		# Ukrainian
	'zh': u'嵌合體',		# Chinese
}

"""
From Desktop Entry Specification 1.0:

The escape sequences \s, \n, \t, \r, and \\ are supported for values of type string and localestring, meaning ASCII space, newline, tab, carriage return, and backslash, respectively. 

Some keys can have multiple values. In such a case, the value of the key is specified as a plural: for example, string(s). The multiple values should be separated by a semicolon. Those keys which have several values should have a semicolon as the trailing character. Semicolons in these values need to be escaped using \;. 
"""

def str_quote(text):
	result = ""
	for ch in text:
		if ch == '\n':
			result += '\\n'
		elif ch == '\t':
			result += '\\t'
		elif ch == '\r':
			result += '\\r'
		elif ch == '\\':
			result += '\\\\'
		elif ch == ';':
			result += '\\;'
		elif ord(ch) < 32:
			continue
		else:
			result += ch
	return result

"""
From Desktop Entry Specification 1.0:

Arguments may be quoted in whole.  If an argument contains a reserved
character the argument must be quoted.  The rules for quoting of arguments
is also applicable to the executable name or path of the executable
program as provided. 

Quoting must be done by enclosing the argument between double quotes and
escaping the double quote character, backtick character ("`"), dollar
sign ("$") and backslash character ("\") by preceding it with an
additional backslash character.  Implementations must undo quoting before
expanding field codes and before passing the argument to the executable
program.  Reserved characters are space (" "), tab, newline, double quote,
single quote ("'"), backslash character ("\"), greater-than sign (">"),
less-than sign ("<"), tilde ("~"), vertical bar ("|"), ampersand ("&"),
semicolon (";"), dollar sign ("$"), asterisk ("*"), question mark ("?"),
hash mark ("#"), parenthesis ("(") and (")") and backtick character ("`"). 
"""

reserved_char = """ \t\n"'\\><~|&;$*?#()`"""
def arg_quote(arg):
	has_reserved = any(True for ch in arg if ch in reserved_char)
	if not has_reserved:
		return arg
	result = '"'
	for ch in arg:
		if ch in '"`$\\':
			result += '\\'
		result += ch
	result += '"'
	return result

"""
<?xml version="1.0"?>
<mime-info xmlns='http://www.freedesktop.org/standards/shared-mime-info'>
  <mime-type type="text/x-shiny">
    <comment>Shiny new file type</comment>
    <glob pattern="*.shiny"/>
    <glob pattern="*.shi"/>
  </mime-type>
</mime-info>
"""

class MimeInfo:
	IDENT = '    '

	class Nested:

		def __init__(self, plist, tag, args=''):
			self.plist = plist
			self.tag = tag
			self.args = args

		def __enter__(self):
			p = self.plist
			p.output.write("%s<%s%s>\n" % (p.IDENT * p.level, self.tag, self.args))
			p.level += 1

		def __exit__(self, exc_type, exc_value, traceback):
			p = self.plist
			p.level -= 1
			p.output.write("%s</%s>\n" % (p.IDENT * p.level, self.tag))


	def __init__(self, output=sys.stdout):
		self.level = 0
		self.output = output

	def __enter__(self):
		self.output.write(
"""<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns='http://www.freedesktop.org/standards/shared-mime-info'>
""")
		self.level = 1

	def __exit__(self, exc_type, exc_value, traceback):
		self.output.write("</mime-info>\n")
		self.output.close()

	def xml_comment(self, text):
		self.output.write("%s<!-- %s -->\n"
					% (self.IDENT * self.level, text))

	def comment(self, text):
		if isinstance(text, unicode):
			text = text.encode("utf-8")
		self.output.write("%s<comment>%s</comment>\n"
					% (self.IDENT * self.level, text))

	def glob(self, pattern):
		if isinstance(pattern, unicode):
			pattern = pattern.encode("utf-8")
		self.output.write('%s<glob pattern="*%s"/>\n'
					% (self.IDENT * self.level, pattern))

	def type(self, mimetype):
		# <mime-type type="text/x-shiny">
		return self.Nested(self, "mime-type", args=' type="%s"' % mimetype)

def desktop_comment(f, text):
	f.write("# %s\n" % text)

def desktop_group(f, name):
	# assert '[' not in name and ']' not in name
	f.write("[%s]\n" % name)

def desktop_boolean(f, tag, value):
	f.write("%s=%s\n" % (tag, "true" if value else "false"))

def desktop_numeric(f, tag, value, format="%f"):
	f.write(("%s=" + format + "\n") % (tag, value))

def desktop_string(f, tag, value):
	f.write("%s=%s\n" % (tag, str_quote(value)))

def desktop_stringlist(f, tag, values):
	f.write("%s=%s;\n" % (tag, ';'.join(str_quote(v) for v in values)))

def make_desktop(name, version, mime_types):
	if verbose:
		print "generating", name
	with codecs.open(name, mode='wt', encoding='utf-8') as f:
		if version.endswith('s'):
			version = version[0:-1] + " snapshot"
		elif version.endswith('rc'):
			version = version[0:-2] + " release candidate"
		chimera_dir = os.getenv('CHIMERA')
		desktop_group(f, "Desktop Entry")
		year = chimera.version.version.split()[5].split('-')[0]
		desktop_comment(f, u"Copyright \u00A9 %s Regents of the University of California.  All Rights Reserved." % year)
		desktop_string(f, "Type", "Application")
		desktop_numeric(f, "Version", 1.0, "%.1f")
		desktop_string(f, "Encoding", "UTF-8")
		desktop_string(f, "Name", "UCSF Chimera %s" % version)
		locales = list(localized_chimera.keys())
		locales.sort()
		for lo in locales:
			desktop_string(f, "Name[%s]" % lo,
				"UCSF %s %s" % (localized_chimera[lo], version))
		desktop_string(f, "GenericName", "Molecular Visualization")
		desktop_string(f, "Comment",
			"A extensible molecular modeling system, http://www.cgl.ucsf.edu/chimera/")
		desktop_string(f, "Icon", "UCSF-Chimera")
		desktop_stringlist(f, "Categories", [
			"Education", "Science", "Biology", "Chemistry",
			"Graphics", "3DGraphics", "DataVisualization"])
		desktop_stringlist(f, "MimeType", mime_types)
		if '=' in chimera_dir:
			print >> sys.stderr, "warning: '=' found in path to chimera"
		else:
			desktop_string(f, "Exec",
				"%s -- %%F" % arg_quote(chimera_dir + "/bin/chimera"))
	s = os.stat(name)
	os.chmod(name, s.st_mode | 0o555)	# make executable

def make_mimeinfo(name, file_info):
	if verbose:
		print "generating", name
	mi = MimeInfo(codecs.open(name, mode='wt', encoding='utf-8'))
	with mi:
		year = chimera.version.version.split()[5].split('-')[0]
		mi.xml_comment(u"Copyright \u00A9 %s Regents of the University of California.  All Rights Reserved." % year)

		for t in file_info.types():
			extensions = file_info.extensions(t)
			mimeTypes = file_info.mimeType(t)
			if not extensions or not mimeTypes:
				continue
			for m in mimeTypes:
				with mi.type(m):
					mi.comment(file_info.category(t))
					for e in extensions:
						mi.glob(e)

def add_xdg_utils_to_path():
	if verbose:
		print "adding xdg scripts to end of path"
	path = os.getenv("PATH")
	path += ":%s/share/xdg-utils" % os.getenv("CHIMERA")
	os.environ["PATH"] = path

import subprocess
def install_icons(mime_types):
	if verbose:
		print "installing icons"
	image_dir = os.getenv("CHIMERA") + "/share/chimera/images"
	cmd = [
		'xdg-icon-resource', 'install',
		'--context', 'apps',
		'--size', '48',
		'%s/chimera48.png' % image_dir,
		'UCSF-Chimera'
	]
	subprocess.call(cmd)
	if "chimera/x-pdb" in mime_types:
		cmd = [
			'xdg-icon-resource', 'install',
			'--context', 'mimetypes',
			'--size', '48',
			'%s/pdb48.png' % image_dir,
			'chemical-x-pdb'
		]
		subprocess.call(cmd)
	if "chimera/x-mol2" in mime_types:
		cmd = [
			'xdg-icon-resource', 'install',
			'--context', 'mimetypes',
			'--size', '48',
			'%s/pdb48.png' % image_dir,
			'chemical-x-mol2'
		]
		subprocess.call(cmd)

def install_desktop_menu(desktop):
	if verbose:
		print "installing desktop menu"
	cmd = [ 'xdg-desktop-menu', 'install', desktop ]
	subprocess.call(cmd)

def install_desktop_icon(desktop):
	if verbose:
		print "installing desktop icon"
	cmd = [ 'xdg-desktop-icon', 'install', desktop ]
	subprocess.call(cmd)

def uninstall_desktop_menu(desktop):
	if verbose:
		print "uninstalling desktop menu"
	cmd = [ 'xdg-desktop-menu', 'uninstall', desktop ]
	subprocess.call(cmd)

def uninstall_desktop_icon(desktop):
	if verbose:
		print "uninstalling desktop icon"
	cmd = [ 'xdg-desktop-icon', 'uninstall', desktop ]
	subprocess.call(cmd)

def install_mimeinfo(mimetypes):
	if verbose:
		print "installing MIME info"
	cmd = [ 'xdg-mime', 'install', mimetypes ]
	subprocess.call(cmd)

def uninstall_mimeinfo(mimetypes):
	if verbose:
		print "uninstalling MIME info"
	cmd = [ 'xdg-mime', 'uninstall', mimetypes ]
	subprocess.call(cmd)

if __name__ == '__main__':
	USAGE = "%s [-v] generate|install|reinstall|uninstall"
	# temporary hack until we have a way to run chimera and non-chimera binaries
	del os.environ["LD_LIBRARY_PATH"]

	name = "UCSF-Chimera"
	import platform
	if sys.maxsize > 2 ** 32:
		name += '64'
	import chimera
	version = chimera.version.releaseVersion()
	import getopt
	try:
		opts, args = getopt.getopt(sys.argv[1:], "v", ["build"])
	except getopt.error, message:
		print >> sys.stderr, "%s: %s" % (sys.argv[0], message)
		print >> sys.stderr, USAGE % sys.argv[0]
		raise SystemExit, 2
	for opt, arg in opts:
		if opt == "-v":
			verbose = True
		elif opt == "--build":
			version = 'build'
	name += '-' + version

	if len(args) != 1:
		print >> sys.stderr, USAGE % sys.argv[0]
		raise SystemExit, 2
	command = args[0]

	if os.getuid() == 0:
		# make sure other users can read .desktop files
		if os.umask(0o22) != 0o22 and verbose:
			print "temporarily changed umask to 0o22"

	dir = os.getenv("CHIMERA")
	desktop = "%s/%s.desktop" % (dir, name)
	mimeinfo = "%s/%s.xml" % (dir, name)
	system_generated = os.path.exists(desktop) and os.path.exists(mimeinfo)

	if not system_generated and os.getuid() != 0:
		dir = os.getenv("HOME") + "/.chimera"
		try:
			os.mkdir(dir)
		except OSError, e:
			if e.errno != 17:
				print >> sys.stderr, "Error: Unable to create", dir
				raise SystemExit, 2
		desktop = "%s/%s.desktop" % (dir, name)
		mimeinfo = "%s/%s.xml" % (dir, name)

	if not system_generated or command == "reinstall":
		mime_types = []
		for t in chimera.fileInfo.types():
			mt = chimera.fileInfo.mimeType(t)
			if isinstance(mt, (list, tuple)):
				mime_types.extend(mt)
			elif mt:
				mime_types.append(mt)
		mime_types.sort()

	if command == 'generate':
		if system_generated:
			if verbose:
				print "already generated"
		else:
			make_desktop(desktop, version, mime_types)
			make_mimeinfo(mimeinfo, chimera.fileInfo)
	elif command in ('install', 'reinstall'):
		if not system_generated and command == 'install':
			make_desktop(desktop, version, mime_types)
			make_mimeinfo(mimeinfo, chimera.fileInfo)
		add_xdg_utils_to_path()
		if not system_generated or command == "reinstall":
			install_mimeinfo(mimeinfo)
			install_icons(mime_types)
			install_desktop_menu(desktop)
		if os.getuid() != 0:
			install_desktop_icon(desktop)
	elif command == 'uninstall':
		add_xdg_utils_to_path()
		if os.getuid() != 0:
			uninstall_desktop_icon(desktop)
		if os.getuid() == 0 or not system_generated:
			uninstall_desktop_menu(desktop)
			uninstall_mimeinfo(mimeinfo)
			os.remove(desktop)
			os.remove(mimeinfo)
	else:
		print >> sys.stderr, "Error: unknown command:", command
		raise SystemExit, 2
	raise SystemExit, 0
