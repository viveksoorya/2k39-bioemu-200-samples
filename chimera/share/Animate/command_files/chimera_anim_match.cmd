close session

# Open bound and unbound conformations.
open noprefs 2gha; delete #0:.B
open noprefs 2ghb; delete #1:.B:.C
preset apply int 1
modelcolor red #0
modelcolor yellow #1

focus
scene sc1 save

matchmaker #0 #1
focus
scene sc2 save

morph start #0 name 2gh
morph inter #1 name 2gh
morph movie name 2gh nogui true

~modeldisplay #0,1
coordset #2 21
modeldisplay #2
scene sc3 save

coordset #2 1
scene sc4 save

kfadd sc1
kfadd sc2
kfadd sc3
kfadd sc4
kfmovie loop
kfmovie play

pause end

## ADD to "sc2" keyframe transition commands
modelcolor yellow #0
~modeldisp #0,1
modeldisp #2
wait 20
coordset #2 21
modelcolor yellow #2
coordset #2 21,1; wait 21
modelcolor red #2
wait 20
coordset #2 1,21; wait 21
modelcolor yellow #2
wait 20
coordset #2 21,1; wait 21
modelcolor red #2
wait 20
coordset #2 1,21; wait 21
modelcolor yellow #2
wait 20
## END
