#
# Make a movie slicing through a volume along one axis while planes for the
# two orthogonal axes are shown.
#

# Fetch Herpes virus map from EMDB.
open #0 emdbID:1306

# Save local copy of map.
volume #0 save ~/Desktop/emdb_1306.mrc

# Open 2 more copies of map.
open #1 ~/Desktop/emdb_1306.mrc
open #2 ~/Desktop/emdb_1306.mrc

# Display xy plane of map #0, yz plane of map #1, xz plane of map #2
# Map size is 288,288,288 and slice through center point x = y = 100, z = 144.
volume #0 region 101,101,144,287,287,144
volume #1 region 100,101,0,100,287,287
volume #2 region 101,100,0,287,100,287

# Make display style "solid", ie. gray scale rendering
volume #0-2 style solid

# Make the planes opaque (luminance 8-bit color mode)
volume #0-2 colorMode l8

# Set nice looking threshold levels.
volume #0-2 level -.06,0 level .14,1 level .25,1

# Make volume color white
volume #0-2 color white

# Make background color gray
set bg_color dimgray

# Show white outlines around planes
volume #0-2 showOutlineBox true

# Rotate about center of models to a better viewing direction.
cofr models
turn -1,1,0 -30

# Shift to center
move -150,-150,0

# Zoom out a bit.
scale 0.7

# Set window size in pixels
windowsize 512 512

# Start recording movie
movie record supersample 3

# Move the xy in the z direction through the virus and back.
volume #0 planes z,144,33
wait 111
volume #0 planes z,33,260
wait 235
volume #0 planes z,260,144
wait 120

# Encode movie
movie encode output ~/Desktop/emdb_1306.mov bitrate 5000
