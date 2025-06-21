# -----------------------------------------------------------------------------
# Read a VTK ascii structured points file.
#
# # vtk DataFile Version 2.0
# Volume example
# ASCII
# DATASET STRUCTURED_POINTS
# DIMENSIONS 3 4 6
# SPACING 1 1 1
# ORIGIN 0 0 0
# POINT_DATA 72
# SCALARS volume_scalars char 1
# LOOKUP_TABLE default
# 0 0 0 0 0 0 0 0 0 0 0 0
# 0 5 10 15 20 25 25 20 15 10 5 0
# 0 10 20 30 40 50 50 40 30 20 10 0
# 0 10 20 30 40 50 50 40 30 20 10 0
# 0 5 10 15 20 25 25 20 15 10 5 0
# 0 0 0 0 0 0 0 0 0 0 0 0
#

# -----------------------------------------------------------------------------
#
class VTK_Map:

  def __init__(self, path):

    self.path = path
    #
    # Open file in binary mode 'rb'.  Opening in mode 'r' in Python 2.4.2
    # on Windows with '\n' line endings gives incorrect f.tell() values,
    #
    f = open(path, 'rb')

    ver = f.readline()
    if not ver.startswith('# vtk DataFile Version'):
      raise SyntaxError('First line does not start with "# vtk DataFile Version"')

    header = f.readline()               # description of data set

    ab = f.readline().strip()           # ASCII or BINARY
    if ab != 'ASCII':
      raise SyntaxError('VTK file is not ascii format, got "%s"' % ab)

    g = f.readline().strip()
    if g != 'DATASET STRUCTURED_POINTS':
      raise SyntaxError('VTK file is not structured points, got "%s"' % g)

    self.grid_size = parse_3_values(f.readline().strip(), 'DIMENSIONS', int)

    sline = f.readline().strip()
    try:
      self.spacing = parse_3_values(sline, 'SPACING', float)
    except:
      self.spacing = parse_3_values(sline, 'ASPECT_RATIO', float)

    self.origin = parse_3_values(f.readline().strip(), 'ORIGIN', float)

    pd = f.readline().strip()
    if not pd.startswith('POINT_DATA'):
      raise SyntaxError('VTK file is missing POINT_DATA line, got "%s"' % pd)

    sc = f.readline().strip()
    if not sc.startswith('SCALARS'):
      raise SyntaxError('VTK file is missing SCALARS line, got "%s"' % sc)
    fields = sc.split()
    if len(fields) < 3:
      raise SyntaxError('VTK file is SCALARS line must have at least 3 fields, got "%s"' % sc)
    from numpy import float32, float64, int8, uint8, int16, uint16, int32, uint32, int64, uint64
    vtypes = {'float':float32, 'double':float64,
              'char':int8, 'unsigned_char':uint8,
              'short':int16, 'unsigned_short':uint16,
              'int':int32, 'unsigned_int':uint32,
              'long':int64, 'unsigned_long':uint64,}
    if not fields[2] in vtypes:
      raise SyntaxError('VTK file unrecognzed scalar type "%s", must be one of %s'
                        % (fields[2], ', '.join(vtypes.keys())))
    self.value_type = vtypes[fields[2]]

    lt = f.readline().strip()
    if not lt.startswith('LOOKUP_TABLE default'):
      raise SyntaxError('VTK file requires LOOKUP_TABLE default, got "%s"' % lt)
    
    self.data_offset = f.tell()
    f.seek(0,2)                         # End of file
    self.file_size = f.tell()
    
    f.close()

  # ---------------------------------------------------------------------------
  #
  def matrix(self, progress):

    f = open(self.path, 'rb')
    f.seek(self.data_offset)

    if progress:
      progress.text_file_size(self.file_size)
      progress.close_on_cancel(f)
    
    asize, bsize, csize = self.grid_size
    from numpy import zeros, float32, array, reshape
    data = zeros((csize, bsize, asize), float32)
    from VolumeData.readarray import read_float_lines
    for c in range(csize):
      if progress:
        progress.plane(c)
      read_float_lines(f, data[c,:,:], line_format = None)

    f.close()

    return data

# -----------------------------------------------------------------------------
#
def parse_3_values(line, keyword, vtype):

  if not line.startswith(keyword):
    raise SyntaxError('VTK file missing %s line, got "%s"' % (keyword, line))

  try:
    v = tuple(vtype(d) for d in line.split()[1:])
  except:
    raise SyntaxError('VTK file error parsing %s line "%s"' % (keyword, line))
  if len(v) != 3:
    raise SyntaxError('VTK file requires 3 %s values, got "%d"' % (keyword, len(v)))
  return v
