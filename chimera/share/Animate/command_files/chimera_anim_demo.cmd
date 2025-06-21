close session

open 3fx2
focus

2dlabels create label1 text 3fx2 xpos 0.1 ypos 0.9

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
turn y 30
wait
scene sc2 save

ribcolor gray #0
turn y 30
wait
scene sc3 save

color yellow #0 & ligand
turn y 30
wait
scene sc4 save

repr sphere ligand
turn y 30
wait
scene sc5 save

repr bs ligand
color byatom ligand
turn y 30
wait
scene sc6 save

surface ligand
turn y 30
wait
scene sc7 save

clip hither -15
turn y 30
wait
scene sc8 save

clip hither 15
turn y 30
wait
scene sc9 save

focus ligand
wait
scene sc10 save


kfadd sc1
kfadd sc2
kfadd sc3
kfadd sc4
kfadd sc5
kfadd sc6
kfadd sc7
kfadd sc8
kfadd sc9
kfadd sc10


#kfshow sc1
#kfmovie loop
#kfmovie play
