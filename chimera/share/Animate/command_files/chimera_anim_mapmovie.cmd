# Record a movie spinning a map 360 degrees then slicing through it.

# Open map file EMDB 1500.  This can be done before opening this movie
# recording script.
open emdbID:1500

# Set window size and make map fit within window.
windowsize 512 512
scale 0.8

# Make background color white, enable glossy lighting and silhouette edges
set bg_color white
set light_quality glossy
set silhouette

# Set volume contour level to 0.8 and display full resolution.
volume #0 level 0.8 step 1

# Add text heading.
2dlabels create heading text "Bacteriophage phi6 procapsid, EMDB 1500" color black xpos 0.05 ypos 0.95

# Color virus map radially red to blue from 150 - 250 Angstroms radius.
scolor #0 geometry radial cmaprange 150,250

# Start recording movie.
movie record

# Rotate for 120 frames in 3 degree steps about y axis.
turn y 3 120
wait

# Turn off radial coloring for slicing map.
~scolor #0

# Move front clip plane into map in 5 Anstrom steps.
clip hither -5 120
wait

# Move front clip plane back half way in 5 Angstrom steps.
clip hither 5 60
wait

# Create quicktime encoded movie.
movie encode output ~/Desktop/mapmovie.mov
