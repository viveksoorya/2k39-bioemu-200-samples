def write_collada(path):
	import ExportCollada 
	ExportCollada.write_collada(path)

description = 'Export scene in <a href="http://en.wikipedia.org/wiki/COLLADA">COLLADA</a> file format.'

from chimera import exports
exports.register('COLLADA', '*.dae', '.dae', write_collada, description)
