import os
chimeraRoot = os.environ["CHIMERA"]
chimeraBin = os.path.join(chimeraRoot, "bin")
for dirEntry in os.listdir(chimeraBin):
	if not dirEntry.startswith("amber"):
		continue
	try:
		amberVersion = int(dirEntry[5:])
	except ValueError:
		continue
	break
else:
	raise AssertionError("No amberXX subdirectory for %s" % chimeraBin)

# antechamber uses system() a lot, and cygwin's implementation doesn't
# cotton to backslashes as path separators
amberHome = os.path.join(chimeraBin, dirEntry).replace('\\', '/')
amberBin = amberHome + "/bin"

import sys
if sys.platform == "win32":
	# shut up Cygwin DOS-path complaints
	# and prevent "qm_theory='AM1'," from being changed to "qm_theory=AM1,"
	os.environ['CYGWIN'] = u"nodosfilewarning noglob"
	# if user installed Cygwin, use their libs to avoid conflict
	try:
		import _winreg
		h = _winreg.OpenKeyEx(_winreg.HKEY_LOCAL_MACHINE,
			"SOFTWARE\\Cygwin\\setup")
		import os
		os.environ['PATH'] = os.environ['PATH'] + ';' + \
			_winreg.QueryValueEx(h, "rootdir")[0] + '\\bin\\'
	except WindowsError:
		# Cygwin not installed
		pass
