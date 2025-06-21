close session

#open 3fx2
#2dlabels create label1 text 3fx2 xpos 0.1 ypos 0.9

# 2gsh has two chains, metal complexes, and alt locs (e.g., residue Lys 25)
open 2gsh
2dlabels create label2 text 2gsh xpos 0.1 ypos 0.1

focus

# 1gc1 has four chains that are different proteins instead of copies of the
# same one, and a "missing segment" dashed line in chain G

# TODO: Add additional models and modify when they are displayed or hidden
# (i.e., setting the model.display property)

# play with 'hb' and '~hb' (find Hbond tool)

# test hidden display 
~modeldisplay #0
#~display #0
#~ribbon #0
wait
scene sc1 save

# test preset displays
modeldisplay #0
#display #0 & ligand
#ribbon #0
preset apply interactive 1
turn y 180
wait
surface ligand
label coil
2dlabels change label2 color red
scene sc2 save

2dlabels change label2 visibility hide
scene sc3 save

kfadd sc1
kfadd sc2
kfadd sc3

