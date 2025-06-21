# -----------------------------------------------------------------------------
# Make a movie slicing through a volume along one axis while planes for the
# two orthogonal axes are shown.
#
map_path = '~/Desktop/emd_1500.map'
p0 = (.3,.3,.5)         # Initial plane intersection point.
zrange = (.1,.9)        # Range of z values for moving xy plane.
movie_size = (512,512)  # Pixels

# Change file suffix from ".map" to ".mov" for movie file name.
movie_path = map_path.rstrip('.map') + '.mov'

from chimera import runCommand as r, openModels

# Open 3 copies of map
r('open #0 %s' % map_path)
r('open #1 %s' % map_path)
r('open #2 %s' % map_path)

# Set window size in pixels
r('windowsize %d %d' % movie_size)

# Find map size.
v = openModels.list(id = 0)[0]
xsize, ysize, zsize = size = v.data.size

# Make slices intercept point x0,y0,z0
x0,y0,z0 = [int(f*s) for f,s in zip(p0,size)]

# Move xy slice over a limited range of z values.
zmin, zmax = [int(f*zsize) for f in zrange]

# Display xy plane of map #0, yz plane of map #1, xz plane of map #2
r('volume #0 region %d,%d,%d,%d,%d,%d' % (x0+1,y0+1,z0,xsize,ysize,z0))
r('volume #1 region %d,%d,%d,%d,%d,%d' % (x0,y0+1,0,x0,ysize,zsize))
r('volume #2 region %d,%d,%d,%d,%d,%d' % (x0+1,y0,0,xsize,y0,zsize))

# Fit in window.
r('window')

# Rotate about center of models to a better viewing direction.
r('turn -1,1,0 -30')

# Make display style "solid", ie. gray scale rendering
r('volume #0-2 style solid')

# Make the planes opaque (luminance 8-bit color mode)
r('volume #0-2 colorMode l8')

# Make volume color white
r('volume #0-2 color white')

# Make background color gray
r('set bg_color dimgray')

# Show white outlines around planes
r('volume #0-2 showOutlineBox true')

# Start recording movie
r('movie record supersample 3')

# Move the xy in the z direction through the virus and back.
r('volume #0 planes z,%d,%d ; wait %d' % (z0,zmin,z0-zmin+1))
r('volume #0 planes z,%d,%d ; wait %d' % (zmin,zmax,zmax-zmin+1))
r('volume #0 planes z,%d,%d ; wait %d' % (zmax,z0,zmax-z0+1))

# Encode movie
r('movie encode output %s bitrate 5000' % movie_path)
