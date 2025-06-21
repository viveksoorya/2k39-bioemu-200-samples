# -----------------------------------------------------------------------------
# Register mmCIF file reader.
#
def open_mmcif(path):
    import mmCIF
    return mmCIF.open_mmcif(path)

from chimera import fileInfo, FileInfo
fileInfo.register('CIF/mmCIF', open_mmcif, ['.cif'], ['cif', 'mmcif'],
			mime=("chemical/x-mmcif", "chemical/x-cif"),
			category=FileInfo.STRUCTURE)
