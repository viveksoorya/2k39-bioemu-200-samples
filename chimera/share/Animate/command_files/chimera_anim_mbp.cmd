# Open bound and unbound conformations.
#open 2gha-chain-A.pdb
#open 2ghb-chain-A.pdb
open 2gha; delete #0:.B
open 2ghb; delete #1:.B:.C
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
savepos closeview

# Zoom out, move molecule to corner, name position.
scale 0.7
move x -20
move y -10
savepos wideview

# Move ligand away and rotate it some, name position.
~select 2
move x 60
move y 40
turn z 90
turn x 90
select 2
savepos farligand

# Add caption.
2dlabel create title text "Binding maltotriose" xpos 0.3 ypos 0.92 color black

# Start recording
movie record

# Play movie sequence
reset wideview 50
wait 50
reset closeview 25
wait 25
2dlabel change title visibility hide frames 25
wait 25

# Play morph
coordset #2 1,
wait 25

# Show hydrogen bonds
scale 1.03 25
wait
hbond intermodel true intramodel false color pink linewidth 5
roll y 0.5 50
wait
roll y -0.5 50
wait

# Show surface with aromatic residues colored.
# Put on one line so surface does not appear.
surface #2 ; color white,s #2 ; surftransparency 100 #2

# Vertical orientation
turn z 3 30
wait

# Fade in surface
surftransparency 0 #2 20
wait 20

# Color aromatic rings blue
color blue aromatic ring

# Rock and zoom out
rock y 3 150
wait
scale 0.98 50
wait

# Extra stationary frames at end avoid compression artifacts on last frame.
wait 10

# Stop recording and encode movie.
movie stop
movie encode output ~/Desktop/mbp.mov bitrate 6000
