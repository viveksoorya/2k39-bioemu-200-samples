close session
open 2por

# show a list of all the scenes available
scene list

# show a 'default' scene; if it doesn't exist, this automatically
# creates the 'default' scene; it also updates the status line with
# available scenes
#scene default reset

# manipulate the model and add a scene
turn 1,1,0 1 90
scene sc1 save

# manipulate the model and add another scene
scale 0.5
turn 0,1,1 1 90; move 1,1,0 2 10; wait
scene sc2 save

# animate between scenes, from the current state
scene sc1 reset 60; wait
scene sc2 reset 60; wait
# delete a scene
#~scene default

pause end

# Add some scenes to the key frame animation
kfadd sc1
kfadd sc2
# Note that key frames can repeat scene instances
kfadd sc1

# Show the key frames
kfshow sc1 60; wait
kfshow sc2 60; wait
