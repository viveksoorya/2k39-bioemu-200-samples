# Open bound and unbound conformations.
open noprefs 2gha; delete #0:.B
open noprefs 2ghb; delete #1:.B:.C
matchmaker #0 #1
focus

# Show ribbons and ligand.
preset apply int 1

# Create morph #1 -> #0 as #2.
morph start #1
morph interpolate #0
morph movie

# Hide unbound model, bound state ribbon, and show just ligand atoms.
~modeldisplay #1
~ribbon #0
show ligand

# Show morph in bound state, last frame.
coordset #2 -1

# Show residues of morph near ligand.
show #2 & ligand zr<5

# Return morph to unbound state, first frame.
coordset #2 1
turn y -80 1 models #2 coord #2 center #2
turn z 150 1 models #2 coord #2 center #2

# Color background, morph ribbon, and ligand.
set bg_color gray
color white,r #2
modelcolor yellow ligand

# Ligand in ball and stick style.
repr bs ligand

# Turn on silhouette edges.
set silhouette
set silhouette_width 1.5

# Increase subdivision quality to 5 for smoother ribbon, atoms, bonds.
set subdivision 5

# Name full view position
#scene closeview save

# Zoom out, move molecule to corner, name position.
scale 0.7
move x -20
move y -10
#scene wideview save

# Move ligand away and rotate it some
~select 2
move x 60
move y 40
turn z 90
turn x 90
select 2
# Add caption.
2dlabel create title text "Binding maltotriose" xpos 0.3 ypos 0.92 color black
# name position
#scene farligand save

#kfadd closeview
#kfadd farligand
#kfadd wideview

