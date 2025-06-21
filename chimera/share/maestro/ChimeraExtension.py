# -----------------------------------------------------------------------------
# Register mmCIF file reader.
#
def open_maestro(path):
    import maestro
    return maestro.open_maestro(path)

from chimera import fileInfo, FileInfo
fileInfo.register('Maestro', open_maestro, ['.mae'], ['mae', 'maestro'],
			category=FileInfo.STRUCTURE)
