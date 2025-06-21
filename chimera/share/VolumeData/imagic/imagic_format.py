#
# ******************************************************************************
# *                                                                            *
# *     READ A (SINGLE) 3D VOLUME STORED IN AN IMAGIC FILE                     *
# *                                                                            *
# *     Note: IMAGIC can hold multiple volumes in one single file              *
# *                                                                            *
# ******************************************************************************
# *                                                                            *
# *     An IMAGIC file actually consists of TWO files:                         *
# *                                                                            *
# *        1> <file name>.hed  -  file with header information for             *
# *                               each image/each volume section               *
# *        2> <file name>.img  -  file with all image/volume densities         *
# *                                                                            *
# ******************************************************************************
# *                                                                            *
# *     Image Science Software GmbH                                            *
# *     Gillweg 3                                                              *
# *     14193 Berlin                                                           *
# *     Germany                                                                *
# *     imagic@ImageScience.de                                                 *
# *                                                                            *
# ******************************************************************************
#

class IMAGIC_Data:

  def __init__(self, path, file_type):

    import os

    from numpy import uint8, int8, int16, uint16, int32, uint32, float32, dtype

#
# ******************************************************************************
# *                                                                            *
# *     IMAGIC HEADER                                                          *
# *     (see: imagic_format.html or www.ImageScience.de/formats)               *
# *                                                                            *
# *     Header values needed (description see below):                          *
# *                                                                            *
# *     IDAT1(13) - IXLP                                                       *
# *     IDAT1(14) - IYLP                                                       *
# *     IDAT1(61) - IZLP                                                       *
# *     IDAT1(62) - I4LP                                                       *
# *     IDAT1(69) - REALTYPE                                                   *
# *     IDAT1(15) - TYPE                                                       *
# *     DAT1(123) - RESOL                                                      *
# *                                                                            *
# ******************************************************************************
#
    split = os.path.splitext(path)
    hed_path = split[0] + '.hed'
    img_path = split[0] + '.img'

    self.img_path = img_path

    #
    # Check if both, the IMAGIC header and density file exists
    #

    str1 = ''
    str2 = ''
    
    if not os.path.exists(hed_path):

      str1 = 'header'
      str2 = hed_path

    elif not os.path.exists(img_path): 

      str1 = 'density'
      str2 = img_path

    if not (str1 == '' and str2 == ''):
      s = ''.join([
          '\n',
          'No IMAGIC ', str1, ' file found (', str2, ')',
          '\n',
          '\n',
          'Probably, the input file is not an IMAGIC volume file',
          '\n',
          'Note: An IMAGIC volume is stored in two files:',
          '\n',
          '      <name>.hed and <name>.img'])
      raise IOError, ( s )

    #
    # Open header file (.hed)
    #
    hed_file = open(hed_path, 'rb')

    #
    # Floating point type / machine stamp
    #
    #   16777216: VAX/VMS
    #   33686018: Linux, Unix, Mac OSX, MS Windows, OSF, ULTRIX
    #   67372036: SiliconGraphics, SUN, HP, IBM 
    #
    self.swap_bytes = 0
    hed_file.seek(68*4,0)
    realtype = self.read_values(hed_file, int32, 1)

    if not (realtype == 16777216 or realtype == 33686018 or realtype == 67372036):
      raise SyntaxError, ('IMAGIC header value REALTYPE (%d) is invalid'
                          % realtype)
    #
    # Check endianess
    #
    import sys

    if sys.byteorder == 'little' and realtype == 67372036:
      self.swap_bytes = 1

    if sys.byteorder == 'big' and realtype != 67372036:
      self.swap_bytes = 1

    #
    # Volume dimensions
    #
    #   ixlp : number of of lines per image/section line
    #   iylp : number pixels in each image/section line
    #   izlp : number of sections of the 3D volume
    #
    hed_file.seek(12*4,0)
    ixlp = self.read_values(hed_file, int32, 1)
    hed_file.seek(13*4,0)
    iylp = self.read_values(hed_file, int32, 1)
    hed_file.seek(60*4,0)
    izlp = self.read_values(hed_file, int32, 1)

    nx = iylp
    ny = ixlp
    nz = izlp
    self.data_size = (nx, ny, nz)

    #
    # Number of volumes
    #
    #   i4lp : Number of "objects" in file:
    #          1D (ixlp=1): number of 1D spectra
    #          2D (iylp=1): number of 2D images
    #          3D (izlp>1): number of 3D volumes
    #
    # If the IMAGIC file contains multiple volumes the
    # user has to specify the wanted volume (location)
    #
    hed_file.seek(61*4,0)
    i4lp = self.read_values(hed_file, int32, 1)

    self.location = 1

    from Tkinter import *
    if i4lp > 1:
        frame = Tk()
        frame.wm_title("Select IMAGIC volume (3D location)")
        frame.wm_minsize(width=500, height=150)
        frame.wm_maxsize(width=500, height=150)
        Label(frame, pady=20, text='%d volumes in file - Please select the volume wanted' % i4lp).pack()
        self.slider = Scale(frame, from_=1, to=i4lp, length=400, orient=HORIZONTAL, command=self.get_slider_value)
        self.slider.pack()
        Button(frame, text="OK", command=frame.destroy).pack()
        frame.wait_window()

    #
    # TYPE
    #
    #   REAL : Each image pixel is represented by a 32-bit real/float number
    #   LONG : Each image pixel is represented by a 32-bit (signed) integer number
    #   INTG : Each image pixel is represented by a 16-bit (signed) integer number
    #   PACK : Each image pixel is represented by one (unsigned) byte number
    #   COMP : Each complex image pixel is represented by 2 REAL values
    #
    hed_file.seek(14*4,0)
    itype = hed_file.read(4)

    self.element_type = 0
    if itype == 'PACK':
       self.element_type = dtype(int8)
       self.n_bytes      = 1
    elif itype == 'INTG':
       self.element_type = dtype(int16)
       self.n_bytes      = 2
    elif itype == 'LONG':
       self.element_type = dtype(int32)
       self.n_bytes      = 4
    elif itype == 'REAL':
       self.element_type = dtype(float32)
       self.n_bytes      = 4
    else:
      raise SyntaxError, ('IMAGIC type (%s) ' % itype +
                          'is not 8-bit (PACK), 16-bit (INTG), 32-bit integer(LONG) or 32-bit float (REAL)')

    #
    # Pixel size
    #
    hed_file.seek(122*4,0)
    resol = self.read_values(hed_file, float32, 1)

    #
    # Data origin
    #
    # Starting and origin values are not used (do not make sense) in IMAGIC
    #
    # Unfortunalty, the starting and origin values are used inconsistently by different programs
    # Situs and other programs use the following settings:
    #   nxstart = -nx/2
    #   nystart = -ny/2
    #   nzstart = -nz/2
    # Many programs (even MRC programs) simply set these value to zero (see spider_format.py):
    #   nxstart = 0
    #   nystart = 0
    #   nzstart = 0
    # Here the values are set to zero following the MRC headers of the 3DEM maps stored in the EMDB data base (emdatabank.org)
    #
    nxstart = 0
    nystart = 0
    nzstart = 0
    self.data_origin = (nxstart*resol, nystart*resol, nzstart*resol)

    #
    # Unit cell size
    #
    mx = nx
    my = ny
    mz = nz
    self.unit_cell_size = mx, my, mz

    #
    # Data step
    #
    if resol > 1.0E-20:
      self.data_step = (resol, resol, resol)
    else:
      self.data_step = (1.0, 1.0, 1.0)

    #
    # Cell angles
    #
    alpha = beta = gamma = 90
    self.cell_angles = (alpha, beta, gamma)

    #
    # Rotation
    #
    r = ((1,0,0),(0,1,0),(0,0,1))
    self.rotation = r

    #
    # Close header file (.hed)
    #
    hed_file.close()

    #
    # Offset in IMAGIC densities file (.img)
    #
    self.data_offset = (self.location-1) * nx * ny * nz * self.n_bytes

  #
  # ---------------------------------------------------------------------------
  #
  # An IMAGIC file can hold multiple volumes
  # The user has to specify the wanted volume
  # using a slider
  #
  # Return current slider value
  #
  def get_slider_value(self, event):

      self.location = self.slider.get()
      return

  #
  # ---------------------------------------------------------------------------
  #
  # Read value(s) from file
  # (copied and modified from mrc_format.py)
  #
  def read_values(self, file, etype, count):

    from numpy import array
    esize = array((), etype).itemsize
    string = file.read(esize * count)
    if len(string) < esize * count:
      raise SyntaxError, ('IMAGIC file is truncated.  Failed reading %d values, type %s' % (count, etype.__name__))
    values = self.read_values_from_string(string, etype, count)
    return values

  #
  # ---------------------------------------------------------------------------
  #
  # Read value(s) from a string
  # (copied from mrc_format.py)
  #
  def read_values_from_string(self, string, etype, count):
 
    from numpy import fromstring
    values = fromstring(string, etype)
    if self.swap_bytes:
      values = values.byteswap()
    if count == 1:
      return values[0]
    return values

  #
  # ---------------------------------------------------------------------------
  #
  # Reads a submatrix from a potentially very large file
  # Returns 3D NumPy matrix
  #
  # IMAGIC coordinate system:
  #
  #      -------> X
  #     !              1st  image line
  #     !              2nd  image line
  #     !
  #     V              last image line 
  #
  #     Y
  #
  #     Z is perpendicular to X,Y / right handed
  #
  # Density values are stored line by line / section by section
  # 
  def read_matrix(self, ijk_origin, ijk_size, ijk_step, progress):

    from VolumeData.readarray import read_array
    matrix = read_array(self.img_path, self.data_offset,
                        ijk_origin, ijk_size, ijk_step,
                        self.data_size, self.element_type, self.swap_bytes,
                        progress)

    #
    # From IMAGIC to Chimera coordinate system
    #
    matrix = matrix.copy()[:,::-1,:]

    return matrix

